"""
API juridique / commercial — clients, devis, factures, PDF, envoi Brevo.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import legal_db as db
import legal_generator
from agents.coremind_agent import PROJECT_TYPE_LABELS, ProjectType
from config import get_settings
from cost_tracker import build_costs_api_response
from db.supabase_store import SupabaseStoreError, get_supabase_store
from stripe_service import StripeServiceError, create_payment_link
from tools.capcore_notify import send_document_email_to_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["legal"])

DocumentType = Literal["devis", "facture", "mentions_legales", "cgv"]
DocumentStatus = Literal["draft", "sent", "signed", "paid", "cancelled"]
CommercialType = Literal["devis", "facture"]


# --- Schémas ---


class ClientBody(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=3)
    phone: str | None = None
    address: str | None = None
    siret: str | None = None


class ClientUpdateBody(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    email: str | None = Field(default=None, min_length=3)
    phone: str | None = None
    address: str | None = None
    siret: str | None = None


class LineItemBody(BaseModel):
    description: str = Field(min_length=1)
    quantity: float = Field(default=1.0, gt=0)
    unit_price: float = Field(default=0.0, ge=0)
    order: int | None = None


class DocumentCreateBody(BaseModel):
    type: CommercialType
    title: str = Field(min_length=1)
    client_id: str | None = None
    project_id: str | None = None
    status: DocumentStatus = "draft"
    notes: str | None = None
    tva_rate: float = Field(default=0.0, ge=0)
    number: str | None = None
    line_items: list[LineItemBody] = Field(default_factory=list)


class DocumentUpdateBody(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    notes: str | None = None
    status: DocumentStatus | None = None
    client_id: str | None = None
    project_id: str | None = None
    tva_rate: float | None = Field(default=None, ge=0)
    line_items: list[LineItemBody] | None = None


class StatusBody(BaseModel):
    status: DocumentStatus


class SendDocumentBody(BaseModel):
    message: str = Field(min_length=1, description="Message personnalisé au client")
    subject: str | None = None


class PdfResponse(BaseModel):
    pdf_path: str
    pdf_url: str


class DocumentResponse(BaseModel):
    id: str
    type: str
    number: str
    client_id: str | None = None
    project_id: str | None = None
    status: str
    title: str
    notes: str | None = None
    total_ht: float
    tva_rate: float
    total_ttc: float
    pdf_path: str | None = None
    pdf_url: str | None = None
    sent_at: str | None = None
    created_at: str
    line_items: list[dict[str, Any]] = Field(default_factory=list)


class CgvResponse(BaseModel):
    document: DocumentResponse
    pdf_path: str
    pdf_url: str
    created: bool = False


# --- Helpers ---


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pdf_url(request: Request, document_id: str) -> str:
    return str(request.url_for("legal_download_document_pdf", document_id=document_id))


def _enrich_document(
    doc: dict[str, Any],
    *,
    request: Request | None = None,
    include_lines: bool = True,
) -> dict[str, Any]:
    out = dict(doc)
    if include_lines:
        out["line_items"] = db.get_line_items(str(doc["id"]))
    if request and out.get("pdf_path"):
        out["pdf_url"] = _pdf_url(request, str(doc["id"]))
    elif request:
        out["pdf_url"] = None
    return out


def _document_response(
    doc: dict[str, Any],
    *,
    request: Request | None = None,
) -> DocumentResponse:
    return DocumentResponse(**_enrich_document(doc, request=request))


def _value_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


def _sync_line_items(document_id: str, lines: list[LineItemBody]) -> None:
    for existing in db.get_line_items(document_id):
        db.delete_line_item(str(existing["id"]))
    for idx, line in enumerate(lines):
        db.add_line_item(
            document_id=document_id,
            description=line.description,
            quantity=line.quantity,
            unit_price=line.unit_price,
            order=line.order if line.order is not None else idx,
        )


def _generate_pdf_path(document_id: str, doc_type: str) -> str:
    if doc_type == "devis":
        return legal_generator.generate_devis(document_id)
    if doc_type == "facture":
        return legal_generator.generate_facture(document_id)
    raise HTTPException(
        status_code=400,
        detail="Seuls les devis et factures peuvent être générés en PDF.",
    )


def _project_type_label(project_type: str) -> str:
    try:
        return PROJECT_TYPE_LABELS[ProjectType(project_type)]
    except ValueError:
        raw = (project_type or "").replace("_", " ").strip()
        return raw.title() if raw else "projet digital"


async def _fetch_project_row(project_id: str) -> dict[str, Any]:
    store = get_supabase_store()
    if not store.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Supabase non configuré — impossible de charger le projet.",
        )
    try:
        detail = await store.get_project(project_id.strip())
    except SupabaseStoreError as exc:
        raise HTTPException(
            status_code=502,
            detail=exc.detail.message if exc.detail else str(exc),
        ) from exc
    if detail is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    p = detail.project
    return {
        "id": p.id,
        "title": p.title,
        "prompt": p.prompt,
        "project_type": p.project_type,
        "summary": p.summary,
    }


# --- Clients ---


@router.get("/clients")
def list_clients() -> list[dict[str, Any]]:
    return db.list_clients()


@router.post("/clients", status_code=201)
def create_client(body: ClientBody) -> dict[str, Any]:
    try:
        return db.add_client(
            name=body.name,
            email=body.email,
            phone=body.phone,
            address=body.address,
            siret=body.siret,
        )
    except ValueError as exc:
        raise _value_error(exc) from exc


@router.put("/clients/{client_id}")
def update_client(client_id: str, body: ClientUpdateBody) -> dict[str, Any]:
    fields = body.model_dump(exclude_unset=True)
    if not fields:
        row = db.get_client(client_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Client introuvable.")
        return row
    try:
        updated = db.update_client(client_id, **fields)
    except ValueError as exc:
        raise _value_error(exc) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Client introuvable.")
    return updated


@router.delete("/clients/{client_id}", status_code=204)
def delete_client(client_id: str) -> None:
    if not db.delete_client(client_id):
        raise HTTPException(status_code=404, detail="Client introuvable.")


# --- Documents ---


@router.get("/documents")
def list_documents(
    request: Request,
    type: DocumentType | None = Query(default=None),
    status: DocumentStatus | None = Query(default=None),
    client_id: str | None = Query(default=None),
) -> list[DocumentResponse]:
    rows = db.list_documents(type=type, status=status, client_id=client_id)
    return [
        _document_response(row, request=request)
        for row in rows
    ]


@router.post("/documents", status_code=201, response_model=DocumentResponse)
def create_document(body: DocumentCreateBody, request: Request) -> DocumentResponse:
    try:
        doc = db.create_document(
            type=body.type,
            title=body.title,
            client_id=body.client_id,
            project_id=body.project_id,
            status=body.status,
            notes=body.notes,
            tva_rate=body.tva_rate,
            number=body.number,
        )
    except ValueError as exc:
        raise _value_error(exc) from exc

    if body.line_items:
        _sync_line_items(str(doc["id"]), body.line_items)
        refreshed = db.get_document(str(doc["id"]))
        if refreshed:
            doc = refreshed

    return _document_response(doc, request=request)


@router.put("/documents/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: str,
    body: DocumentUpdateBody,
    request: Request,
) -> DocumentResponse:
    fields = body.model_dump(exclude_unset=True, exclude={"line_items"})
    line_items = body.line_items

    if fields:
        try:
            updated = db.update_document(document_id, **fields)
        except ValueError as exc:
            raise _value_error(exc) from exc
        if updated is None:
            raise HTTPException(status_code=404, detail="Document introuvable.")
    else:
        updated = db.get_document(document_id)
        if updated is None:
            raise HTTPException(status_code=404, detail="Document introuvable.")

    if line_items is not None:
        _sync_line_items(document_id, line_items)
        refreshed = db.get_document(document_id)
        if refreshed:
            updated = refreshed

    return _document_response(updated, request=request)


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: str) -> None:
    if not db.delete_document(document_id):
        raise HTTPException(status_code=404, detail="Document introuvable.")


@router.put("/documents/{document_id}/status", response_model=DocumentResponse)
def update_document_status(
    document_id: str,
    body: StatusBody,
    request: Request,
) -> DocumentResponse:
    try:
        updated = db.update_document(document_id, status=body.status)
    except ValueError as exc:
        raise _value_error(exc) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    return _document_response(updated, request=request)


@router.post("/documents/{document_id}/generate-pdf", response_model=PdfResponse)
def generate_document_pdf(document_id: str, request: Request) -> PdfResponse:
    doc = db.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    try:
        path = _generate_pdf_path(document_id, str(doc["type"]))
    except ValueError as exc:
        raise _value_error(exc) from exc
    return PdfResponse(pdf_path=path, pdf_url=_pdf_url(request, document_id))


@router.get(
    "/documents/{document_id}/pdf",
    name="legal_download_document_pdf",
)
def download_document_pdf(document_id: str) -> FileResponse:
    doc = db.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    pdf_path = (doc.get("pdf_path") or "").strip()
    if not pdf_path:
        raise HTTPException(status_code=404, detail="PDF non généré pour ce document.")
    path = Path(pdf_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier PDF introuvable sur le disque.")
    filename = f"{doc.get('number', document_id)}.pdf"
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
    )


@router.post("/documents/{document_id}/payment-link")
def create_invoice_payment_link(document_id: str) -> dict[str, str]:
    """Génère un lien Stripe pour régler une facture."""
    doc = db.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")
    if str(doc.get("type")) != "facture":
        raise HTTPException(status_code=400, detail="Seules les factures ont un lien de paiement.")

    amount_ttc = float(doc.get("total_ttc") or 0)
    if amount_ttc <= 0:
        raise HTTPException(status_code=400, detail="Montant TTC invalide.")

    client = db.get_client(str(doc["client_id"])) if doc.get("client_id") else None
    email = str(client["email"]) if client else None
    project_id = str(doc.get("project_id") or "capcore")

    try:
        url = create_payment_link(
            project_id=project_id,
            amount_eur=amount_ttc,
            description=f"Facture {doc.get('number', '')}",
            customer_email=email,
        )
    except StripeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"url": url}


@router.post("/documents/{document_id}/send")
async def send_document(document_id: str, body: SendDocumentBody) -> dict[str, Any]:
    doc = db.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable.")

    doc_type = str(doc.get("type", ""))
    if doc_type not in ("devis", "facture"):
        raise HTTPException(
            status_code=400,
            detail="Seuls devis et factures peuvent être envoyés par email.",
        )

    client_id = doc.get("client_id")
    if not client_id:
        raise HTTPException(
            status_code=400,
            detail="Associez un client au document avant l'envoi.",
        )
    client = db.get_client(str(client_id))
    if client is None:
        raise HTTPException(status_code=404, detail="Client introuvable.")

    pdf_path = (doc.get("pdf_path") or "").strip()
    if not pdf_path or not Path(pdf_path).is_file():
        try:
            pdf_path = _generate_pdf_path(document_id, doc_type)
        except ValueError as exc:
            raise _value_error(exc) from exc

    kind_label = "Devis" if doc_type == "devis" else "Facture"
    default_subject = f"{kind_label} {doc.get('number', '')} — CapCore"
    subject = (body.subject or "").strip() or default_subject

    payment_link_block = ""
    if doc_type == "facture":
        amount_ttc = float(doc.get("total_ttc") or 0)
        if amount_ttc > 0:
            project_id = str(doc.get("project_id") or "capcore")
            try:
                payment_url = create_payment_link(
                    project_id=project_id,
                    amount_eur=amount_ttc,
                    description=f"Facture {doc.get('number', '')}",
                    customer_email=str(client["email"]),
                )
                payment_link_block = (
                    f"\n\nVous pouvez régler cette facture en ligne :\n{payment_url}\n"
                )
            except StripeServiceError as exc:
                logger.warning("Lien de paiement Stripe indisponible : %s", exc)

    email_body = (
        f"Bonjour {client.get('name', '')},\n\n"
        f"{body.message.strip()}\n\n"
        f"Veuillez trouver ci-joint votre {kind_label.lower()} "
        f"n° {doc.get('number', '')}."
        f"{payment_link_block}\n\n"
        "Cordialement,\n"
        f"{get_settings().mat_legal_name}\n"
        f"{get_settings().mat_legal_brand}"
    )

    sent = await send_document_email_to_client(
        to_email=str(client["email"]),
        subject=subject,
        body=email_body,
        pdf_path=pdf_path,
        attachment_name=Path(pdf_path).name,
        project_id=str(doc["project_id"]) if doc.get("project_id") else None,
    )
    if not sent:
        raise HTTPException(
            status_code=503,
            detail="Envoi email impossible (Brevo non configuré ou erreur d'envoi).",
        )

    now = _utc_now()
    db.update_document(document_id, status="sent", sent_at=now)

    return {
        "sent": True,
        "to": client["email"],
        "subject": subject,
        "pdf_path": pdf_path,
        "sent_at": now,
    }


@router.post(
    "/documents/from-project/{project_id}",
    status_code=201,
    response_model=DocumentResponse,
)
async def create_document_from_project(
    project_id: str,
    request: Request,
) -> DocumentResponse:
    """Crée un devis pré-rempli depuis un projet CyberForge."""
    project = await _fetch_project_row(project_id)
    costs = build_costs_api_response(project_id)
    plan = costs.get("architect_plan") or {}
    type_label = _project_type_label(str(project["project_type"]))
    title = f"Création {type_label} — {project['title']}"

    suggested = int(plan.get("suggested_price_min") or 0)
    prompt = (project.get("prompt") or "").strip()
    summary = (project.get("summary") or "").strip()
    desc_parts = [f"Prestation : {type_label}"]
    if summary:
        desc_parts.append(summary)
    elif prompt:
        desc_parts.append(prompt[:500] + ("…" if len(prompt) > 500 else ""))
    description = " — ".join(desc_parts)

    try:
        doc = db.create_document(
            type="devis",
            title=title,
            project_id=project_id,
            status="draft",
            tva_rate=0.0,
        )
    except ValueError as exc:
        raise _value_error(exc) from exc

    db.add_line_item(
        document_id=str(doc["id"]),
        description=description,
        quantity=1.0,
        unit_price=float(suggested),
        order=0,
    )
    refreshed = db.get_document(str(doc["id"]))
    if refreshed:
        doc = refreshed
    return _document_response(doc, request=request)


# --- Mentions légales & CGV ---


@router.post("/mentions-legales/{project_id}", response_model=PdfResponse)
def generate_mentions_legales(project_id: str, request: Request) -> PdfResponse:
    try:
        path = legal_generator.generate_mentions_legales(project_id)
    except ValueError as exc:
        raise _value_error(exc) from exc

    docs = db.list_documents(type="mentions_legales", limit=50)
    doc_id = None
    for row in docs:
        if row.get("project_id") == project_id:
            doc_id = str(row["id"])
            break
    if doc_id is None:
        raise HTTPException(status_code=500, detail="Document mentions introuvable après génération.")
    return PdfResponse(pdf_path=path, pdf_url=_pdf_url(request, doc_id))


@router.post("/cgv", response_model=CgvResponse)
def generate_or_get_cgv(request: Request) -> CgvResponse:
    existing = db.list_documents(type="cgv", limit=1)
    created = False
    if existing:
        doc = existing[0]
        pdf_path = (doc.get("pdf_path") or "").strip()
        if pdf_path and Path(pdf_path).is_file():
            return CgvResponse(
                document=_document_response(doc, request=request),
                pdf_path=pdf_path,
                pdf_url=_pdf_url(request, str(doc["id"])),
                created=False,
            )

    try:
        pdf_path = legal_generator.generate_cgv()
    except ValueError as exc:
        raise _value_error(exc) from exc

    docs = db.list_documents(type="cgv", limit=1)
    if not docs:
        raise HTTPException(status_code=500, detail="Document CGV introuvable après génération.")
    doc = docs[0]
    created = True
    return CgvResponse(
        document=_document_response(doc, request=request),
        pdf_path=pdf_path,
        pdf_url=_pdf_url(request, str(doc["id"])),
        created=created,
    )

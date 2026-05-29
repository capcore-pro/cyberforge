"""
Génération de PDFs juridiques / commerciaux (ReportLab).
Devis, factures, mentions légales et CGV — sortie dans LEGAL_DOCUMENTS_ROOT.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config import Settings, get_settings
import legal_db

PDFKind = Literal["devis", "facture", "mentions_legales", "cgv"]

_TVA_MENTION = "TVA non applicable — article 293 B du CGI"
_VALIDITY_DAYS = 30
_DEPOSIT_PERCENT = 30

_COLOR_PRIMARY = colors.HexColor("#1e3a5f")
_COLOR_MUTED = colors.HexColor("#64748b")
_COLOR_LINE = colors.HexColor("#e2e8f0")
_REPO_ROOT = Path(__file__).resolve().parents[1]
_LOGO_LIGHT_SVG = _REPO_ROOT / "frontend" / "public" / "logo-capcore-light.svg"


@dataclass(frozen=True)
class MatProfile:
    name: str
    activity: str
    status: str
    email: str
    siret: str
    brand: str
    tva_mention: str = _TVA_MENTION


def _mat_profile(settings: Settings | None = None) -> MatProfile:
    s = settings or get_settings()
    siret = (s.mat_siret or "").strip() or "SIRET à renseigner (MAT_SIRET)"
    return MatProfile(
        name=s.mat_legal_name.strip(),
        activity=s.mat_legal_activity.strip(),
        status=s.mat_legal_status.strip(),
        email=s.mat_legal_email.strip(),
        siret=siret,
        brand=s.mat_legal_brand.strip() or "CapCore",
    )


def _documents_root(settings: Settings | None = None) -> Path:
    root = (settings or get_settings()).legal_documents_dir
    root.mkdir(parents=True, exist_ok=True)
    return root


def _parse_date(value: str | None) -> date:
    if not value:
        return datetime.now(timezone.utc).date()
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()


def _format_date_fr(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _format_eur(amount: float) -> str:
    return f"{float(amount):,.2f} €".replace(",", " ").replace(".", ",")


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "-", value.strip())
    return cleaned[:120] or "document"


def _pdf_output_path(kind: PDFKind, basename: str, settings: Settings | None = None) -> Path:
    sub = _documents_root(settings) / kind
    sub.mkdir(parents=True, exist_ok=True)
    return sub / f"{_safe_filename(basename)}.pdf"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "LegalTitle",
            parent=base["Heading1"],
            fontSize=18,
            textColor=_COLOR_PRIMARY,
            spaceAfter=8,
        ),
        "heading": ParagraphStyle(
            "LegalHeading",
            parent=base["Heading2"],
            fontSize=12,
            textColor=_COLOR_PRIMARY,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "LegalBody",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.black,
        ),
        "small": ParagraphStyle(
            "LegalSmall",
            parent=base["Normal"],
            fontSize=8,
            leading=10,
            textColor=_COLOR_MUTED,
        ),
        "right": ParagraphStyle(
            "LegalRight",
            parent=base["Normal"],
            fontSize=10,
            alignment=TA_RIGHT,
        ),
        "center": ParagraphStyle(
            "LegalCenter",
            parent=base["Normal"],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=_COLOR_MUTED,
        ),
    }


def _footer_canvas(canvas, doc, mat: MatProfile) -> None:  # noqa: ARG001
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_COLOR_MUTED)
    footer = (
        f"{mat.brand} — {mat.name} — {mat.status} — SIRET : {mat.siret} — {mat.email}"
    )
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm, footer)
    canvas.restoreState()


class _SvgLogoFlowable(Flowable):
    """Flowable ReportLab pour un drawing SVG (svglib)."""

    def __init__(self, drawing: Any, width: float, height: float) -> None:
        super().__init__()
        self.drawing = drawing
        self.width = width
        self.height = height

    def draw(self) -> None:
        from reportlab.graphics import renderPDF

        self.canv.saveState()
        renderPDF.draw(self.drawing, self.canv, 0, 0)
        self.canv.restoreState()


def _logo_header_block() -> list[Any]:
    """Logo CapCore (version fond clair) en tête des PDFs commerciaux."""
    if not _LOGO_LIGHT_SVG.is_file():
        return []
    try:
        from svglib.svglib import svg2rlg
    except ImportError:
        return []

    drawing = svg2rlg(str(_LOGO_LIGHT_SVG))
    if drawing is None or not drawing.width or not drawing.height:
        return []

    target_w = 6.5 * cm
    scale = target_w / float(drawing.width)
    drawing.width = target_w
    drawing.height = float(drawing.height) * scale
    drawing.scale(scale, scale)
    return [
        _SvgLogoFlowable(drawing, drawing.width, drawing.height),
        Spacer(1, 0.35 * cm),
    ]


def _issuer_block(mat: MatProfile, st: dict[str, ParagraphStyle]) -> list[Any]:
    lines = [
        f"<b>{mat.brand}</b>",
        mat.activity,
        mat.name,
        mat.status,
        mat.email,
        f"SIRET : {mat.siret}",
    ]
    return [Paragraph("<br/>".join(lines), st["body"])]


def _client_block(client: dict[str, Any] | None, st: dict[str, ParagraphStyle]) -> list[Any]:
    if not client:
        return [Paragraph("<b>Client</b><br/>—", st["body"])]
    parts = [f"<b>{client.get('name', 'Client')}</b>"]
    if client.get("email"):
        parts.append(str(client["email"]))
    if client.get("phone"):
        parts.append(str(client["phone"]))
    if client.get("address"):
        parts.append(str(client["address"]))
    if client.get("siret"):
        parts.append(f"SIRET : {client['siret']}")
    return [Paragraph("<br/>".join(parts), st["body"])]


def _header_table(
    mat: MatProfile,
    client: dict[str, Any] | None,
    st: dict[str, ParagraphStyle],
) -> Table:
    tbl = Table(
        [
            [_issuer_block(mat, st)[0], _client_block(client, st)[0]],
        ],
        colWidths=[9.5 * cm, 9.5 * cm],
    )
    tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return tbl


def _line_items_table(items: list[dict[str, Any]], st: dict[str, ParagraphStyle]) -> Table:
    header = [
        Paragraph("<b>Description</b>", st["body"]),
        Paragraph("<b>Qté</b>", st["body"]),
        Paragraph("<b>Prix unit. HT</b>", st["body"]),
        Paragraph("<b>Total HT</b>", st["body"]),
    ]
    rows: list[list[Any]] = [header]
    for item in items:
        rows.append(
            [
                Paragraph(str(item.get("description", "")), st["body"]),
                Paragraph(f"{float(item.get('quantity', 1)):g}", st["body"]),
                Paragraph(_format_eur(float(item.get("unit_price", 0))), st["body"]),
                Paragraph(_format_eur(float(item.get("total", 0))), st["body"]),
            ]
        )
    if len(rows) == 1:
        rows.append(
            [
                Paragraph("<i>Aucune ligne</i>", st["body"]),
                Paragraph("—", st["body"]),
                Paragraph("—", st["body"]),
                Paragraph(_format_eur(0), st["body"]),
            ]
        )

    tbl = Table(rows, colWidths=[9 * cm, 2 * cm, 3.5 * cm, 3.5 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _COLOR_PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, _COLOR_LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tbl


def _totals_block(
    doc: dict[str, Any],
    mat: MatProfile,
    st: dict[str, ParagraphStyle],
) -> Table:
    total_ht = float(doc.get("total_ht", 0))
    total_ttc = float(doc.get("total_ttc", total_ht))
    rows = [
        ["Total HT", _format_eur(total_ht)],
        [mat.tva_mention, "—"],
        ["Total TTC", _format_eur(total_ttc)],
    ]
    tbl = Table(rows, colWidths=[12 * cm, 6 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, _COLOR_PRIMARY),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tbl


def _build_commercial_pdf(
    *,
    kind: PDFKind,
    title: str,
    meta_lines: list[str],
    doc: dict[str, Any],
    client: dict[str, Any] | None,
    items: list[dict[str, Any]],
    conditions: list[str],
    extra_paragraphs: list[str] | None = None,
    output_path: Path,
    settings: Settings | None = None,
) -> Path:
    mat = _mat_profile(settings)
    st = _styles()

    def on_page(canvas, doc_tpl):  # noqa: ANN001
        _footer_canvas(canvas, doc_tpl, mat)

    pdf = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2.2 * cm,
    )

    story: list[Any] = [
        *_logo_header_block(),
        _header_table(mat, client, st),
        Spacer(1, 0.5 * cm),
        Paragraph(title, st["title"]),
    ]
    for line in meta_lines:
        story.append(Paragraph(line, st["body"]))
    story.append(Spacer(1, 0.4 * cm))
    if doc.get("title"):
        story.append(Paragraph(f"<b>Objet :</b> {doc['title']}", st["body"]))
    if doc.get("notes"):
        story.append(Paragraph(f"<i>{doc['notes']}</i>", st["small"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_line_items_table(items, st))
    story.append(Spacer(1, 0.4 * cm))
    story.append(_totals_block(doc, mat, st))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("<b>Conditions</b>", st["heading"]))
    for cond in conditions:
        story.append(Paragraph(f"• {cond}", st["body"]))
    if extra_paragraphs:
        story.append(Spacer(1, 0.3 * cm))
        for para in extra_paragraphs:
            story.append(Paragraph(para, st["body"]))

    pdf.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return output_path


def _save_pdf_path(document_id: str, pdf_path: Path) -> str:
    path_str = str(pdf_path.resolve())
    updated = legal_db.update_document(document_id, pdf_path=path_str)
    if updated is None:
        raise ValueError(f"Document introuvable : {document_id}")
    return path_str


def _load_commercial_document(
    document_id: str,
    expected_type: Literal["devis", "facture"],
) -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]]]:
    doc = legal_db.get_document(document_id)
    if doc is None:
        raise ValueError(f"Document introuvable : {document_id}")
    if doc.get("type") != expected_type:
        raise ValueError(
            f"Type attendu « {expected_type} », reçu « {doc.get('type')} »."
        )
    client = None
    if doc.get("client_id"):
        client = legal_db.get_client(str(doc["client_id"]))
    items = legal_db.get_line_items(document_id)
    return doc, client, items


def generate_devis(document_id: str, *, settings: Settings | None = None) -> str:
    """Génère le PDF d'un devis et met à jour pdf_path en base."""
    doc, client, items = _load_commercial_document(document_id, "devis")
    issue = _parse_date(doc.get("created_at"))
    valid_until = issue + timedelta(days=_VALIDITY_DAYS)

    meta = [
        f"<b>Devis n°</b> {doc.get('number', '—')}",
        f"<b>Date :</b> {_format_date_fr(issue)}",
        f"<b>Validité :</b> {_format_date_fr(valid_until)} ({_VALIDITY_DAYS} jours)",
    ]
    conditions = [
        f"Devis valable {_VALIDITY_DAYS} jours à compter de la date d'émission.",
        f"Acompte de {_DEPOSIT_PERCENT} % à la commande, solde à la livraison.",
        "Tout travail supplémentaire fera l'objet d'un avenant ou d'un nouveau devis.",
    ]
    out = _pdf_output_path("devis", str(doc.get("number", document_id)), settings)
    _build_commercial_pdf(
        kind="devis",
        title="DEVIS",
        meta_lines=meta,
        doc=doc,
        client=client,
        items=items,
        conditions=conditions,
        output_path=out,
        settings=settings,
    )
    return _save_pdf_path(document_id, out)


def generate_facture(document_id: str, *, settings: Settings | None = None) -> str:
    """Génère le PDF d'une facture et met à jour pdf_path en base."""
    doc, client, items = _load_commercial_document(document_id, "facture")
    issue = _parse_date(doc.get("created_at"))
    due = issue + timedelta(days=_VALIDITY_DAYS)

    meta = [
        f"<b>Facture n°</b> {doc.get('number', '—')}",
        f"<b>Date d'émission :</b> {_format_date_fr(issue)}",
        f"<b>Date d'échéance :</b> {_format_date_fr(due)} ({_VALIDITY_DAYS} jours)",
    ]
    extra: list[str] = []
    if doc.get("status") == "paid":
        paid_on = _parse_date(doc.get("sent_at") or doc.get("created_at"))
        extra.append(
            f'<b>Acquitté le {_format_date_fr(paid_on)}</b> — Paiement reçu.'
        )

    conditions = [
        f"Paiement sous {_VALIDITY_DAYS} jours à compter de la date d'émission.",
        "En cas de retard, des pénalités pourront être appliquées conformément à la loi.",
        _TVA_MENTION + ".",
    ]
    out = _pdf_output_path("facture", str(doc.get("number", document_id)), settings)
    _build_commercial_pdf(
        kind="facture",
        title="FACTURE",
        meta_lines=meta,
        doc=doc,
        client=client,
        items=items,
        conditions=conditions,
        extra_paragraphs=extra or None,
        output_path=out,
        settings=settings,
    )
    return _save_pdf_path(document_id, out)


def _hosting_label(project_type: str) -> str:
    pt = (project_type or "").strip().lower()
    if pt in (
        "application_web",
        "saas_dashboard",
        "api_backend",
        "application_mobile",
    ):
        return (
            "Hébergement : interface sur Vercel (https://vercel.com) ; "
            "services applicatifs sur Railway (https://railway.app) lorsque applicable."
        )
    return "Hébergement : Vercel Inc. (https://vercel.com)."


def _fetch_project_sync(project_id: str) -> dict[str, str] | None:
    try:
        from db.supabase_store import get_supabase_store
    except ImportError:
        return None

    store = get_supabase_store()
    if not store.is_configured():
        return None

    async def _load() -> dict[str, str] | None:
        detail = await store.get_project(project_id.strip())
        if detail is None:
            return None
        p = detail.project
        return {
            "title": p.title,
            "project_type": p.project_type,
            "prompt": p.prompt,
        }

    try:
        from db.supabase_store import SupabaseStoreError

        try:
            return asyncio.run(_load())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(_load())
            finally:
                loop.close()
    except SupabaseStoreError:
        return None


def _find_or_create_legal_document(
    *,
    doc_type: PDFKind,
    title: str,
    project_id: str | None = None,
) -> dict[str, Any]:
    existing = legal_db.list_documents(type=doc_type, limit=500)
    if project_id:
        for row in existing:
            if row.get("project_id") == project_id:
                return row
    elif doc_type == "cgv" and existing:
        return existing[0]

    return legal_db.create_document(
        type=doc_type,
        title=title,
        project_id=project_id,
        status="draft",
        tva_rate=0,
    )


def _build_text_pdf(
    *,
    kind: PDFKind,
    title: str,
    sections: list[tuple[str, str]],
    basename: str,
    settings: Settings | None = None,
) -> Path:
    mat = _mat_profile(settings)
    st = _styles()
    out = _pdf_output_path(kind, basename, settings)

    def on_page(canvas, doc_tpl):  # noqa: ANN001
        _footer_canvas(canvas, doc_tpl, mat)

    pdf = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2.2 * cm,
    )
    story: list[Any] = [
        Paragraph(f"<b>{mat.brand}</b> — {mat.activity}", st["center"]),
        Spacer(1, 0.3 * cm),
        Paragraph(title, st["title"]),
        Spacer(1, 0.2 * cm),
    ]
    for heading, body in sections:
        story.append(Paragraph(heading, st["heading"]))
        for para in body.split("\n\n"):
            text = para.strip()
            if text:
                story.append(Paragraph(text.replace("\n", "<br/>"), st["body"]))
        story.append(Spacer(1, 0.15 * cm))

    pdf.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return out


def generate_mentions_legales(
    project_id: str,
    *,
    settings: Settings | None = None,
) -> str:
    """Génère les mentions légales pour un projet web et enregistre le PDF."""
    mat = _mat_profile(settings)
    project = _fetch_project_sync(project_id)
    site_name = project["title"] if project else f"Projet {project_id[:8]}"
    project_type = project["project_type"] if project else "site_web"
    hosting = _hosting_label(project_type)

    doc_row = _find_or_create_legal_document(
        doc_type="mentions_legales",
        title=f"Mentions légales — {site_name}",
        project_id=project_id.strip(),
    )
    doc_id = str(doc_row["id"])

    sections = [
        (
            "1. Éditeur du site",
            (
                f"Le site « {site_name} » est édité par :<br/>"
                f"<b>{mat.name}</b>, {mat.activity}, {mat.status}.<br/>"
                f"Email : {mat.email}<br/>"
                f"SIRET : {mat.siret}"
            ),
        ),
        (
            "2. Directeur de la publication",
            f"{mat.name}, en qualité d'éditeur et responsable de publication.",
        ),
        (
            "3. Hébergement",
            hosting,
        ),
        (
            "4. Contact",
            (
                f"Pour toute question relative au site, vous pouvez écrire à : "
                f"<b>{mat.email}</b>."
            ),
        ),
        (
            "5. Propriété intellectuelle",
            (
                "L'ensemble des contenus présents sur le site (textes, images, graphismes, "
                "logo, icônes, structure) est protégé par le droit d'auteur. Toute "
                "reproduction, représentation ou exploitation non autorisée est interdite."
            ),
        ),
        (
            "6. Données personnelles",
            (
                "Les données collectées via les formulaires du site sont traitées uniquement "
                "pour répondre aux demandes des utilisateurs. Vous disposez d'un droit "
                "d'accès, de rectification et de suppression en contactant l'éditeur."
            ),
        ),
        (
            "7. Limitation de responsabilité",
            (
                "L'éditeur s'efforce d'assurer l'exactitude des informations diffusées. "
                "Toutefois, il ne saurait être tenu responsable des omissions, "
                "inexactitudes ou indisponibilité temporaire du service."
            ),
        ),
    ]

    basename = f"ML-{project_id[:8]}-{doc_row.get('number', doc_id)[:20]}"
    out = _build_text_pdf(
        kind="mentions_legales",
        title="MENTIONS LÉGALES",
        sections=sections,
        basename=basename,
        settings=settings,
    )
    return _save_pdf_path(doc_id, out)


def generate_cgv(*, settings: Settings | None = None) -> str:
    """Génère les CGV standard et enregistre le PDF."""
    mat = _mat_profile(settings)
    doc_row = _find_or_create_legal_document(
        doc_type="cgv",
        title="Conditions générales de vente — CapCore",
    )
    doc_id = str(doc_row["id"])

    sections = [
        (
            "1. Objet",
            (
                f"Les présentes conditions générales de vente (CGV) régissent les "
                f"prestations de services numériques proposées par {mat.name}, "
                f"agissant sous le nom commercial {mat.brand} ({mat.activity}), "
                f"à ses clients professionnels ou particuliers."
            ),
        ),
        (
            "2. Prestations",
            (
                "Les prestations comprennent notamment : conception et développement "
                "de sites web, applications, contenus, intégrations, maintenance et "
                "conseil digital. Le périmètre exact est défini dans le devis accepté "
                "par le client."
            ),
        ),
        (
            "3. Tarifs",
            (
                "Les prix sont indiqués en euros hors taxes. "
                f"{_TVA_MENTION}. "
                "Tout travail non prévu au devis initial fera l'objet d'un devis "
                "complémentaire validé avant exécution."
            ),
        ),
        (
            "4. Paiement",
            (
                f"Un acompte de {_DEPOSIT_PERCENT} % est exigible à la commande. "
                "Le solde est dû à la livraison ou selon l'échéancier convenu. "
                "En cas de retard de paiement, des pénalités de retard pourront être "
                "appliquées conformément aux dispositions légales en vigueur."
            ),
        ),
        (
            "5. Délais",
            (
                "Les délais de réalisation sont communiqués à titre indicatif dans le "
                "devis. Le prestataire informe le client de tout retard significatif. "
                "Le client s'engage à fournir dans les délais les éléments nécessaires "
                "(textes, visuels, accès, validations)."
            ),
        ),
        (
            "6. Propriété intellectuelle",
            (
                "Sauf mention contraire au devis, la cession des droits d'exploitation "
                "intervient après paiement intégral. Le prestataire conserve le droit "
                "de mentionner la réalisation dans son portfolio sauf opposition "
                "écrite du client."
            ),
        ),
        (
            "7. Responsabilité",
            (
                "La responsabilité du prestataire est limitée au montant HT facturé "
                "au titre de la prestation concernée. Le prestataire n'est pas "
                "responsable des dommages indirects, pertes de données ou manques "
                "à gagner résultant de l'utilisation du livrable."
            ),
        ),
        (
            "8. Résiliation",
            (
                "En cas de résiliation par le client avant achèvement, les travaux "
                "déjà réalisés et frais engagés restent dus. Les sommes versées à "
                "titre d'acompte ne sont pas remboursables sauf accord écrit."
            ),
        ),
        (
            "9. Droit applicable",
            (
                "Les présentes CGV sont soumises au droit français. En cas de litige, "
                "les parties rechercheront une solution amiable avant toute action "
                "judiciaire. À défaut, les tribunaux français seront seuls compétents."
            ),
        ),
        (
            "10. Contact",
            (
                f"Pour toute question : {mat.name} — {mat.email} — SIRET : {mat.siret}"
            ),
        ),
    ]

    basename = f"CGV-{doc_row.get('number', doc_id)}"
    out = _build_text_pdf(
        kind="cgv",
        title="CONDITIONS GÉNÉRALES DE VENTE",
        sections=sections,
        basename=basename,
        settings=settings,
    )
    return _save_pdf_path(doc_id, out)

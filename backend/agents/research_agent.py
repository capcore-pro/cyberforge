"""
ResearchAgent — enrichissement contenu via Brave Search + Exa AI.

Appelé après ArchitectAI pour alimenter BuilderAI / CoreMindAI avec des
données réelles (tendances, concurrents, mots-clés, exemples).
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import requests
from pydantic import BaseModel, Field

from agents.architect_agent import ArchitectPlan
from agents.base_agent import BaseAgent
from config import Settings, get_settings, plain_secret_str
from tools.project_title import clean_project_title

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
EXA_AVAILABLE = False

try:
    from exa_py import Exa

    EXA_AVAILABLE = True
except ImportError:
    Exa = None  # type: ignore[assignment,misc]

_CITY_RE = re.compile(
    r"(?:\b(?:à|a|sur|dans|ville de|based in)\s+)"
    r"([A-ZÀ-ÖÙ-Ý][a-zà-öù-ÿ\-]+(?:\s+[A-ZÀ-ÖÙ-Ý][a-zà-öù-ÿ\-]+)?)",
    re.UNICODE,
)
_COMPANY_RE = re.compile(
    r"(?:pour|entreprise|société|restaurant|cabinet|salon|agence|studio|"
    r"site (?:web|vitrine) (?:pour|de))\s+[«\"']?"
    r"([^»,.\n\"']{2,80})",
    re.IGNORECASE,
)


class ResearchBrief(BaseModel):
    """Brief enrichi pour la génération de contenu."""

    agent_id: str = "research"
    agent_name: str = "ResearchAI"
    secteur: str = ""
    nom_entreprise: str = ""
    ville: str = ""
    type_projet: str = ""
    tendances: list[str] = Field(default_factory=list)
    concurrents: list[str] = Field(default_factory=list)
    mots_cles: list[str] = Field(default_factory=list)
    contenu_suggere: list[str] = Field(default_factory=list)
    exemples_sites: list[str] = Field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None

    @property
    def enriched(self) -> bool:
        return bool(
            self.tendances
            or self.concurrents
            or self.mots_cles
            or self.contenu_suggere
            or self.exemples_sites
        )


def format_research_brief_for_prompt(brief: ResearchBrief | None) -> str:
    """Formate le brief pour injection dans les prompts BuilderAI / CoreMindAI."""
    if brief is None or brief.skipped or not brief.enriched:
        return ""
    lines = [
        "## Brief recherche contenu (Brave Search + Exa AI)",
        "Utilise ces éléments réels pour rédiger du contenu personnalisé — "
        "pas de noms, adresses ou statistiques fictifs.",
        "",
    ]
    if brief.secteur or brief.nom_entreprise or brief.ville:
        ctx = " · ".join(
            p
            for p in (
                f"Secteur : {brief.secteur}" if brief.secteur else "",
                f"Entreprise : {brief.nom_entreprise}" if brief.nom_entreprise else "",
                f"Ville : {brief.ville}" if brief.ville else "",
                f"Type : {brief.type_projet}" if brief.type_projet else "",
            )
            if p
        )
        lines.append(ctx)
        lines.append("")
    if brief.tendances:
        lines.append("### Tendances du secteur")
        lines.extend(f"- {item}" for item in brief.tendances[:8])
        lines.append("")
    if brief.concurrents:
        lines.append("### Concurrents / acteurs locaux")
        lines.extend(f"- {item}" for item in brief.concurrents[:8])
        lines.append("")
    if brief.mots_cles:
        lines.append("### Mots-clés populaires")
        lines.append(", ".join(brief.mots_cles[:15]))
        lines.append("")
    if brief.contenu_suggere:
        lines.append("### Contenu suggéré")
        lines.extend(f"- {item}" for item in brief.contenu_suggere[:8])
        lines.append("")
    if brief.exemples_sites:
        lines.append("### Exemples de sites similaires")
        lines.extend(f"- {item}" for item in brief.exemples_sites[:6])
        lines.append("")
    return "\n".join(lines).strip() + "\n\n"


def extract_research_context(
    prompt: str,
    *,
    plan: ArchitectPlan | None = None,
) -> dict[str, str]:
    """Extrait secteur, entreprise, ville et type depuis le plan et le prompt."""
    text = (prompt or "").strip()
    secteur = (plan.secteur if plan and plan.secteur else "") or _guess_secteur(text)
    nom_entreprise = _extract_company_name(text)
    ville = _extract_city(text)
    type_projet = plan.project_type_label if plan else "site web"
    return {
        "secteur": secteur,
        "nom_entreprise": nom_entreprise,
        "ville": ville,
        "type_projet": type_projet,
    }


def _guess_secteur(prompt: str) -> str:
    lower = prompt.lower()
    sectors = (
        ("restaurant", "restauration"),
        ("restauration", "restauration"),
        ("immobilier", "immobilier"),
        ("coiffeur", "coiffure"),
        ("coiffure", "coiffure"),
        ("avocat", "juridique"),
        ("cabinet", "services professionnels"),
        ("e-commerce", "e-commerce"),
        ("ecommerce", "e-commerce"),
        ("saas", "SaaS"),
        ("fitness", "sport & bien-être"),
        ("yoga", "sport & bien-être"),
        ("hôtel", "hôtellerie"),
        ("hotel", "hôtellerie"),
        ("artisan", "artisanat"),
        ("plombier", "artisanat"),
        ("médecin", "santé"),
        ("santé", "santé"),
    )
    for needle, label in sectors:
        if needle in lower:
            return label
    return "activité locale"


def _extract_company_name(prompt: str) -> str:
    for match in _COMPANY_RE.finditer(prompt):
        name = match.group(1).strip()
        if len(name) >= 2:
            return name[:80]
    title = clean_project_title(prompt, max_len=60)
    if title and title != "Projet sans titre":
        return title
    return ""


def _extract_city(prompt: str) -> str:
    match = _CITY_RE.search(prompt)
    if match:
        return match.group(1).strip()[:60]
    return ""


def _resolve_api_key(env_name: str, settings_value: Any) -> str:
    try:
        from security.secret_vault import get_secret_vault

        vault_val = get_secret_vault().peek(env_name)
        if vault_val:
            return vault_val.strip()
    except Exception:
        pass
    return plain_secret_str(settings_value)


class ResearchAgent(BaseAgent):
    """Recherche Brave Search + Exa pour enrichir le contenu généré."""

    @property
    def agent_id(self) -> str:
        return "research"

    @property
    def name(self) -> str:
        return "ResearchAI"

    async def run(self, prompt: str, **kwargs: Any) -> str:
        plan = kwargs.get("architect_plan")
        ctx = extract_research_context(
            prompt,
            plan=plan if isinstance(plan, ArchitectPlan) else None,
        )
        brief = await self.research(**ctx, prompt=prompt)
        return brief.model_dump_json()

    async def research(
        self,
        *,
        secteur: str,
        nom_entreprise: str,
        ville: str,
        type_projet: str,
        prompt: str = "",
        settings: Settings | None = None,
    ) -> ResearchBrief:
        resolved = settings or self._settings
        base = ResearchBrief(
            secteur=secteur.strip(),
            nom_entreprise=nom_entreprise.strip(),
            ville=ville.strip(),
            type_projet=type_projet.strip(),
        )

        if not resolved.research_enabled:
            return base.model_copy(
                update={"skipped": True, "skip_reason": "Recherche de contenu désactivée"},
            )

        brave_key = _resolve_api_key("BRAVE_SEARCH_API_KEY", resolved.brave_search_api_key)
        exa_key = _resolve_api_key("EXA_API_KEY", resolved.exa_api_key)
        if not brave_key and not exa_key:
            return base.model_copy(
                update={
                    "skipped": True,
                    "skip_reason": "Clés Brave Search / Exa non configurées",
                },
            )

        sector = secteur or _guess_secteur(prompt)

        async def _empty_dict() -> dict[str, list[str]]:
            return {}

        try:
            brave_task = (
                asyncio.to_thread(
                    _brave_research,
                    brave_key,
                    sector=sector,
                    ville=ville,
                    type_projet=type_projet,
                    timeout=resolved.research_timeout_seconds,
                )
                if brave_key
                else _empty_dict()
            )
            exa_task = (
                asyncio.to_thread(
                    _exa_research,
                    exa_key,
                    sector=sector,
                    ville=ville,
                    type_projet=type_projet,
                    nom_entreprise=nom_entreprise,
                    timeout=resolved.research_timeout_seconds,
                )
                if exa_key and EXA_AVAILABLE
                else _empty_dict()
            )
            brave_data, exa_data = await asyncio.gather(brave_task, exa_task)
        except Exception as exc:
            logger.exception("ResearchAgent")
            return base.model_copy(
                update={"skipped": True, "skip_reason": f"Erreur recherche : {exc}"},
            )

        tendances = list(brave_data.get("tendances") or [])
        concurrents = list(brave_data.get("concurrents") or [])
        mots_cles = list(brave_data.get("mots_cles") or [])
        contenu_suggere = list(exa_data.get("contenu_suggere") or [])
        exemples_sites = list(exa_data.get("exemples_sites") or [])

        if not any((tendances, concurrents, mots_cles, contenu_suggere, exemples_sites)):
            return base.model_copy(
                update={"skipped": True, "skip_reason": "Aucun résultat de recherche"},
            )

        return ResearchBrief(
            secteur=sector,
            nom_entreprise=nom_entreprise.strip(),
            ville=ville.strip(),
            type_projet=type_projet.strip(),
            tendances=_dedupe(tendances)[:8],
            concurrents=_dedupe(concurrents)[:8],
            mots_cles=_dedupe(mots_cles)[:15],
            contenu_suggere=_dedupe(contenu_suggere)[:8],
            exemples_sites=_dedupe(exemples_sites)[:6],
        )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out


def _brave_search(
    api_key: str,
    query: str,
    *,
    count: int = 5,
    timeout: float,
) -> list[dict[str, str]]:
    if not api_key.strip():
        return []
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key.strip(),
    }
    response = requests.get(
        BRAVE_SEARCH_URL,
        headers=headers,
        params={"q": query, "count": count, "search_lang": "fr", "country": "FR"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    web = payload.get("web") if isinstance(payload.get("web"), dict) else {}
    results = web.get("results") if isinstance(web.get("results"), list) else []
    parsed: list[dict[str, str]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        parsed.append(
            {
                "title": str(item.get("title") or "").strip(),
                "description": str(item.get("description") or "").strip(),
                "url": str(item.get("url") or "").strip(),
            }
        )
    return parsed


def _brave_research(
    api_key: str,
    *,
    sector: str,
    ville: str,
    type_projet: str,
    timeout: float,
) -> dict[str, list[str]]:
    loc = f" {ville}" if ville else " France"
    queries = {
        "tendances": f"tendances {sector} {type_projet}{loc} 2025 2026",
        "concurrents": f"{sector} {ville} entreprises concurrents" if ville else f"{sector} entreprises leaders France",
        "mots_cles": f"mots clés SEO {sector} {type_projet}{loc}",
    }
    tendances: list[str] = []
    concurrents: list[str] = []
    mots_cles: list[str] = []

    for label, query in queries.items():
        try:
            hits = _brave_search(api_key, query, count=5, timeout=timeout)
        except Exception as exc:
            logger.warning("Brave Search (%s): %s", label, exc)
            continue
        for hit in hits:
            title = hit.get("title") or ""
            desc = hit.get("description") or ""
            snippet = f"{title} — {desc}".strip(" —") if desc else title
            if not snippet:
                continue
            if label == "tendances":
                tendances.append(snippet[:220])
            elif label == "concurrents":
                line = title[:100]
                if hit.get("url"):
                    line = f"{line} ({hit['url']})"
                concurrents.append(line[:220])
            else:
                words = re.findall(r"[a-zàâäéèêëïîôùûüç0-9-]{3,}", f"{title} {desc}".lower())
                mots_cles.extend(words[:5])

    return {
        "tendances": tendances,
        "concurrents": concurrents,
        "mots_cles": mots_cles,
    }


def _exa_research(
    api_key: str,
    *,
    sector: str,
    ville: str,
    type_projet: str,
    nom_entreprise: str,
    timeout: float,
) -> dict[str, list[str]]:
    if not EXA_AVAILABLE or not api_key.strip():
        return {"contenu_suggere": [], "exemples_sites": []}

    exa = Exa(api_key=api_key.strip())
    loc = f" à {ville}" if ville else ""
    query = (
        f"sites web {type_projet} {sector}{loc} exemples réussis contenu marketing"
    )
    if nom_entreprise:
        query = f"{query} inspiration pour {nom_entreprise}"

    contenu_suggere: list[str] = []
    exemples_sites: list[str] = []

    try:
        response = exa.search_and_contents(
            query,
            num_results=5,
            text={"max_characters": 400},
            type="auto",
        )
    except Exception as exc:
        logger.warning("Exa search: %s", exc)
        return {"contenu_suggere": [], "exemples_sites": []}

    results = getattr(response, "results", None) or []
    for item in results:
        title = str(getattr(item, "title", "") or "").strip()
        url = str(getattr(item, "url", "") or "").strip()
        text = str(getattr(item, "text", "") or "").strip()
        if url:
            exemples_sites.append(f"{title or url} — {url}"[:220])
        if text:
            excerpt = text.replace("\n", " ").strip()[:280]
            if excerpt:
                contenu_suggere.append(excerpt)
        elif title:
            contenu_suggere.append(title[:220])

    return {
        "contenu_suggere": contenu_suggere,
        "exemples_sites": exemples_sites,
    }

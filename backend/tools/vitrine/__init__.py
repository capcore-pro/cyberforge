"""Sites vitrines Next.js — génération de contenu et rendu scaffold."""

from tools.vitrine.build import VitrineBuildResult, build_vitrine_site
from tools.vitrine.content_agent import VitrineContentAgent, VitrineContentError
from tools.vitrine.content_schema import ClientBranding, VitrineSiteContent
from tools.vitrine.scaffold_renderer import ScaffoldRenderError, render_vitrine_scaffold

__all__ = [
    "ClientBranding",
    "ScaffoldRenderError",
    "VitrineBuildResult",
    "VitrineContentAgent",
    "VitrineContentError",
    "VitrineSiteContent",
    "build_vitrine_site",
    "render_vitrine_scaffold",
]

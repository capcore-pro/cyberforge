"""Sites vitrines Next.js — génération de contenu et rendu scaffold."""

from tools.vitrine.build import VitrineBuildResult, build_vitrine_site
from tools.vitrine.content_agent import VitrineContentAgent, VitrineContentError
from tools.vitrine.content_schema import ClientBranding, VitrineSiteContent
from tools.vitrine.scaffold_renderer import ScaffoldRenderError, render_vitrine_scaffold
from tools.vitrine.unsplash_resolver import (
    UnsplashImageResolver,
    UnsplashResolveStats,
    resolve_vitrine_images,
)

__all__ = [
    "ClientBranding",
    "ScaffoldRenderError",
    "VitrineBuildResult",
    "VitrineContentAgent",
    "VitrineContentError",
    "VitrineSiteContent",
    "UnsplashImageResolver",
    "UnsplashResolveStats",
    "build_vitrine_site",
    "render_vitrine_scaffold",
    "resolve_vitrine_images",
]

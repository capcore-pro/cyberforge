"""Schéma Pydantic du contenu site vitrine (content/site.json)."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field, field_validator


class UnsplashImage(BaseModel):
    url: str = Field(min_length=10)
    alt: str = Field(min_length=3)
    imageQuery: str | None = Field(
        default=None,
        max_length=120,
        description="Terme de recherche Unsplash (résolu en Phase 4.2c).",
    )
    photographer: str | None = None
    photographerUrl: str | None = None


class NavItem(BaseModel):
    label: str
    href: str


class CtaLink(BaseModel):
    label: str
    href: str


class ServiceCard(BaseModel):
    title: str
    description: str
    href: str
    image: UnsplashImage


class Testimonial(BaseModel):
    quote: str
    author: str
    role: str
    rating: int = Field(ge=1, le=5)

    @field_validator("rating")
    @classmethod
    def _clamp_rating(cls, value: int) -> int:
        return max(1, min(5, value))


class ServiceSection(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str
    description: str
    bullets: list[str] = Field(default_factory=list)
    image: UnsplashImage


class SiteMeta(BaseModel):
    businessName: str
    tagline: str
    locale: str = Field(default="fr")
    primaryColor: str = Field(default="#0284c7")
    logoUrl: str | None = None


class HomeHero(BaseModel):
    title: str
    subtitle: str
    ctaPrimary: CtaLink
    ctaSecondary: CtaLink | None = None
    image: UnsplashImage


class HomeCtaBand(BaseModel):
    title: str
    text: str
    buttonLabel: str
    buttonHref: str


class HomeContent(BaseModel):
    hero: HomeHero
    servicesPreview: list[ServiceCard] = Field(min_length=1, max_length=6)
    testimonials: list[Testimonial] = Field(min_length=1, max_length=6)
    ctaBand: HomeCtaBand


class ServicesPageContent(BaseModel):
    intro: dict[str, str]
    sections: list[ServiceSection] = Field(min_length=1, max_length=8)

    @field_validator("intro")
    @classmethod
    def _intro_keys(cls, value: dict[str, str]) -> dict[str, str]:
        if "title" not in value or "description" not in value:
            raise ValueError("servicesPage.intro requiert title et description")
        return value


class ContactFields(BaseModel):
    name: str
    email: str
    message: str
    submit: str


class ContactSidebar(BaseModel):
    phone: str
    email: str
    hours: str
    address: str


class ContactPageContent(BaseModel):
    headline: str
    subtext: str
    fields: ContactFields
    successMessage: str
    sidebar: ContactSidebar


class FooterContent(BaseModel):
    description: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    socialLinks: list[dict[str, str]] = Field(default_factory=list)
    legalNote: str


class VitrineSiteContent(BaseModel):
    meta: SiteMeta
    navigation: list[NavItem] = Field(min_length=3, max_length=6)
    home: HomeContent
    servicesPage: ServicesPageContent
    contactPage: ContactPageContent
    footer: FooterContent


@dataclass(frozen=True)
class ClientBranding:
    """Branding optionnel issu d'une fiche client CyberForge."""

    name: str | None = None
    company: str | None = None
    email: str | None = None
    phone: str | None = None
    primary_color: str | None = None
    logo_url: str | None = None

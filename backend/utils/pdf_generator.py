"""
CyberForge — PDF Brief Generator
Génère le formulaire brief vidéo client au format PDF premium.
"""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generate_brief_pdf(
    client_name: str,
    client_email: str,
    client_company: str,
    secteur: str,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    DARK = colors.HexColor("#0f1117")
    GOLD = colors.HexColor("#f5c842")
    GREY = colors.HexColor("#6b7280")
    LIGHT = colors.HexColor("#f9fafb")
    WHITE = colors.white

    getSampleStyleSheet()

    title_style = ParagraphStyle(
        "title",
        fontSize=22,
        textColor=DARK,
        fontName="Helvetica-Bold",
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "subtitle",
        fontSize=11,
        textColor=GREY,
        fontName="Helvetica",
        alignment=TA_CENTER,
        spaceAfter=16,
    )
    section_style = ParagraphStyle(
        "section",
        fontSize=12,
        textColor=WHITE,
        fontName="Helvetica-Bold",
        alignment=TA_LEFT,
        backColor=DARK,
        leftIndent=8,
        spaceBefore=12,
        spaceAfter=6,
    )
    label_style = ParagraphStyle(
        "label",
        fontSize=10,
        textColor=DARK,
        fontName="Helvetica-Bold",
        spaceAfter=2,
    )

    story: list = []

    story.append(Paragraph("⚡ CyberForge", title_style))
    story.append(Paragraph("Brief Vidéo Publicitaire", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=12))

    info_data = [
        ["Client", client_name or "___________________________"],
        ["Email", client_email or "___________________________"],
        ["Entreprise", client_company or "___________________________"],
        ["Secteur", secteur.upper() if secteur else "___________________________"],
        ["Date", "___________________________"],
    ]
    info_table = Table(info_data, colWidths=[45 * mm, 125 * mm])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), DARK),
                ("TEXTCOLOR", (1, 0), (1, -1), GREY),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT, WHITE]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 12))

    def field_block(label: str, lines: int = 1) -> None:
        story.append(Paragraph(label, label_style))
        for _ in range(lines):
            story.append(
                HRFlowable(width="100%", thickness=0.5, color=GREY, spaceAfter=8)
            )

    story.append(Paragraph("1. VOTRE ACTIVITÉ", section_style))
    field_block("Décrivez votre activité / vos produits / vos services", 2)
    field_block("Votre public cible (âge, profil, besoins)", 2)
    field_block("Vos concurrents principaux")

    story.append(Paragraph("2. OBJECTIF DE LA VIDÉO", section_style))
    field_block("Quel est l'objectif principal ? (notoriété, ventes, recrutement...)")
    field_block("Où sera diffusée la vidéo ? (Instagram, YouTube, site web, TV...)")
    field_block("Avez-vous un message clé à transmettre ?", 2)

    story.append(Paragraph("3. IDENTITÉ VISUELLE", section_style))
    field_block("Couleurs de votre marque (codes couleur ou description)")
    field_block("Votre slogan / tagline")
    field_block("Avez-vous un logo ? (oui / non — si oui, l'envoyer par email)")

    story.append(Paragraph("4. STYLE & TON", section_style))
    field_block("Ton souhaité : ☐ Professionnel  ☐ Dynamique  ☐ Émotionnel  ☐ Luxe")
    field_block("Exemples de vidéos que vous aimez (liens YouTube / Instagram)")
    field_block("Ce que vous ne voulez PAS voir dans la vidéo")

    story.append(Paragraph("5. DÉTAILS TECHNIQUES", section_style))
    field_block("Durée souhaitée : ☐ 15s  ☐ 30s  ☐ 60s  ☐ Autre : _______")
    field_block("Format : ☐ 16:9 (YouTube/TV)  ☐ 9:16 (Stories/Reels)  ☐ 1:1 (Post)")
    field_block("Musique : ☐ Fournie par vous  ☐ Sélection CyberForge")
    field_block("Textes à afficher dans la vidéo (slogan, CTA, coordonnées...)", 2)

    story.append(Paragraph("6. BUDGET & DÉLAIS", section_style))
    field_block("Budget envisagé")
    field_block("Date de livraison souhaitée")
    field_block("Remarques ou informations complémentaires", 3)

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=GOLD, spaceAfter=6))
    story.append(
        Paragraph(
            "Formulaire à retourner complété par email · ⚡ CyberForge by CapCore · capcore.pro",
            ParagraphStyle(
                "footer", fontSize=8, textColor=GREY, alignment=TA_CENTER
            ),
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.read()

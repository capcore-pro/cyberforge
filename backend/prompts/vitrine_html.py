"""Règles HTML vitrine — BuilderAI, CodeGen, AutoFix."""

from __future__ import annotations

from prompts.shared import with_personalization

VITRINE_HTML_QUALITY_RULES = """
SITE VITRINE HTML — RÈGLES OBLIGATOIRES :
1. IDENTITÉ LITTÉRALE : le bloc « IDENTITÉ CLIENT » impose le nom EXACT dans <title> et dans le <h1>,
   au moins 3 mots-clés ResearchAI dans le corps <body>, plus secteur, ville, meta description et footer.
   Aucune autre marque ou nom inventé.
2. INTERDIT dans le HTML visible : lorem ipsum, "Lorem", "Votre texte ici", "Your text here",
   "Example Corp", "Entreprise XYZ", "Nom de l'entreprise", "Description du service",
   "Welcome to", "Acme", slogans génériques sans le vrai nom client.
3. CTA ET LIENS : chaque bouton/lien doit avoir une action réelle :
   - scroll : data-cf-action="scroll" data-cf-target="#contact" (ou #services, #hero)
   - contact : data-cf-action="contact"
   - téléphone : href="tel:+33..."
   - email : href="mailto:..."
   JAMAIS href="#" ou href="" seul sur un CTA.
4. CONTACT : section avec id="contact" contenant un formulaire id="cf-contact-form"
   (champs name, email, message + bouton submit). Le script CapCore enverra vers le backend.
5. NAVIGATION : ancres internes (#services, #contact, #about) avec sections id correspondants.
""".strip()

BUILDER_VITRINE_HTML_DIRECTIVE = VITRINE_HTML_QUALITY_RULES

"""
CyberForge — Video Sector Prompts
Bibliothèque de prompts cinématiques par secteur pour VideoAI client.
"""

SECTOR_ALIASES: dict[str, str] = {
    "restauration": "restaurant",
    "restaurant": "restaurant",
    "immobilier": "immobilier",
    "real_estate": "immobilier",
    "fitness": "fitness",
    "sport": "fitness",
    "gym": "fitness",
    "mode": "mode",
    "fashion": "mode",
    "automobile": "automobile",
    "auto": "automobile",
    "voiture": "automobile",
    "hotel": "hotel",
    "hôtel": "hotel",
    "hotellerie": "hotel",
    "medical": "medical",
    "santé": "medical",
    "sante": "medical",
    "clinique": "medical",
    "tech": "tech",
    "technologie": "tech",
    "saas": "tech",
    "artisan": "artisan",
    "artisanat": "artisan",
    "beaute": "beaute",
    "beauté": "beaute",
    "spa": "beaute",
}

SECTOR_PROMPTS = {
    "restaurant": {
        "scenes": [
            "Extreme close-up of a steaming gourmet dish being plated by a chef, golden hour natural lighting, shallow depth of field, cinematic warm tones, 4K ultra sharp",
            "Happy customers laughing and toasting around a beautifully set table, warm candlelight ambiance, bokeh background, soft golden lighting, elegant restaurant interior",
            "Fresh colorful ingredients in slow motion falling — tomatoes, herbs, olive oil drizzle — on rustic wooden surface, cinematic macro lens, vibrant saturated colors",
            "Aerial drone shot of a full terrace restaurant at sunset, people dining, string lights glowing, Mediterranean atmosphere, golden hour magic",
            "Chef smiling and presenting signature dish directly to camera, professional kitchen background with team working, confidence and passion, cinematic portrait",
        ],
        "ton_map": {
            "professionnel": "elegant fine dining, muted warm tones, slow paced",
            "dynamique": "fast cuts, vibrant colors, energetic kitchen atmosphere",
            "emotionnel": "family moments, shared laughter, intimate candlelight",
            "luxe": "Michelin star plating, gold accents, silent luxury aesthetic",
        },
    },
    "immobilier": {
        "scenes": [
            "Cinematic drone aerial shot rising above a luxury property at golden hour, manicured garden, infinity pool reflecting the sky, smooth tracking movement",
            "Slow dolly shot through a bright open-plan living room, floor-to-ceiling windows, natural light flooding polished marble floors, minimalist luxury interior",
            "Young couple walking hand in hand through a sun-drenched corridor, opening large double doors to reveal a stunning bedroom, soft natural light",
            "Close-up of architectural details — brushed brass handle, textured stone wall, panoramic window frame with city view beyond, premium materials",
            "Time-lapse of a property exterior from sunrise to golden sunset, warm light shifting across the facade, trees moving gently in breeze",
        ],
        "ton_map": {
            "professionnel": "clean neutral tones, architectural precision, calm pace",
            "dynamique": "fast aerial cuts, modern music, urban energy",
            "emotionnel": "family moving in, children running, new life beginning",
            "luxe": "silent luxury, no text rush, slow reveal, prestige materials",
        },
    },
    "fitness": {
        "scenes": [
            "Athlete in slow motion performing a perfect deadlift, dramatic side lighting, sweat drops visible, raw power and determination, dark industrial gym background",
            "Aerial view of a group fitness class in perfect synchronization, colorful mats, instructor leading with energy, modern bright studio",
            "Close-up of hands gripping pull-up bar, muscles tensing, camera slowly pulling back to reveal full body in motion, black and white high contrast",
            "Runner at sunrise on an empty road, fog lifting, silhouette against orange sky, motivational cinematic wide shot, epic scale",
            "Transformation split-screen — before relaxed posture vs after confident athletic stance, same person, same location, powerful contrast",
        ],
        "ton_map": {
            "professionnel": "clean white studio, precise movements, coaching authority",
            "dynamique": "fast cuts synced to beat, high energy, sweat and intensity",
            "emotionnel": "personal journey, struggle and triumph, authentic raw moments",
            "luxe": "premium equipment, high-end studio, elite athlete aesthetic",
        },
    },
    "mode": {
        "scenes": [
            "Model walking confidently on a rooftop at golden hour, fabric flowing in the wind, slow motion, cinematic wide shot with city skyline behind",
            "Extreme close-up of fabric texture, stitching details, zipper in slow motion, hands arranging collar — craftsmanship and quality storytelling",
            "Fashion editorial style — model posing in industrial loft, dramatic side lighting, high contrast black and white, powerful and minimal",
            "Behind the scenes atmosphere — stylist adjusting outfit, photographer shooting, creative energy, authentic documentary style",
            "Product flat lay animation — clothing items arranged perfectly, camera slowly pulling back, clean white background, premium brand aesthetic",
        ],
        "ton_map": {
            "professionnel": "editorial clean, neutral palette, confident minimal",
            "dynamique": "street style energy, fast cuts, urban backdrop",
            "emotionnel": "self-expression, identity, authentic personal style",
            "luxe": "haute couture pace, silence, extreme close-ups, prestige",
        },
    },
    "automobile": {
        "scenes": [
            "Cinematic low angle shot of car driving on empty coastal road at sunrise, camera tracking alongside, ocean in background, speed and freedom",
            "Slow motion close-up of wheel spinning, brake caliper visible, water splashing on wet road, dramatic side lighting, engineering precision",
            "Interior detail shots — leather steering wheel, dashboard lighting up, gear shift in slow motion, premium materials and craftsmanship",
            "Aerial drone chasing car through mountain pass curves, breathtaking landscape, power and agility combined, epic cinematic scale",
            "Car arriving and parking dramatically, door opening in slow motion revealing driver stepping out confidently, urban night setting with reflections",
        ],
        "ton_map": {
            "professionnel": "precision engineering focus, clean lines, technical authority",
            "dynamique": "speed cuts, adrenaline, racing energy, aggressive angles",
            "emotionnel": "freedom of the open road, adventure, life moments",
            "luxe": "silent reveal, reflections, prestige materials, no rush",
        },
    },
    "hotel": {
        "scenes": [
            "Sunrise drone shot of luxury hotel facade with pool terrace, ocean or mountain view beyond, complete silence and prestige, golden light",
            "Slow camera glide through a suite — from entrance to panoramic window, crisp white bed linen, perfectly arranged details, natural morning light",
            "Concierge greeting arriving guest with genuine warm smile, elegant lobby, marble floors, fresh flower arrangements, world-class hospitality",
            "Spa area — steam rising from infinity pool, candles, white towels rolled perfectly, total serenity and wellness atmosphere",
            "Restaurant breakfast scene — beautifully presented tray delivered to guest on private terrace with view, luxury morning ritual",
        ],
        "ton_map": {
            "professionnel": "service excellence, precision, trusted authority",
            "dynamique": "activities, spa, pool energy, guest experiences",
            "emotionnel": "romantic getaway, honeymoon, family memories",
            "luxe": "5-star silence, slow reveal, extreme detail close-ups",
        },
    },
    "medical": {
        "scenes": [
            "Doctor in white coat walking confidently through modern bright clinic corridor, natural light, reassuring and professional atmosphere",
            "Close-up of caring hands — doctor gently examining patient, warm human connection, trust and expertise, soft clinical lighting",
            "State-of-the-art medical equipment in operation, precise robotic movements, advanced technology, clean sterile environment",
            "Patient leaving clinic smiling and relieved, shaking hands with doctor, warm natural light outside, positive outcome and hope",
            "Team of medical professionals in brief consultation, collaborative expertise, modern conference room, confident and united",
        ],
        "ton_map": {
            "professionnel": "clinical authority, precision, trusted expertise",
            "dynamique": "innovation, cutting-edge tech, forward-thinking",
            "emotionnel": "patient journey, care, relief, human connection",
            "luxe": "premium private clinic, discretion, excellence",
        },
    },
    "tech": {
        "scenes": [
            "Developer hands typing on keyboard, code scrolling on multiple screens, dramatic dark room with blue light accents, focus and intensity",
            "Abstract data visualization — glowing nodes connecting across dark background, network growing, AI intelligence made visible",
            "Product demo on screen — clean UI animation, smooth transitions, user interacting effortlessly, problem solved in seconds",
            "Modern open-space tech office — diverse team collaborating around large screens, energetic startup atmosphere, innovation in progress",
            "Cinematic close-up of circuit board, camera flying over surface revealing complexity and precision, technology as art",
        ],
        "ton_map": {
            "professionnel": "B2B authority, clean demos, trusted partner",
            "dynamique": "startup energy, disruption, fast innovation",
            "emotionnel": "human impact of technology, lives improved",
            "luxe": "premium SaaS, enterprise, silent power",
        },
    },
    "artisan": {
        "scenes": [
            "Craftsman hands working on a piece — chisel on wood, throwing clay, cutting leather — extreme close-up, slow motion, raw authenticity",
            "Workshop environment — tools hanging perfectly arranged, sawdust in light beams, decades of expertise visible in every detail",
            "Finished product revealed — handmade object placed on natural surface, camera slowly revealing the complete piece, pride of creation",
            "Artisan looking up from work and smiling at camera, honest portrait, workshop background, genuine human story",
            "Time-lapse of creation process — raw material transforming into finished product, hands never stopping, mastery made visible",
        ],
        "ton_map": {
            "professionnel": "heritage and expertise, trusted quality, timeless",
            "dynamique": "creative energy, making process, satisfying craft",
            "emotionnel": "passion, life's work, human story behind the product",
            "luxe": "bespoke creation, rarity, collector's piece",
        },
    },
    "beaute": {
        "scenes": [
            "Extreme slow motion close-up of product application — serum drops on skin, lipstick gliding, powder brush sweeping — sensual and precise",
            "Model with glowing skin in soft natural window light, minimal makeup, radiance and confidence, clean beauty aesthetic",
            "Flat lay of premium beauty products arranged on marble surface, camera slowly pulling back, elegant brand universe",
            "Behind-the-scenes makeup artist at work, professional tools, artistry and precision, transformation in progress",
            "Before and after — subtle confident transformation, same woman, different light, authentic natural result",
        ],
        "ton_map": {
            "professionnel": "clinical efficacy, dermatology authority, results focus",
            "dynamique": "bold color, self-expression, trend-forward energy",
            "emotionnel": "self-confidence, inner beauty, authentic transformation",
            "luxe": "haute cosmétique, extreme close-ups, silence and sensuality",
        },
    },
}


def normalize_sector_key(secteur: str | None) -> str | None:
    if not secteur or not secteur.strip():
        return None
    key = secteur.strip().lower().replace("_", " ").replace("-", " ")
    if key in SECTOR_PROMPTS:
        return key
    return SECTOR_ALIASES.get(key)


def normalize_ton_key(ton: str | None) -> str:
    if not ton or not ton.strip():
        return "professionnel"
    key = ton.strip().lower()
    if key in ("pro", "corporate"):
        return "professionnel"
    return key


def get_prompts_for_brief(secteur: str, ton: str, nb_scenes: int = 5) -> list[str]:
    """
    Retourne les prompts adaptés au secteur et au ton du client.
    VideoAI les reçoit pour générer des scènes précises.
    """
    sector_key = normalize_sector_key(secteur) or "tech"
    sector_data = SECTOR_PROMPTS.get(sector_key, SECTOR_PROMPTS["tech"])
    scenes = list(sector_data["scenes"][:nb_scenes])
    ton_key = normalize_ton_key(ton)
    ton_instruction = sector_data["ton_map"].get(ton_key, "")

    if ton_instruction:
        scenes = [f"{scene} — Style: {ton_instruction}" for scene in scenes]

    return scenes


def format_sector_brief_block(secteur: str, ton: str, nb_scenes: int = 6) -> str:
    """Bloc texte injecté dans le user_prompt VideoAI."""
    sector_key = normalize_sector_key(secteur)
    if not sector_key:
        return ""

    prompts = get_prompts_for_brief(sector_key, ton, nb_scenes=nb_scenes)
    ton_key = normalize_ton_key(ton)
    lines = [
        f"SECTEUR CLIENT : {sector_key}",
        f"TON SOUHAITÉ : {ton_key}",
        "PROMPTS RÉFÉRENCE (adapter en 6 scènes JSON, sujet + lieu + action concrets) :",
    ]
    for index, prompt in enumerate(prompts, start=1):
        lines.append(f"{index}. {prompt}")
    if nb_scenes > len(prompts):
        lines.append(
            f"Génère {nb_scenes - len(prompts)} scène(s) supplémentaire(s) "
            "cohérente(s) avec le même secteur et ton."
        )
    return "\n".join(lines)


def get_available_sectors() -> list[str]:
    return list(SECTOR_PROMPTS.keys())

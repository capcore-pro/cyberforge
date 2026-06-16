"""
DeployAI — injection images Pexels + déploiement Cloudflare Pages (cyberforge-demos).
"""

from __future__ import annotations

import json
import logging
import re
from html import escape
from typing import Any

from agents.design_system_ai import build_design_system, inject_design_system_into_html
from config import get_settings
from tools.export_cloudflare import (
    CloudflareExportError,
    deploy_extension_demo,
    deploy_html_demo,
)
from tools.toolbox_media import PexelsImageRole, search_toolbox_photos
from tools.watermark import inject_watermark

logger = logging.getLogger(__name__)

_IMG_PEXELS_RE = re.compile(
    r"<img\b(?=[^>]*\bpexels-inject\b)([^>]*)/?>",
    re.IGNORECASE,
)
_CART_SCRIPT_RE = re.compile(
    r"<script\b[^>]*>[\s\S]*?(?:addToCart|window\.cart|renderCart)[\s\S]*?</script>",
    re.IGNORECASE,
)
_BODY_CLOSE_RE = re.compile(r"</body>", re.IGNORECASE)

CART_JS = r"""
<script>
window.cart=[];
function addToCart(btn){
  var card=btn.closest('[data-id]')||btn.closest('.product-card')||btn.parentElement;
  var id=card.dataset.id||card.dataset.productId||Math.random().toString(36).slice(2);
  var name=card.dataset.name||card.dataset.productName||card.querySelector('h3,h2,.product-name')?.textContent||'Produit';
  var price=parseFloat(card.dataset.price||card.dataset.productPrice||card.querySelector('.price,[class*="price"]')?.textContent?.replace(/[^\d.]/g,'')||0);
  var size=card.querySelector('select')?.value||'';
  var ex=window.cart.find(function(i){return i.id===id&&i.size===size;});
  if(ex){ex.qty++;}else{window.cart.push({id:id,name:name,price:price,qty:1,size:size});}
  renderCart();
}
function removeFromCart(id){window.cart=window.cart.filter(function(i){return i.id!==id;});renderCart();}
function updateQty(id,delta){var item=window.cart.find(function(i){return i.id===id;});if(item){item.qty+=delta;if(item.qty<=0)removeFromCart(id);else renderCart();}}
function renderCart(){
  var count=document.getElementById('cart-count');
  var items=document.getElementById('cart-items');
  var total=document.getElementById('cart-total');
  var n=window.cart.reduce(function(s,i){return s+i.qty;},0);
  if(count)count.textContent=n;
  if(!items)return;
  if(window.cart.length===0){items.innerHTML='<p style="text-align:center;color:#999;padding:20px">Votre panier est vide</p>';if(total)total.textContent='0.00 €';return;}
  items.innerHTML=window.cart.map(function(i){return '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #eee"><span>'+i.name+(i.size?' ('+i.size+')':'')+'</span><span><button onclick="updateQty(\''+i.id+'\',-1)" style="width:24px;height:24px;cursor:pointer;border:1px solid #ddd;background:#fff;border-radius:4px">−</button> '+i.qty+' <button onclick="updateQty(\''+i.id+'\',1)" style="width:24px;height:24px;cursor:pointer;border:1px solid #ddd;background:#fff;border-radius:4px">+</button> <strong>'+( i.price*i.qty).toFixed(2)+'€</strong> <button onclick="removeFromCart(\''+i.id+'\')" style="color:red;margin-left:8px;cursor:pointer;border:none;background:none">✕</button></span></div>';}).join('');
  var t=window.cart.reduce(function(s,i){return s+i.price*i.qty;},0);
  if(total)total.textContent=t.toFixed(2)+' €';
}
function filterProducts(cat){
  document.querySelectorAll('.product-card,[data-category]').forEach(function(card){
    var c=(card.dataset.category||'').toLowerCase();
    card.style.display=(cat==='tous'||cat==='all'||cat==='toutes'||c.includes(cat.toLowerCase()))?'':'none';
  });
}
function submitOrder(){
  if(window.cart.length===0){alert('Votre panier est vide.');return;}
  var fields=document.querySelectorAll('#order-form [required],#commande [required]');
  for(var i=0;i<fields.length;i++){if(!fields[i].value.trim()){fields[i].focus();alert('Veuillez remplir tous les champs.');return;}}
  window.cart=[];renderCart();
  var s=document.getElementById('order-success');
  if(s){s.style.display='block';}else{alert('Commande confirmée ! Merci.');}
}
document.addEventListener('DOMContentLoaded',function(){renderCart();});
</script>
"""
_ALT_RE = re.compile(r"""\balt=(["'])(.*?)\1""", re.IGNORECASE | re.DOTALL)
_SRC_RE = re.compile(r"""\bsrc=(["'])(.*?)\1""", re.IGNORECASE)

# (mots-clés dans alt/titre, requête Pexels) — ordre : plus spécifique en premier
_CAMPING_LODGING_QUERIES: list[tuple[tuple[str, ...], str]] = [
    (("mobil-home", "mobil home", "mobile home", "mobilhome"), "mobile home camping exterior"),
    (("chalet",), "wooden chalet forest"),
    (("tente", "emplacement tente"), "camping tent nature"),
    (("emplacement",), "campsite grass trees"),
    (("caravane", "caravan"), "caravan camping site"),
]


def _is_extension_project(project_type: str | None) -> bool:
    return (project_type or "").strip().lower().replace("-", "_") == "extension_navigateur"


def build_extension_demo_page(
    *,
    extension_name: str,
    client_name: str,
    primary_color: str = "#4f46e5",
    zip_href: str = "./extension.zip",
) -> str:
    """Page Cloudflare de démo : instructions + lien téléchargement ZIP."""
    title = escape((extension_name or client_name or "Extension").strip())
    primary = escape((primary_color or "#4f46e5").strip())
    safe_zip = escape(zip_href, quote=True)
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Extension {title} — prête à installer</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: Inter, system-ui, sans-serif;
      background: #0f1117; color: #e2e8f0; min-height: 100vh;
      display: flex; align-items: center; justify-content: center; padding: 24px;
    }}
    .wrap {{
      max-width: 520px; width: 100%;
      background: #1e2535; border: 1px solid rgba(255,255,255,0.08);
      border-radius: 16px; padding: 32px;
    }}
    h1 {{ font-size: 1.5rem; margin-bottom: 8px; }}
    p {{ color: #8892a4; line-height: 1.6; margin-bottom: 16px; }}
    ol {{ margin: 0 0 24px 20px; color: #cbd5e1; line-height: 1.8; }}
    .btn {{
      display: inline-block; padding: 14px 28px; border-radius: 8px;
      background: {primary}; color: #fff; text-decoration: none; font-weight: 600;
    }}
    .btn:hover {{ opacity: 0.92; }}
    footer {{ margin-top: 28px; font-size: 12px; color: #64748b; }}
  </style>
</head>
<body>
  <main class="wrap">
    <h1>Extension {title} — prête à installer</h1>
    <p>Téléchargez l'archive ZIP et chargez l'extension dans Chrome (mode développeur).</p>
    <ol>
      <li>Ouvrez <code>chrome://extensions</code></li>
      <li>Activez le <strong>Mode développeur</strong></li>
      <li>Cliquez sur <strong>Charger l'extension non empaquetée</strong></li>
      <li>Décompressez le ZIP et sélectionnez le dossier</li>
    </ol>
    <a class="btn" href="{safe_zip}" download="extension.zip">Télécharger le ZIP</a>
    <footer>Manifest V3 — généré par CyberForge</footer>
  </main>
</body>
</html>"""


def _is_ecommerce_project(project_type: str | None) -> bool:
    pt = (project_type or "").strip().lower().replace("-", "_")
    return pt in ("ecommerce", "saas_dashboard")


def inject_cart_js(html: str) -> str:
    """Remplace les scripts panier générés par un bloc JS fiable avant déploiement."""
    print("[DeployAI] inject_cart_js appelée")
    raw = (html or "").strip()
    if not raw:
        print("[DeployAI] inject_cart_js: HTML vide, skip")
        return raw

    print("[DeployAI] HTML avant injection:", raw[:200])
    removed = len(_CART_SCRIPT_RE.findall(raw))
    cleaned = _CART_SCRIPT_RE.sub("", raw)
    body_m = _BODY_CLOSE_RE.search(cleaned)
    if not body_m:
        logger.warning("[DeployAI] inject_cart_js: balise </body> absente")
        out = cleaned.rstrip() + "\n" + CART_JS.strip() + "\n"
    else:
        pos = body_m.start()
        out = cleaned[:pos] + CART_JS + "\n" + cleaned[pos:]

    print("[DeployAI] HTML après injection:", out[-500:])
    if removed:
        logger.info("[DeployAI] %d script(s) panier remplacé(s)", removed)
    logger.info("[DeployAI] JS panier injecté avant </body>")
    return out


def inject_stripe_checkout(
    html: str,
    *,
    project_type: str | None,
    payment_config: dict[str, Any] | None,
) -> str:
    """Injecte Stripe.js + redirectToCheckout si clé publishable présente (e-commerce)."""
    if not _is_ecommerce_project(project_type):
        return html

    pk = ""
    if isinstance(payment_config, dict):
        pk = str(payment_config.get("publishable_key") or "").strip()
    if not pk or not pk.startswith("pk_"):
        return html

    raw = (html or "").strip()
    if not raw:
        return html

    pk_js = json.dumps(pk)
    stripe_block = f"""
<script src="https://js.stripe.com/v3/"></script>
<script>
(function() {{
  var stripe = Stripe({pk_js});
  window.submitOrder = function() {{
    if (!window.cart || !window.cart.length) return;
    stripe.redirectToCheckout({{
      lineItems: window.cart.map(function(item) {{
        return {{
          price_data: {{
            currency: 'eur',
            product_data: {{ name: item.name }},
            unit_amount: Math.round(item.price * 100)
          }},
          quantity: item.qty
        }};
      }}),
      mode: 'payment',
      successUrl: window.location.href + '?payment=success',
      cancelUrl: window.location.href + '?payment=cancelled'
    }});
  }};
  document.addEventListener('DOMContentLoaded', function() {{
    var params = new URLSearchParams(window.location.search);
    var status = params.get('payment');
    if (!status) return;
    var banner = document.createElement('div');
    banner.style.cssText = 'position:sticky;top:0;z-index:9999;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px;font-size:14px;font-weight:600;';
    if (status === 'success') {{
      banner.style.background = '#065f46';
      banner.style.color = '#ecfdf5';
      banner.textContent = 'Paiement confirmé — merci pour votre commande !';
    }} else if (status === 'cancelled') {{
      banner.style.background = '#b45309';
      banner.style.color = '#fffbeb';
      banner.textContent = 'Paiement annulé — votre panier a été conservé.';
    }} else {{
      return;
    }}
    var close = document.createElement('button');
    close.type = 'button';
    close.setAttribute('aria-label', 'Fermer');
    close.textContent = '×';
    close.style.cssText = 'background:transparent;border:none;color:inherit;font-size:20px;line-height:1;cursor:pointer;padding:0 4px;';
    close.addEventListener('click', function() {{ banner.remove(); }});
    banner.appendChild(close);
    document.body.insertBefore(banner, document.body.firstChild);
  }});
}})();
</script>
"""
    body_m = _BODY_CLOSE_RE.search(raw)
    if not body_m:
        out = raw.rstrip() + "\n" + stripe_block.strip() + "\n"
    else:
        pos = body_m.start()
        out = raw[:pos] + stripe_block + "\n" + raw[pos:]

    logger.info("[DeployAI] Stripe Checkout injecté (e-commerce)")
    return out


def _is_camping_reservation_context(*, sector: str | None, project_type: str | None) -> bool:
    pt = (project_type or "").strip().lower().replace("-", "_")
    if pt == "site_reservation":
        return True
    sec = (sector or "").strip().lower()
    return "camping" in sec or "plein air" in sec or "hebergement" in sec


def _pexels_query_for_alt(
    alt: str,
    *,
    sector: str | None,
    project_type: str | None,
) -> str:
    """Choisit une requête Pexels selon le type d'hébergement (alt / titre)."""
    text = (alt or "").strip().lower()
    if not text:
        return "business professional"
    if _is_camping_reservation_context(sector=sector, project_type=project_type):
        for keywords, query in _CAMPING_LODGING_QUERIES:
            if any(kw in text for kw in keywords):
                return query
    return (alt or "").strip()


def _detect_pexels_image_role(attrs: str, html: str, position: int) -> PexelsImageRole:
    """Hero/slider → large2x ; cards hébergements → large."""
    combined = (attrs or "").lower()
    start = max(0, position - 600)
    snippet = (html[start:position] + " " + combined).lower()
    hero_markers = (
        "hero-slide",
        "hero-slider",
        'class="hero',
        "class='hero",
        "hero ",
    )
    if any(m in snippet or m in combined for m in hero_markers):
        return "hero"
    card_markers = (
        "hebergement-card",
        "hebergement",
        "lodging-card",
        "accommodation-card",
        "data-hebergement",
        "#hebergements",
    )
    if any(m in snippet or m in combined for m in card_markers):
        return "card"
    return "default"


async def _pexels_url_for_alt(
    alt: str,
    *,
    sector: str | None,
    project_type: str | None = None,
    image_role: PexelsImageRole = "default",
) -> str | None:
    query = _pexels_query_for_alt(alt, sector=sector, project_type=project_type)
    settings = get_settings()
    _, photos = await search_toolbox_photos(
        query[:80],
        secteur=sector,
        per_page=3,
        pexels_image_role=image_role,
        settings=settings,
    )
    if not photos:
        return None
    photo = photos[0]
    return (photo.url_full or photo.url_download or "").strip() or None


def _set_img_src(attrs: str, url: str) -> str:
    safe_url = escape(url, quote=True)
    if _SRC_RE.search(attrs):
        return _SRC_RE.sub(f'src="{safe_url}"', attrs, count=1)
    return f'{attrs} src="{safe_url}"'


async def inject_pexels_images(
    html: str,
    *,
    sector: str | None = None,
    project_type: str | None = None,
) -> str:
    """Remplace les src des <img class=\"pexels-inject\"> par des URLs Pexels CDN."""
    index = 0

    async def _replace(match: re.Match[str]) -> str:
        nonlocal index
        attrs = match.group(1) or ""
        alt_m = _ALT_RE.search(attrs)
        alt = (alt_m.group(2) if alt_m else "").strip() or f"image {index + 1}"
        role = _detect_pexels_image_role(attrs, html, match.start())
        url = await _pexels_url_for_alt(
            alt,
            sector=sector,
            project_type=project_type,
            image_role=role,
        )
        index += 1
        if not url:
            return match.group(0)
        attrs = _set_img_src(attrs, url)
        closing = "/" if match.group(0).rstrip().endswith("/>") else ""
        return f"<img{attrs}{closing}>"

    out = html
    for m in list(_IMG_PEXELS_RE.finditer(html)):
        replacement = await _replace(m)
        out = out.replace(m.group(0), replacement, 1)
    if index:
        logger.info("[DeployAI] %d image(s) Pexels injectée(s)", index)
    return out


class DeployAI:
    async def run_extension(
        self,
        zip_bytes: bytes,
        *,
        extension_name: str = "",
        client_name: str = "",
        primary_color: str = "#4f46e5",
        project_type: str = "extension_navigateur",
    ) -> dict[str, Any]:
        if not zip_bytes:
            return {"url": "", "success": False, "error": "ZIP extension vide"}

        name = (extension_name or client_name or "Extension").strip()
        demo_html = build_extension_demo_page(
            extension_name=name,
            client_name=client_name or name,
            primary_color=primary_color,
            zip_href="./extension.zip",
        )
        demo_title = f"Extension {name}"[:120]

        try:
            production_url, demo_token, _demo_password, unlock_url = await deploy_extension_demo(
                demo_html=demo_html,
                zip_bytes=zip_bytes,
                title=demo_title,
                project_type=project_type,
            )
            return {
                "url": production_url,
                "success": True,
                "demo_token": demo_token,
                "demo_password": "",
                "unlock_url": unlock_url,
                "html": demo_html,
                "extension_zip_bytes": len(zip_bytes),
            }
        except CloudflareExportError as exc:
            logger.error("[DeployAI] extension Cloudflare: %s", exc)
            return {
                "url": "",
                "success": False,
                "error": str(exc),
                "html": demo_html,
            }

    async def run(
        self,
        html: str,
        *,
        title: str = "",
        sector: str | None = None,
        project_type: str | None = None,
        payment_config: dict[str, Any] | None = None,
        design_system: dict[str, Any] | None = None,
        brief: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if _is_extension_project(project_type):
            return {
                "url": "",
                "success": False,
                "error": "Utiliser run_extension() pour extension_navigateur",
            }

        raw = (html or "").strip()
        if not raw:
            return {"url": "", "success": False, "error": "HTML vide"}

        enriched = await inject_pexels_images(
            raw,
            sector=sector,
            project_type=project_type,
        )
        if _is_ecommerce_project(project_type):
            print(
                f"[DeployAI] e-commerce détecté (project_type={project_type!r}) "
                "— injection panier avant Cloudflare",
            )
            enriched = inject_cart_js(enriched)
            enriched = inject_stripe_checkout(
                enriched,
                project_type=project_type,
                payment_config=payment_config,
            )
            print(f"[DeployAI] enriched réassigné, taille HTML={len(enriched)}")
        else:
            print(
                f"[DeployAI] inject_cart_js ignorée (project_type={project_type!r})",
            )
        ds = design_system if isinstance(design_system, dict) and design_system else None
        if not ds and isinstance(brief, dict):
            ds = brief.get("design_system")
        if not ds and isinstance(brief, dict):
            ds = build_design_system(brief)
        if ds:
            enriched = inject_design_system_into_html(enriched, ds)
        enriched = inject_watermark(enriched)
        demo_title = (title or "CyberForge Demo").strip()[:120]

        try:
            production_url, demo_token, demo_password, unlock_url = await deploy_html_demo(
                html=enriched,
                title=demo_title,
                project_type=(project_type or "vitrine_next").strip(),
            )
            return {
                "url": production_url,
                "success": True,
                "demo_token": demo_token,
                "demo_password": demo_password,
                "unlock_url": unlock_url,
                "html": enriched,
            }
        except CloudflareExportError as exc:
            logger.error("[DeployAI] Cloudflare: %s", exc)
            return {
                "url": "",
                "success": False,
                "error": str(exc),
                "html": enriched,
            }

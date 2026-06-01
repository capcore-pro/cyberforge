"""
Images produits e-commerce — miniatures Unsplash + repli si Pexels / chargement échoue.
"""

from __future__ import annotations

import re

# URLs stables Unsplash (secteur boulangerie / pâtisserie)
_ECOMMERCE_ALIMENTAIRE_IMAGES: tuple[str, ...] = (
    "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=800&q=80",
    "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800&q=80",
    "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=800&q=80",
    "https://images.unsplash.com/photo-1486427943681-8ddb4dedf9ea?w=800&q=80",
    "https://images.unsplash.com/photo-1608198093002-4fd9ac503252?w=800&q=80",
    "https://images.unsplash.com/photo-1517433670267-08bbd4be890f?w=800&q=80",
)

_ECOMMERCE_MODE_IMAGES: tuple[str, ...] = (
    "https://images.unsplash.com/photo-1445205170230-053b83016050?w=800&q=80",
    "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=800&q=80",
    "https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=800&q=80",
    "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=800&q=80",
    "https://images.unsplash.com/photo-1483985988351-763728e1935b?w=800&q=80",
    "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=800&q=80",
)

_ECOMMERCE_DEFAULT_IMAGES: tuple[str, ...] = (
    "https://images.unsplash.com/photo-1472851291508-755d8d195ffd?w=800&q=80",
    "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=800&q=80",
    "https://images.unsplash.com/photo-1556740758-90de374c12ef?w=800&q=80",
    "https://images.unsplash.com/photo-1563013544-824ae1b704d3?w=800&q=80",
    "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800&q=80",
    "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&q=80",
)

_IMAGES_BY_TEMPLATE: dict[str, tuple[str, ...]] = {
    "ecommerce_alimentaire": _ECOMMERCE_ALIMENTAIRE_IMAGES,
    "ecommerce_mode": _ECOMMERCE_MODE_IMAGES,
    "ecommerce_default": _ECOMMERCE_DEFAULT_IMAGES,
}

_PRODUCT_THUMB_RE = re.compile(
    r'(<article\b[^>]*\bclass=["\'][^"\']*product-card[^"\']*["\'][^>]*>\s*'
    r'<div\s+class=["\']thumb["\'][^>]*>)([\s\S]*?)(</div>)',
    re.IGNORECASE,
)

_FALLBACK_SCRIPT = """
<script id="cf-ecom-img-fallback">
(function () {
  var pools = {
    boulangerie: %s,
    mode: %s,
    default: %s
  };
  function poolFor(img) {
    var t = (img.getAttribute("data-cf-sector") || "boulangerie").toLowerCase();
    return pools[t] || pools.default;
  }
  function applyFallback(img) {
    var list = poolFor(img);
    var idx = parseInt(img.getAttribute("data-cf-img-idx") || "0", 10) || 0;
    var url = list[idx %% list.length];
    if (url && img.src !== url) img.src = url;
  }
  document.querySelectorAll(".product-card .thumb img").forEach(function (img) {
    img.addEventListener("error", function () { applyFallback(img); });
    if (!img.getAttribute("src") || img.complete && img.naturalWidth === 0) {
      applyFallback(img);
    }
  });
})();
</script>
"""


def _image_pool_for_template(template_id: str) -> tuple[str, ...]:
    return _IMAGES_BY_TEMPLATE.get(
        template_id, _IMAGES_BY_TEMPLATE["ecommerce_default"]
    )


def _sector_key(template_id: str) -> str:
    if template_id == "ecommerce_alimentaire":
        return "boulangerie"
    if template_id == "ecommerce_mode":
        return "mode"
    return "default"


def ensure_ecommerce_product_thumbnails(html: str, template_id: str) -> str:
    """Injecte une <img> dans chaque .product-card .thumb vide ou sans src."""
    if not html or "product-card" not in html:
        return html
    pool = _image_pool_for_template(template_id)
    sector = _sector_key(template_id)
    index = 0

    def replacer(match: re.Match[str]) -> str:
        nonlocal index
        open_tag, inner, close_tag = match.group(1), match.group(2), match.group(3)
        url = pool[index % len(pool)]
        index += 1
        if re.search(r"<img\b", inner, re.I):
            inner = re.sub(
                r'(<img\b[^>]*\bsrc=["\'])([^"\']*)(["\'])',
                rf"\1{url}\3",
                inner,
                count=1,
                flags=re.I,
            )
            if "data-cf-sector" not in inner.lower():
                inner = re.sub(
                    r"<img\b",
                    f'<img data-cf-sector="{sector}" data-cf-img-idx="{index - 1}"',
                    inner,
                    count=1,
                    flags=re.I,
                )
            return f"{open_tag}{inner}{close_tag}"
        return (
            f'{open_tag}<img src="{url}" alt="" loading="lazy" '
            f'data-cf-sector="{sector}" data-cf-img-idx="{index - 1}" />{close_tag}'
        )

    out = _PRODUCT_THUMB_RE.sub(replacer, html)
    if 'id="cf-ecom-img-fallback"' not in out and index > 0:
        import json

        script = _FALLBACK_SCRIPT % (
            json.dumps(list(_ECOMMERCE_ALIMENTAIRE_IMAGES)),
            json.dumps(list(_ECOMMERCE_MODE_IMAGES)),
            json.dumps(list(_ECOMMERCE_DEFAULT_IMAGES)),
        )
        if re.search(r"</body>", out, re.I):
            out = re.sub(r"</body>", script + "\n</body>", out, count=1, flags=re.I)
        else:
            out += script
    return out

/** Paramètre URL — bypass écran « Démo protégée » pour Mat dans CyberForge. */
export const CYBERFORGE_INTERNAL_PREVIEW_QUERY = "preview=cyberforge_internal";

/** HTML suffisant pour iframe srcDoc (template-first, vitrine, ecommerce). */
export function isUsablePreviewHtml(html: string | null | undefined): boolean {
  const s = html?.trim();
  if (!s || s.length < 200) return false;
  const low = s.toLowerCase();
  return low.includes("<!doctype") || low.includes("<html");
}

/** Premier candidat HTML exploitable (aperçu interne, pas l’URL /demo/{token}). */
export function pickPreviewHtml(
  ...candidates: Array<string | null | undefined>
): string | null {
  for (const c of candidates) {
    if (isUsablePreviewHtml(c)) return c!.trim();
  }
  return null;
}

export function withCyberforgeInternalPreview(url: string): string {
  const raw = url.trim();
  if (!raw) return raw;
  try {
    const parsed = new URL(raw);
    if (!parsed.protocol.startsWith("http")) return raw;
    if (parsed.searchParams.get("preview") === "cyberforge_internal") {
      return raw;
    }
    parsed.searchParams.set("preview", "cyberforge_internal");
    return parsed.toString();
  } catch {
    const sep = raw.includes("?") ? "&" : "?";
    if (raw.includes(CYBERFORGE_INTERNAL_PREVIEW_QUERY)) return raw;
    return `${raw}${sep}${CYBERFORGE_INTERNAL_PREVIEW_QUERY}`;
  }
}

const INTERNAL_PREVIEW_HIDE_LOCK =
  '<style id="cf-internal-preview-chrome">#cf-lock-btn,.cf-lock-btn{display:none!important;visibility:hidden!important;pointer-events:none!important;height:0!important;overflow:hidden!important}</style>';

function stripLockButtonChrome(html: string): string {
  let doc = html.replace(
    /<button\b[^>]*\bid\s*=\s*["']?cf-lock-btn["']?[^>]*>[\s\S]*?<\/button>/gi,
    "",
  );
  doc = doc.replace(
    /<button\b[^>]*\bclass\s*=\s*["'][^"']*\bcf-lock-btn\b[^"']*["'][^>]*>[\s\S]*?<\/button>/gi,
    "",
  );
  if (!doc.includes('id="cf-internal-preview-chrome"')) {
    if (/<head\b/i.test(doc)) {
      doc = doc.replace(/<head([^>]*)>/i, `<head$1>${INTERNAL_PREVIEW_HIDE_LOCK}`);
    } else if (/<body\b/i.test(doc)) {
      doc = doc.replace(/<body([^>]*)>/i, `<body$1>${INTERNAL_PREVIEW_HIDE_LOCK}`);
    } else {
      doc = INTERNAL_PREVIEW_HIDE_LOCK + doc;
    }
  }
  return doc;
}

/** Aperçu in-app (iframe srcDoc) — sans écran mot de passe ni bouton Verrouiller. */
export function prepareInternalPreviewSrcDoc(html: string): string {
  const body = html.trim();
  if (!body) {
    return body;
  }
  const unlock = `<script>(function(){function u(){var l=document.getElementById("cf-login-screen");var d=document.getElementById("cf-demo-content");if(l&&d){l.style.display="none";d.classList.add("cf-unlocked");d.removeAttribute("aria-hidden");}var b=document.getElementById("cf-lock-btn");if(b){b.remove();}document.querySelectorAll(".cf-lock-btn").forEach(function(n){n.remove();});}window.unlockDemo=u;if(document.readyState==="loading"){document.addEventListener("DOMContentLoaded",u);}else{u();}})();</script>`;
  let doc = body;
  if (body.toLowerCase().includes("cf-login-screen")) {
    if (/<\/body>/i.test(doc)) {
      doc = doc.replace(/<\/body>/i, `${unlock}</body>`);
    } else if (/<head\b/i.test(doc)) {
      doc = doc.replace(/<head([^>]*)>/i, `<head$1>${unlock}`);
    } else {
      doc = unlock + doc;
    }
  }
  return stripLockButtonChrome(doc);
}

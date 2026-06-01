/** Paramètre URL — bypass écran « Démo protégée » pour Mat dans CyberForge. */
export const CYBERFORGE_INTERNAL_PREVIEW_QUERY = "preview=cyberforge_internal";

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

/** Déverrouille l'écran mot de passe pour iframe srcDoc (pas d'URL). */
export function prepareInternalPreviewSrcDoc(html: string): string {
  const body = html.trim();
  if (!body || !body.toLowerCase().includes("cf-login-screen")) {
    return body;
  }
  const unlock = `<script>(function(){var l=document.getElementById("cf-login-screen");var d=document.getElementById("cf-demo-content");if(l&&d){l.style.display="none";d.classList.add("cf-unlocked");d.removeAttribute("aria-hidden");}})();</script>`;
  if (/<head\b/i.test(body)) {
    return body.replace(/<head([^>]*)>/i, `<head$1>${unlock}`);
  }
  return unlock + body;
}

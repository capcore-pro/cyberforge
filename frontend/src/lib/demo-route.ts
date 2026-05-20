/** Extrait le token démo depuis l'URL publique /demo/{token}. */
export function getPublicDemoToken(): string | null {
  const match = window.location.pathname.match(/^\/demo\/([^/]+)\/?$/);
  const token = match?.[1]?.trim();
  return token || null;
}

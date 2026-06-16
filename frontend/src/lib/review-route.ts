/** Extrait le token review depuis l'URL publique /review/{token}. */
export function getPublicReviewToken(): string | null {
  const match = window.location.pathname.match(/^\/review\/([^/]+)\/?$/);
  const token = match?.[1]?.trim();
  return token || null;
}

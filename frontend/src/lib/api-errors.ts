/** Extrait un message d'erreur lisible depuis une réponse API. */
export function apiErrorMessage(
  response: { status: number; statusText: string; data: unknown },
  offline: string,
): string {
  if (response.status === 0) return offline;
  if (
    response.data &&
    typeof response.data === "object" &&
    "detail" in response.data
  ) {
    return String((response.data as { detail: unknown }).detail);
  }
  return `Erreur ${response.status} : ${response.statusText}`;
}

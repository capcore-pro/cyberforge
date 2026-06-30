/** Extrait un message d'erreur lisible depuis une réponse API. */
export function apiErrorMessage(
  response: { status: number; statusText: string; data: unknown },
  offline: string,
): string {
  if (response.status === 0) {
    const fromData = formatApiErrorDetail(response.data);
    const fromStatusText = response.statusText?.trim();
    if (fromData) return fromData;
    if (fromStatusText) return fromStatusText;
    return offline;
  }
  return formatApiErrorDetail(response.data) || `Erreur ${response.status} : ${response.statusText}`;
}

/** Formate le champ `detail` FastAPI (string, objet ou tableau). */
export function formatApiErrorDetail(data: unknown): string {
  if (data === null || data === undefined) return "";

  if (typeof data === "string") {
    if (data === "Not Found") {
      return "Route API introuvable (404). Vérifiez VITE_API_BASE_URL (sans /api final) et redémarrez le backend.";
    }
    return data;
  }

  if (Array.isArray(data)) {
    return data.map((item) => formatApiErrorDetail(item)).filter(Boolean).join("\n");
  }

  if (typeof data !== "object") return String(data);

  const record = data as Record<string, unknown>;

  if ("detail" in record) {
    return formatApiErrorDetail(record.detail);
  }

  const lines: string[] = [];

  if (record.message) lines.push(String(record.message));
  if (record.operation) lines.push(`Opération : ${String(record.operation)}`);
  if (record.method && record.url) {
    lines.push(`${String(record.method)} ${String(record.url)}`);
  } else if (record.url) {
    lines.push(`URL : ${String(record.url)}`);
  }
  if (record.upstream_status_code) {
    lines.push(`PostgREST HTTP ${String(record.upstream_status_code)}`);
  } else if (record.status_code) {
    lines.push(`HTTP ${String(record.status_code)}`);
  }
  if (record.fastapi_route_registered) {
    lines.push("Route FastAPI /api/projects : enregistrée");
  }
  if (record.hint) lines.push(`Piste : ${String(record.hint)}`);
  if (record.response_body) lines.push(`Réponse Supabase :\n${String(record.response_body)}`);
  if (record.diagnostics) {
    lines.push(`Diagnostics :\n${JSON.stringify(record.diagnostics, null, 2)}`);
  }
  if (record.route) lines.push(`Route : ${String(record.route)}`);

  if (lines.length > 0) return lines.join("\n\n");

  return JSON.stringify(record, null, 2);
}

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  ""
).replace(/\/$/, "");

export async function switchToAutonome(
  clientId: string,
): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/api/portal-onboarding/back-to-autonome`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: clientId }),
  });
  return res.json();
}

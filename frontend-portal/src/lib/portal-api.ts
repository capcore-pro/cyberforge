const API_BASE = import.meta.env.VITE_API_URL || "";

export interface PortalClient {
  id: string;
  email: string;
  full_name: string;
  company: string;
  plan: string;
}

export interface PortalSite {
  id: string;
  site_name: string;
  site_url: string | null;
  html_content: string | null;
  sector: string | null;
  project_type: string;
  status: string;
}

export interface LoginResponse {
  success: boolean;
  client: PortalClient;
  sites: PortalSite[];
}

export async function portalLogin(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/api/portal/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  const data = (await res.json()) as LoginResponse & { detail?: string };
  if (!res.ok) {
    throw new Error(
      typeof data.detail === "string" ? data.detail : "Connexion impossible",
    );
  }
  return data;
}

export async function saveAndDeploy(payload: {
  site_id: string;
  client_id: string;
  edits: Array<{
    type: string;
    selector: string;
    old_value: string;
    new_value: string;
  }>;
  html_updated: string;
}): Promise<{ success: boolean; url?: string; edits_saved?: number }> {
  const res = await fetch(`${API_BASE}/api/portal/save-deploy`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || "Enregistrement impossible");
  }
  return data;
}

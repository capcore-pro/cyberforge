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

export interface ClientFeatures {
  plan: string;
  management_plan: string;
  can_edit_colors: boolean;
  can_edit_fonts: boolean;
  can_edit_sections: boolean;
}

export interface ModificationRequestPayload {
  client_id: string;
  site_id: string;
  type_modification: string;
  description: string;
  priorite: "normale" | "urgente";
}

export async function getMyFeatures(clientId: string): Promise<ClientFeatures> {
  const res = await fetch(`${API_BASE}/api/portal/my-features/${clientId}`);
  const data = await res.json();
  return {
    plan: data.plan,
    management_plan: data.management_plan,
    can_edit_colors: data.can_edit_colors,
    can_edit_fonts: data.can_edit_fonts,
    can_edit_sections: data.can_edit_sections,
  };
}

export async function delegateToCapcore(
  clientId: string,
  siteId: string,
): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/api/portal-onboarding/delegate-to-capcore`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: clientId, site_id: siteId }),
  });
  return res.json();
}

export async function sendModificationRequest(
  payload: ModificationRequestPayload,
): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/api/portal-onboarding/modification-request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export interface MediaItem {
  id: string;
  file_name: string;
  r2_url: string;
  file_type: string;
  file_size_bytes: number | null;
  uploaded_by: string;
  created_at: string;
}

export interface MediaListResponse {
  media: MediaItem[];
  count: number;
  limit: number;
  plan: string | null;
}

export async function uploadPortalMedia(
  clientId: string,
  file: File,
  siteId?: string,
  uploadedBy: string = "client",
): Promise<{ success: boolean; r2_url: string; media_id: string }> {
  const formData = new FormData();
  formData.append("client_id", clientId);
  formData.append("uploaded_by", uploadedBy);
  formData.append("file", file);
  if (siteId) formData.append("site_id", siteId);
  const res = await fetch(`${API_BASE}/api/portal/media/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      typeof err.detail === "string" ? err.detail : "Erreur upload photo",
    );
  }
  return res.json();
}

export async function fetchPortalMedia(
  clientId: string,
): Promise<MediaListResponse> {
  const res = await fetch(`${API_BASE}/api/portal/media/${clientId}`);
  if (!res.ok) throw new Error("Erreur chargement photos");
  return res.json();
}

export async function deletePortalMedia(mediaId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/portal/media/${mediaId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Erreur suppression photo");
}

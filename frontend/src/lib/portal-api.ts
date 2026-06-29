import { buildBackendApiUrl } from "@/lib/backend-url";

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
  const res = await fetch(buildBackendApiUrl("/api/portal/media/upload"), {
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
  const res = await fetch(buildBackendApiUrl(`/api/portal/media/${clientId}`));
  if (!res.ok) throw new Error("Erreur chargement photos");
  return res.json();
}

export async function deletePortalMedia(mediaId: string): Promise<void> {
  const res = await fetch(buildBackendApiUrl(`/api/portal/media/${mediaId}`), {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Erreur suppression photo");
}

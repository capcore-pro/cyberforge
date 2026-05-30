import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

const CMS = `${API_PREFIX}/cms`;

export interface CmsProjectSettings {
  project_id: string;
  cms_enabled: boolean;
  cms_login_url: string | null;
  site_url: string | null;
}

export function fetchCmsProjectSettings(projectId: string) {
  return apiRequest<CmsProjectSettings>({
    method: "GET",
    path: `${CMS}/projects/${encodeURIComponent(projectId)}/settings`,
  });
}

export function patchCmsProjectSettings(projectId: string, cms_enabled: boolean) {
  return apiRequest<CmsProjectSettings>({
    method: "PATCH",
    path: `${CMS}/projects/${encodeURIComponent(projectId)}/settings`,
    body: { cms_enabled },
  });
}

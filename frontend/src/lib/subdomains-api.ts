import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export interface SubdomainCreateResult {
  subdomain: string;
  url: string;
  dns_record_id: string;
  status: "created" | "already_exists";
  project_update_warning?: string;
}

export interface SubdomainRecord {
  name: string;
  content: string;
  id: string;
  created_on: string;
}

export async function createSubdomain(body: {
  client_name: string;
  project_id?: string;
}) {
  return apiRequest<SubdomainCreateResult>({
    method: "POST",
    path: `${API_PREFIX}/subdomains/create`,
    body,
  });
}

export async function deleteSubdomain(clientName: string) {
  return apiRequest<{ deleted: boolean; client_name: string }>({
    method: "DELETE",
    path: `${API_PREFIX}/subdomains/${encodeURIComponent(clientName)}`,
  });
}

export async function listSubdomains() {
  return apiRequest<{ items: SubdomainRecord[]; count: number }>({
    method: "GET",
    path: `${API_PREFIX}/subdomains`,
  });
}

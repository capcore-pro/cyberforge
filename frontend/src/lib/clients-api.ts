import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export type DemoStatusSlug = "envoyee" | "ouverte" | "validee" | "expiree";
export type ClientKind = "client" | "perso";

export interface ClientRecord {
  id: string;
  kind: ClientKind;
  name: string;
  company: string | null;
  email: string | null;
  phone: string | null;
  primary_color: string | null;
  logo_url: string | null;
  created_at: string;
}

export interface ClientDemoRecord {
  id: string;
  token: string;
  title: string;
  status: DemoStatusSlug;
  created_at: string;
  expires_at: string;
  opened_at: string | null;
  unlock_url: string | null;
}

export interface ClientDetail extends ClientRecord {
  demos: ClientDemoRecord[];
}

export interface ClientBranding {
  client_id: string;
  kind?: ClientKind;
  name: string;
  company: string | null;
  primary_color: string | null;
  logo_data_url: string | null;
}

export interface ClientPayload {
  kind?: ClientKind;
  name: string;
  company?: string | null;
  email?: string | null;
  phone?: string | null;
  primary_color?: string | null;
  logo_url?: string | null;
}

export const DEMO_STATUS_LABELS: Record<DemoStatusSlug, string> = {
  envoyee: "Envoyée",
  ouverte: "Ouverte",
  validee: "Validée",
  expiree: "Expirée",
};

export async function listClients(kind?: ClientKind) {
  const query = kind ? `?kind=${encodeURIComponent(kind)}` : "";
  return apiRequest<ClientRecord[]>({
    method: "GET",
    path: `${API_PREFIX}/clients${query}`,
  });
}

export async function fetchClientDetail(clientId: string) {
  return apiRequest<ClientDetail>({
    method: "GET",
    path: `${API_PREFIX}/clients/${clientId}`,
  });
}

export async function createClient(body: ClientPayload) {
  return apiRequest<ClientRecord>({
    method: "POST",
    path: `${API_PREFIX}/clients`,
    body,
  });
}

export async function updateClient(clientId: string, body: Partial<ClientPayload>) {
  return apiRequest<ClientRecord>({
    method: "PATCH",
    path: `${API_PREFIX}/clients/${clientId}`,
    body,
  });
}

export async function deleteClient(clientId: string) {
  return apiRequest<{ deleted: boolean }>({
    method: "DELETE",
    path: `${API_PREFIX}/clients/${clientId}`,
  });
}

export async function fetchClientBranding(clientId: string) {
  return apiRequest<ClientBranding>({
    method: "GET",
    path: `${API_PREFIX}/clients/${clientId}/branding`,
  });
}

export async function updateDemoStatus(demoId: string, status: "validee" | "expiree") {
  return apiRequest<{ id: string; status: DemoStatusSlug }>({
    method: "PATCH",
    path: `${API_PREFIX}/demos/${demoId}/status`,
    body: { status },
  });
}

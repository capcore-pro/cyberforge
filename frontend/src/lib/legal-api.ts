import {
  API_PREFIX,
  DEFAULT_API_BASE_URL,
  normalizeBackendBaseUrl,
} from "@shared/constants";
import type { ProjectRecord } from "@shared/types";
import { apiRequest } from "@/lib/api-client";

const LEGAL = `${API_PREFIX}/legal`;

export type DocumentType = "devis" | "facture" | "mentions_legales" | "cgv";
export type DocumentStatus =
  | "draft"
  | "sent"
  | "signed"
  | "paid"
  | "cancelled";

export interface LegalClient {
  id: string;
  name: string;
  email: string;
  phone: string | null;
  address: string | null;
  siret: string | null;
  created_at: string;
}

export interface LineItem {
  id: string;
  document_id: string;
  description: string;
  quantity: number;
  unit_price: number;
  total: number;
  order: number;
}

export interface LegalDocument {
  id: string;
  type: DocumentType;
  number: string;
  client_id: string | null;
  project_id: string | null;
  status: DocumentStatus;
  title: string;
  notes: string | null;
  total_ht: number;
  tva_rate: number;
  total_ttc: number;
  pdf_path: string | null;
  pdf_url: string | null;
  sent_at: string | null;
  created_at: string;
  line_items: LineItem[];
}

export interface LineItemInput {
  description: string;
  quantity: number;
  unit_price: number;
  order?: number;
}

export interface PdfResult {
  pdf_path: string;
  pdf_url: string;
}

export interface CgvResult {
  document: LegalDocument;
  pdf_path: string;
  pdf_url: string;
  created: boolean;
}

export function resolveLegalUrl(pathOrUrl: string): string {
  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
    return pathOrUrl;
  }
  if (import.meta.env.DEV) {
    return pathOrUrl;
  }
  const base = normalizeBackendBaseUrl(
    import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL,
  );
  return `${base}${pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`}`;
}

export async function fetchLegalClients() {
  return apiRequest<LegalClient[]>({ method: "GET", path: `${LEGAL}/clients` });
}

export async function createLegalClient(body: {
  name: string;
  email: string;
  phone?: string | null;
  address?: string | null;
  siret?: string | null;
}) {
  return apiRequest<LegalClient>({
    method: "POST",
    path: `${LEGAL}/clients`,
    body,
  });
}

export async function updateLegalClient(
  id: string,
  body: Partial<{
    name: string;
    email: string;
    phone: string | null;
    address: string | null;
    siret: string | null;
  }>,
) {
  return apiRequest<LegalClient>({
    method: "PUT",
    path: `${LEGAL}/clients/${id}`,
    body,
  });
}

export async function deleteLegalClient(id: string) {
  return apiRequest<void>({
    method: "DELETE",
    path: `${LEGAL}/clients/${id}`,
  });
}

export async function fetchLegalDocuments(params?: {
  type?: DocumentType;
  status?: DocumentStatus;
  client_id?: string;
}) {
  const q = new URLSearchParams();
  if (params?.type) q.set("type", params.type);
  if (params?.status) q.set("status", params.status);
  if (params?.client_id) q.set("client_id", params.client_id);
  const qs = q.toString();
  return apiRequest<LegalDocument[]>({
    method: "GET",
    path: `${LEGAL}/documents${qs ? `?${qs}` : ""}`,
  });
}

export async function createLegalDocument(body: {
  type: "devis" | "facture";
  title: string;
  client_id?: string | null;
  project_id?: string | null;
  status?: DocumentStatus;
  notes?: string | null;
  tva_rate?: number;
  line_items?: LineItemInput[];
}) {
  return apiRequest<LegalDocument>({
    method: "POST",
    path: `${LEGAL}/documents`,
    body,
  });
}

export async function updateLegalDocument(
  id: string,
  body: Partial<{
    title: string;
    notes: string | null;
    status: DocumentStatus;
    client_id: string | null;
    project_id: string | null;
    line_items: LineItemInput[];
  }>,
) {
  return apiRequest<LegalDocument>({
    method: "PUT",
    path: `${LEGAL}/documents/${id}`,
    body,
  });
}

export async function deleteLegalDocument(id: string) {
  return apiRequest<void>({
    method: "DELETE",
    path: `${LEGAL}/documents/${id}`,
  });
}

export async function updateDocumentStatus(id: string, status: DocumentStatus) {
  return apiRequest<LegalDocument>({
    method: "PUT",
    path: `${LEGAL}/documents/${id}/status`,
    body: { status },
  });
}

export async function generateDocumentPdf(id: string) {
  return apiRequest<PdfResult>({
    method: "POST",
    path: `${LEGAL}/documents/${id}/generate-pdf`,
  });
}

export async function sendLegalDocument(
  id: string,
  body: { message: string; subject?: string },
) {
  return apiRequest<{
    sent: boolean;
    to: string;
    subject: string;
    pdf_path: string;
    sent_at: string;
  }>({
    method: "POST",
    path: `${LEGAL}/documents/${id}/send`,
    body,
  });
}

export async function createDocumentFromProject(projectId: string) {
  return apiRequest<LegalDocument>({
    method: "POST",
    path: `${LEGAL}/documents/from-project/${projectId}`,
  });
}

export async function generateMentionsLegales(projectId: string) {
  return apiRequest<PdfResult>({
    method: "POST",
    path: `${LEGAL}/mentions-legales/${projectId}`,
  });
}

export async function generateOrGetCgv() {
  return apiRequest<CgvResult>({
    method: "POST",
    path: `${LEGAL}/cgv`,
  });
}

export async function fetchProjectsForLegal() {
  return apiRequest<ProjectRecord[]>({
    method: "GET",
    path: `${API_PREFIX}/projects`,
  });
}

export function openPdfDownload(doc: LegalDocument) {
  const url = resolveLegalUrl(
    doc.pdf_url || `${LEGAL}/documents/${doc.id}/pdf`,
  );
  window.open(url, "_blank", "noopener,noreferrer");
}

export async function convertDevisToFacture(devis: LegalDocument) {
  return createLegalDocument({
    type: "facture",
    title: devis.title,
    client_id: devis.client_id,
    project_id: devis.project_id,
    status: "draft",
    notes: devis.notes,
    tva_rate: devis.tva_rate,
    line_items: devis.line_items.map((line, idx) => ({
      description: line.description,
      quantity: line.quantity,
      unit_price: line.unit_price,
      order: idx,
    })),
  });
}

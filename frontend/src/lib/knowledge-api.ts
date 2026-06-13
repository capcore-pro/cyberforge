import { API_PREFIX } from "@shared/constants";
import type { ApiResponsePayload } from "@shared/ipc";
import { apiRequest } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-errors";
import { buildBackendApiUrl } from "@/lib/backend-url";
import type { BadgeVariant } from "@/components/ui/Badge";

const KNOWLEDGE = `${API_PREFIX}/knowledge`;

export const KNOWLEDGE_ALLOWED_EXTENSIONS = [".txt", ".md", ".pdf"] as const;
export const KNOWLEDGE_MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

export interface KnowledgeDocument {
  id: string;
  title: string;
  source_type: string;
  language: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeChunk {
  chunk_id: string;
  document_id: string;
  document_title: string;
  content: string;
  similarity?: number;
  combined_score?: number;
  rerank_score?: number;
}

export interface IngestResult {
  document_id: string;
  chunks_count: number;
  status: string;
}

function normalizeDocument(row: Record<string, unknown>): KnowledgeDocument {
  const created = String(row.created_at ?? "");
  return {
    id: String(row.id ?? ""),
    title: String(row.title ?? ""),
    source_type: String(row.source_type ?? "manual"),
    language: String(row.language ?? "fr"),
    status: String(row.status ?? "active"),
    created_at: created,
    updated_at: String(row.updated_at ?? created),
  };
}

function normalizeChunk(row: Record<string, unknown>): KnowledgeChunk {
  return {
    chunk_id: String(row.chunk_id ?? ""),
    document_id: String(row.document_id ?? ""),
    document_title: String(row.document_title ?? ""),
    content: String(row.content ?? ""),
    similarity:
      row.similarity != null ? Number(row.similarity) : undefined,
    combined_score:
      row.combined_score != null ? Number(row.combined_score) : undefined,
    rerank_score:
      row.rerank_score != null ? Number(row.rerank_score) : undefined,
  };
}

export function sourceTypeBadgeVariant(sourceType: string): BadgeVariant {
  const key = sourceType.trim().toLowerCase();
  if (key === "pdf") return "blue";
  if (key === "uploaded") return "teal";
  return "gray";
}

export function chunkScoreValue(chunk: KnowledgeChunk): number | null {
  if (chunk.combined_score != null && !Number.isNaN(chunk.combined_score)) {
    return chunk.combined_score;
  }
  if (chunk.similarity != null && !Number.isNaN(chunk.similarity)) {
    return chunk.similarity;
  }
  if (chunk.rerank_score != null && !Number.isNaN(chunk.rerank_score)) {
    return chunk.rerank_score;
  }
  return null;
}

export function scoreBadgeVariant(score: number): BadgeVariant {
  if (score > 0.7) return "teal";
  if (score >= 0.4) return "amber";
  return "gray";
}

export function truncateChunkContent(content: string, max = 150): string {
  const trimmed = content.trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max).trimEnd()}…`;
}

export function isKnowledgeFileAllowed(file: File): boolean {
  const name = file.name.toLowerCase();
  return KNOWLEDGE_ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export function titleFromFilename(filename: string): string {
  const base = filename.replace(/\.[^.]+$/, "").trim();
  return base || "Document";
}

export async function fetchDocuments(
  project_id?: string,
): Promise<KnowledgeDocument[]> {
  const q = new URLSearchParams();
  if (project_id?.trim()) q.set("project_id", project_id.trim());
  const suffix = q.toString() ? `?${q}` : "";
  const res = await apiRequest<unknown[]>({
    method: "GET",
    path: `${KNOWLEDGE}/documents${suffix}`,
  });
  if (!res.ok) {
    throw new Error(
      apiErrorMessage(res, "Impossible de charger les documents."),
    );
  }
  const rows = Array.isArray(res.data) ? res.data : [];
  return rows.map((row) =>
    normalizeDocument(row as Record<string, unknown>),
  );
}

export async function ingestText(
  title: string,
  content: string,
  project_id?: string,
): Promise<IngestResult> {
  const res = await apiRequest<IngestResult>({
    method: "POST",
    path: `${KNOWLEDGE}/ingest`,
    body: {
      title: title.trim(),
      content,
      project_id: project_id?.trim() || undefined,
    },
  });
  if (!res.ok || !res.data) {
    throw new Error(apiErrorMessage(res, "Indexation texte impossible."));
  }
  return res.data;
}

export async function ingestFile(
  file: File,
  title: string,
  project_id?: string,
  onProgress?: (percent: number) => void,
): Promise<IngestResult> {
  if (!isKnowledgeFileAllowed(file)) {
    throw new Error("Formats acceptés : .txt, .md, .pdf");
  }
  if (file.size > KNOWLEDGE_MAX_UPLOAD_BYTES) {
    throw new Error("Fichier trop volumineux (max 20 Mo).");
  }

  const form = new FormData();
  form.append("file", file);
  form.append("title", title.trim());
  if (project_id?.trim()) {
    form.append("project_id", project_id.trim());
  }

  const url = buildBackendApiUrl(`${KNOWLEDGE}/ingest-file`);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);

    xhr.upload.onprogress = (event) => {
      if (!onProgress || !event.lengthComputable) return;
      const pct = Math.round((event.loaded / event.total) * 100);
      onProgress(Math.min(100, pct));
    };

    xhr.onload = () => {
      let data: IngestResult | null = null;
      try {
        data = JSON.parse(xhr.responseText) as IngestResult;
      } catch {
        data = null;
      }
      if (xhr.status >= 200 && xhr.status < 300 && data) {
        onProgress?.(100);
        resolve(data);
        return;
      }
      const detail =
        (data as unknown as { detail?: string })?.detail ??
        xhr.responseText ??
        "Upload impossible.";
      reject(new Error(String(detail)));
    };

    xhr.onerror = () => reject(new Error("Erreur réseau lors de l'upload."));
    xhr.onabort = () => reject(new Error("Upload annulé."));
    xhr.send(form);
  });
}

export async function searchKnowledge(
  query: string,
  project_id?: string,
  limit = 10,
): Promise<KnowledgeChunk[]> {
  const res = await apiRequest<unknown[]>({
    method: "POST",
    path: `${KNOWLEDGE}/search`,
    body: {
      query: query.trim(),
      project_id: project_id?.trim() || undefined,
      limit,
    },
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Recherche impossible."));
  }
  const rows = Array.isArray(res.data) ? res.data : [];
  return rows.map((row) => normalizeChunk(row as Record<string, unknown>));
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await apiRequest<{ ok?: boolean }>({
    method: "DELETE",
    path: `${KNOWLEDGE}/documents/${encodeURIComponent(id)}`,
  });
  if (!res.ok) {
    throw new Error(apiErrorMessage(res, "Suppression impossible."));
  }
}

/** Variante non bloquante pour la recherche (erreurs silencieuses côté UI). */
export async function searchKnowledgeSafe(
  query: string,
  project_id?: string,
  limit = 10,
): Promise<ApiResponsePayload<KnowledgeChunk[]>> {
  try {
    const data = await searchKnowledge(query, project_id, limit);
    return { ok: true, status: 200, statusText: "OK", data };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Recherche impossible.";
    return {
      ok: false,
      status: 0,
      statusText: message,
      data: [],
    };
  }
}

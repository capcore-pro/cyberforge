import type { CoreMindRunResponse, ProjectType } from "@shared/types";

const STORAGE_KEY = "cyberforge_generation_history";
const MAX_ENTRIES = 40;

export interface GenerationHistoryEntry {
  id: string;
  createdAt: string;
  prompt: string;
  projectType: ProjectType;
  result: CoreMindRunResponse;
}

function readAll(): GenerationHistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isHistoryEntry);
  } catch {
    return [];
  }
}

function isHistoryEntry(value: unknown): value is GenerationHistoryEntry {
  if (!value || typeof value !== "object") return false;
  const entry = value as GenerationHistoryEntry;
  return (
    typeof entry.id === "string" &&
    typeof entry.createdAt === "string" &&
    typeof entry.prompt === "string" &&
    typeof entry.projectType === "string" &&
    entry.result !== null &&
    typeof entry.result === "object"
  );
}

function writeAll(entries: GenerationHistoryEntry[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

/** Enregistre une génération réussie (plus récent en tête). */
export function saveGenerationToHistory(
  prompt: string,
  projectType: ProjectType,
  result: CoreMindRunResponse,
): GenerationHistoryEntry {
  const entry: GenerationHistoryEntry = {
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    prompt,
    projectType,
    result,
  };

  const next = [entry, ...readAll()].slice(0, MAX_ENTRIES);
  writeAll(next);
  return entry;
}

export function listGenerationHistory(): GenerationHistoryEntry[] {
  return readAll();
}

export function removeGenerationFromHistory(id: string): void {
  writeAll(readAll().filter((entry) => entry.id !== id));
}

export function clearGenerationHistory(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function formatHistoryDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

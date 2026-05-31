const STORAGE_KEY = "cyberforge.researchEnabled";

/** Recherche de contenu activée par défaut. */
export function isResearchEnabled(): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return true;
    return raw === "true";
  } catch {
    return true;
  }
}

export function setResearchEnabled(enabled: boolean): void {
  localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
}

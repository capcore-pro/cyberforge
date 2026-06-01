const STORAGE_KEY = "cyberforge.stitchEnabled";

/** Maquettes StitchAI activées par défaut. */
export function isStitchEnabled(): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return true;
    return raw === "true";
  } catch {
    return true;
  }
}

export function setStitchEnabled(enabled: boolean): void {
  localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
}

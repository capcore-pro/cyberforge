const STORAGE_KEY = "cyberforge.lighthouseEnabled";

/** Audit Lighthouse activé par défaut. */
export function isLighthouseEnabled(): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return true;
    return raw === "true";
  } catch {
    return true;
  }
}

export function setLighthouseEnabled(enabled: boolean): void {
  localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
}

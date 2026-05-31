const STORAGE_KEY = "cyberforge.playwrightEnabled";

/** Tests Playwright activés par défaut. */
export function isPlaywrightEnabled(): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return true;
    return raw === "true";
  } catch {
    return true;
  }
}

export function setPlaywrightEnabled(enabled: boolean): void {
  localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
}

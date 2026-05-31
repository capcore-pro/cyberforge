const STORAGE_KEY = "cyberforge.openhandsEnabled";

/** OpenHands activé par défaut (utilise la clé Anthropic existante). */
export function isOpenHandsEnabled(): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return true;
    return raw === "true";
  } catch {
    return true;
  }
}

export function setOpenHandsEnabled(enabled: boolean): void {
  localStorage.setItem(STORAGE_KEY, enabled ? "true" : "false");
}

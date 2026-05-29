const FIRST_NAME_KEY = "cf_user_first_name";

/** Prénom affiché sur le tableau de bord (Paramètres → Général). */
export function getUserFirstName(): string {
  try {
    const stored = localStorage.getItem(FIRST_NAME_KEY)?.trim();
    if (stored) return stored;
  } catch {
    /* localStorage indisponible */
  }
  return "Mat";
}

export function setUserFirstName(name: string): void {
  try {
    const clean = name.trim();
    if (clean) localStorage.setItem(FIRST_NAME_KEY, clean);
    else localStorage.removeItem(FIRST_NAME_KEY);
  } catch {
    /* ignore */
  }
}

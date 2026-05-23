const STORAGE_KEY = "cyberforge:demo_client_id";

export function setSelectedClientId(clientId: string | null): void {
  if (!clientId) {
    sessionStorage.removeItem(STORAGE_KEY);
    return;
  }
  sessionStorage.setItem(STORAGE_KEY, clientId);
}

export function getSelectedClientId(): string | null {
  const value = sessionStorage.getItem(STORAGE_KEY);
  return value?.trim() ? value : null;
}

export function clearSelectedClientId(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}

/** Événement global après enregistrement de clés dans le coffre. */
export const SECRETS_SAVED_EVENT = "cyberforge:secrets-saved";

export function notifySecretsSaved(): void {
  window.dispatchEvent(new CustomEvent(SECRETS_SAVED_EVENT));
}

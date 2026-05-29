import type { CockpitService } from "@/lib/cockpit-api";

export function balanceOf(service: CockpitService): number {
  return Number(service.balance?.balance_eur ?? 0);
}

/** Solde à 0 jamais initialisé (aucune sync ni recharge enregistrée). */
export function isBalanceUninitialized(service: CockpitService): boolean {
  if (balanceOf(service) !== 0) return false;
  const synced = service.balance?.last_synced_at;
  return synced == null || String(synced).trim() === "";
}

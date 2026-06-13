export const colors = {
  bg: "#0d0d0d",
  card: "#111111",
  cardSecondary: "#161616",
  border: "#222222",
  gold: "#c9a84c",
  goldHover: "#e0be6a",
  textPrimary: "#f0f0f0",
  textSecondary: "#888888",
  textMuted: "#444444",
  success: "#4caf50",
  warning: "#e8a020",
  error: "#ef4444",
  info: "#5b8dd9",
  teal: "#10b981",
  purple: "#8b5cf6",
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
};

export const radius = {
  sm: 6,
  md: 10,
  lg: 16,
  full: 999,
};

export const PROSPECT_STATUTS = [
  "nouveau",
  "contacté",
  "démo_envoyée",
  "négociation",
  "gagné",
  "perdu",
] as const;

export type ProspectStatut = (typeof PROSPECT_STATUTS)[number];

export const STATUT_LABELS: Record<ProspectStatut, string> = {
  nouveau: "Nouveau",
  contacté: "Contacté",
  démo_envoyée: "Démo envoyée",
  négociation: "Négociation",
  gagné: "Gagné",
  perdu: "Perdu",
};

export const STATUT_COLORS: Record<ProspectStatut, string> = {
  nouveau: colors.textSecondary,
  contacté: colors.info,
  démo_envoyée: colors.warning,
  négociation: colors.purple,
  gagné: colors.teal,
  perdu: colors.error,
};

export const PROJECT_TYPE_LABELS: Record<string, string> = {
  vitrine_next: "Vitrine",
  ecommerce: "E-commerce",
  site_reservation: "Réservation",
  application_web: "App web",
  application_desktop: "Desktop",
  extension_navigateur: "Extension",
  real_app: "React",
};

export function nextStatut(current: string): ProspectStatut | null {
  const idx = PROSPECT_STATUTS.indexOf(current as ProspectStatut);
  if (idx < 0 || idx >= PROSPECT_STATUTS.length - 1) return null;
  return PROSPECT_STATUTS[idx + 1];
}

/** Pages accessibles dans l'application desktop. */
export type AppPage =
  | "dashboard"
  | "cockpit"
  | "media_library"
  | "legal"
  | "generator"
  | "projects"
  | "vitrines"
  | "application_web"
  | "extensions"
  | "site_reservation"
  | "ecommerce"
  | "clients"
  | "perso"
  | "agents"
  | "tools"
  | "reports"
  | "settings";

export interface NavItem {
  id: AppPage;
  label: string;
  icon: string;
  enabled: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Tableau de bord", icon: "◈", enabled: true },
  { id: "cockpit", label: "Cockpit", icon: "◐", enabled: true },
  { id: "media_library", label: "Médiathèque", icon: "▥", enabled: true },
  { id: "legal", label: "Légal", icon: "⚖", enabled: true },
  { id: "generator", label: "Générateur", icon: "⚡", enabled: true },
  { id: "projects", label: "Projets", icon: "▤", enabled: true },
  { id: "vitrines", label: "Vitrines", icon: "▦", enabled: true },
  { id: "application_web", label: "Apps web", icon: "▣", enabled: true },
  { id: "extensions", label: "Extensions", icon: "⬢", enabled: true },
  { id: "site_reservation", label: "Réservation", icon: "◷", enabled: true },
  { id: "ecommerce", label: "Ecommerce", icon: "▧", enabled: true },
  { id: "clients", label: "Clients", icon: "◎", enabled: true },
  { id: "perso", label: "Perso", icon: "◉", enabled: true },
  { id: "agents", label: "Agents", icon: "◇", enabled: false },
  { id: "tools", label: "Outils", icon: "⬡", enabled: false },
  { id: "reports", label: "Rapports", icon: "◫", enabled: false },
  { id: "settings", label: "Paramètres", icon: "⚙", enabled: true },
];

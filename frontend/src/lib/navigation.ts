/** Pages accessibles dans l'application desktop. */
export type AppPage =
  | "dashboard"
  | "cockpit"
  | "media_library"
  | "accounting"
  | "newsletter"
  | "generator"
  | "projects"
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

/** Navigation principale (hors Paramètres, épinglé en bas de la barre latérale). */
export const PRIMARY_NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Tableau de bord", icon: "◈", enabled: true },
  { id: "cockpit", label: "Cockpit", icon: "◐", enabled: true },
  { id: "media_library", label: "Médiathèque", icon: "▥", enabled: true },
  { id: "accounting", label: "Comptabilité", icon: "€", enabled: true },
  { id: "newsletter", label: "Newsletter", icon: "✉", enabled: true },
  { id: "generator", label: "Générateur", icon: "⚡", enabled: true },
  { id: "projects", label: "Projets", icon: "▤", enabled: true },
  { id: "clients", label: "Clients", icon: "◎", enabled: true },
  { id: "perso", label: "Perso", icon: "◉", enabled: true },
  { id: "agents", label: "Agents", icon: "◇", enabled: false },
  { id: "tools", label: "Outils", icon: "⬡", enabled: false },
  { id: "reports", label: "Rapports", icon: "◫", enabled: false },
];

export const SETTINGS_NAV_ITEM: NavItem = {
  id: "settings",
  label: "Paramètres",
  icon: "⚙",
  enabled: true,
};

/** Liste complète (tests, compatibilité). */
export const NAV_ITEMS: NavItem[] = [
  ...PRIMARY_NAV_ITEMS,
  SETTINGS_NAV_ITEM,
];

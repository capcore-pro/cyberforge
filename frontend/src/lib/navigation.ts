/** Pages accessibles dans l'application desktop. */
export type AppPage =
  | "dashboard"
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

export const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Tableau de bord", icon: "◈", enabled: true },
  { id: "generator", label: "Générateur", icon: "⚡", enabled: true },
  { id: "projects", label: "Projets", icon: "▤", enabled: true },
  { id: "clients", label: "Clients", icon: "◎", enabled: true },
  { id: "perso", label: "Perso", icon: "◉", enabled: true },
  { id: "agents", label: "Agents", icon: "◇", enabled: false },
  { id: "tools", label: "Outils", icon: "⬡", enabled: false },
  { id: "reports", label: "Rapports", icon: "◫", enabled: false },
  { id: "settings", label: "Paramètres", icon: "⚙", enabled: true },
];

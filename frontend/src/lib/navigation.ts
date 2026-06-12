/** Pages accessibles dans l'application desktop. */
export type AppPage =
  | "dashboard"
  | "generator"
  | "projects"
  | "clients"
  | "accounting"
  | "newsletter"
  | "media_library"
  | "settings"
  /** Routes internes (hors sidebar) */
  | "perso"
  | "agents"
  | "monitoring"
  | "tools"
  | "reports";

export interface NavItem {
  id: AppPage;
  label: string;
  icon: string;
  /** Classe Tabler Icons (ex. ti ti-robot) — prioritaire sur `icon` si défini */
  iconClass?: string;
  enabled: boolean;
}

export interface NavGroup {
  id: string;
  items: NavItem[];
}

/** Bloc principal — activité CapCore. */
export const MAIN_NAV_GROUP: NavGroup = {
  id: "main",
  items: [
    { id: "dashboard", label: "Accueil", icon: "◈", enabled: true },
    { id: "generator", label: "Générateur", icon: "⚡", enabled: true },
    { id: "projects", label: "Projets", icon: "▤", enabled: true },
    {
      id: "agents",
      label: "Agents IA",
      icon: "◉",
      iconClass: "ti ti-robot",
      enabled: true,
    },
    {
      id: "monitoring",
      label: "Monitoring",
      icon: "◉",
      iconClass: "ti ti-activity",
      enabled: true,
    },
    { id: "perso", label: "Perso", icon: "◇", enabled: true },
    { id: "clients", label: "Clients", icon: "◎", enabled: true },
    { id: "accounting", label: "Comptabilité", icon: "€", enabled: true },
    { id: "newsletter", label: "Newsletter", icon: "✉", enabled: true },
  ],
};

/** Outils infra — séparés visuellement dans la sidebar. */
export const SECONDARY_NAV_GROUP: NavGroup = {
  id: "secondary",
  items: [
    { id: "media_library", label: "Médiathèque", icon: "▥", enabled: true },
  ],
};

export const SIDEBAR_NAV_GROUPS: NavGroup[] = [
  MAIN_NAV_GROUP,
  SECONDARY_NAV_GROUP,
];

/** Liste plate (tests, compatibilité). */
export const PRIMARY_NAV_ITEMS: NavItem[] = SIDEBAR_NAV_GROUPS.flatMap(
  (g) => g.items,
);

export const SETTINGS_NAV_ITEM: NavItem = {
  id: "settings",
  label: "Paramètres",
  icon: "⚙",
  enabled: true,
};

/** Liste complète sidebar + paramètres. */
export const NAV_ITEMS: NavItem[] = [
  ...PRIMARY_NAV_ITEMS,
  SETTINGS_NAV_ITEM,
];

/** Pages routées dans App.tsx (sidebar + routes internes). */
export const ROUTED_PAGES: AppPage[] = [
  ...PRIMARY_NAV_ITEMS.map((i) => i.id),
  SETTINGS_NAV_ITEM.id,
];

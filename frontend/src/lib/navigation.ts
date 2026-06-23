/** Pages accessibles dans l'application desktop. */
export type AppPage =
  | "dashboard"
  | "generator"
  | "projects"
  | "clients"
  | "pipeline"
  | "accounting"
  | "newsletter"
  | "media_library"
  | "knowledge"
  | "settings"
  /** Routes internes (hors sidebar) */
  | "perso"
  | "agents"
  | "agent_builder"
  | "mobile_builder"
  | "desktop_builder"
  | "erp_builder"
  | "video_builder"
  | "video_client"
  | "monitoring"
  | "workflows"
  | "editor"
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
      id: "agent_builder",
      label: "Agent Builder",
      icon: "◉",
      iconClass: "ti ti-bot",
      enabled: true,
    },
    {
      id: "monitoring",
      label: "Monitoring",
      icon: "◉",
      iconClass: "ti ti-activity",
      enabled: true,
    },
    {
      id: "workflows",
      label: "Workflows",
      icon: "◉",
      iconClass: "ti ti-git-branch",
      enabled: true,
    },
    { id: "perso", label: "Perso", icon: "◇", enabled: true },
    { id: "clients", label: "Clients", icon: "◎", enabled: true },
    {
      id: "pipeline",
      label: "Pipeline",
      icon: "◉",
      iconClass: "ti ti-chart-arrows-vertical",
      enabled: true,
    },
    { id: "accounting", label: "Comptabilité", icon: "€", enabled: true },
    { id: "newsletter", label: "Newsletter", icon: "✉", enabled: true },
  ],
};

/** Builders — Mobile & ERP (section dédiée, visible dans la sidebar). */
export const BUILDERS_NAV_GROUP: NavGroup = {
  id: "builders",
  items: [
    {
      id: "mobile_builder",
      label: "Mobile Builder",
      icon: "ti-device-mobile",
      iconClass: "ti ti-device-mobile",
      enabled: true,
    },
    {
      id: "desktop_builder",
      label: "Desktop Builder",
      icon: "ti-device-desktop",
      iconClass: "ti ti-device-desktop",
      enabled: true,
    },
    {
      id: "erp_builder",
      label: "ERP Builder",
      icon: "ti-building",
      iconClass: "ti ti-building",
      enabled: true,
    },
    {
      id: "video_builder",
      label: "Video Builder",
      icon: "ti-movie",
      iconClass: "ti ti-movie",
      enabled: true,
    },
    {
      id: "video_client",
      label: "Vidéos clients",
      icon: "🎬",
      enabled: true,
    },
  ],
};

/** Outils infra — séparés visuellement dans la sidebar. */
export const SECONDARY_NAV_GROUP: NavGroup = {
  id: "secondary",
  items: [
    { id: "media_library", label: "Médiathèque", icon: "▥", enabled: true },
    {
      id: "knowledge",
      label: "Base de connaissance",
      icon: "◉",
      iconClass: "ti ti-brain",
      enabled: true,
    },
  ],
};

export const SIDEBAR_NAV_GROUPS: NavGroup[] = [
  MAIN_NAV_GROUP,
  BUILDERS_NAV_GROUP,
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

/** Hash URL pour navigation profonde (ex. #/erp-builder). */
export const PAGE_HASH_PATHS: Partial<Record<AppPage, string>> = {
  clients: "clients",
  generator: "generator",
  erp_builder: "erp-builder",
  desktop_builder: "desktop-builder",
  mobile_builder: "mobile-builder",
  video_builder: "video-builder",
  video_client: "video-client",
  agent_builder: "agent-builder",
};

export function pageFromHash(hash: string): AppPage | null {
  const normalized = hash.replace(/^#\/?/, "").trim().toLowerCase();
  if (!normalized) return null;
  const pathOnly = normalized.split("?")[0];
  for (const [page, path] of Object.entries(PAGE_HASH_PATHS) as [AppPage, string][]) {
    if (pathOnly === path) return page;
  }
  return null;
}

/** Paramètres de requête dans le hash (ex. #/video-builder?project_id=…). */
export function queryFromHash(hash: string): URLSearchParams {
  const normalized = hash.replace(/^#\/?/, "").trim();
  const qIndex = normalized.indexOf("?");
  if (qIndex === -1) return new URLSearchParams();
  return new URLSearchParams(normalized.slice(qIndex + 1));
}

export function hashForPage(page: AppPage): string | null {
  const path = PAGE_HASH_PATHS[page];
  return path ? `#/${path}` : null;
}

/** Pages routées dans App.tsx (sidebar + routes internes). */
export const ROUTED_PAGES: AppPage[] = [
  ...PRIMARY_NAV_ITEMS.map((i) => i.id),
  SETTINGS_NAV_ITEM.id,
];

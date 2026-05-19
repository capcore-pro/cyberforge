import type { ProjectType } from "@shared/types";

export interface ProjectTypeOption {
  id: ProjectType;
  label: string;
  description: string;
}

/** Types de projet proposés dans le Générateur. */
export const PROJECT_TYPE_OPTIONS: ProjectTypeOption[] = [
  {
    id: "site_web",
    label: "Site web",
    description: "Site multi-pages, vitrine classique",
  },
  {
    id: "landing_page",
    label: "Landing page",
    description: "Page unique, hero et CTA",
  },
  {
    id: "application_web",
    label: "App web",
    description: "SPA, dashboard, logique métier",
  },
  {
    id: "application_desktop",
    label: "App desktop",
    description: "Electron, Tauri, logiciel",
  },
  {
    id: "application_mobile",
    label: "App mobile",
    description: "iOS, Android, React Native",
  },
  {
    id: "extension_navigateur",
    label: "Extension",
    description: "Plugin Chrome / Firefox",
  },
  {
    id: "saas_dashboard",
    label: "SaaS",
    description: "Produit cloud, abonnements",
  },
];

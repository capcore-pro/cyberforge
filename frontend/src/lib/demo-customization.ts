import type { DemoSeedPayload, DemoSeedTask } from "@shared/types";

export interface DemoTaskItem {
  text: string;
  completed: boolean;
}

export interface DemoStats {
  total: number;
  active: number;
  done: number;
}

export interface DemoCustomization {
  title: string;
  subtitle: string;
  brand_name: string;
  logo_data_url: string | null;
  primary_color: string;
  secondary_color: string;
  user_name: string;
  user_role: string;
  tasks: DemoTaskItem[];
  stats: DemoStats;
}

const DEFAULT_PRIMARY = "#6366f1";
const DEFAULT_SECONDARY = "#22d3ee";
const TITLE_MAX = 30;

export function deriveInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "??";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}

export function statsFromTasks(tasks: DemoTaskItem[]): DemoStats {
  const total = tasks.length;
  const done = tasks.filter((t) => t.completed).length;
  return {
    total,
    active: Math.max(0, total - done),
    done,
  };
}

function tasksFromSeed(seed: DemoSeedPayload | null | undefined): DemoTaskItem[] {
  const raw = seed?.tasks ?? [];
  const items: DemoTaskItem[] = [];
  for (const item of raw) {
    const text = item.text?.trim();
    if (!text) continue;
    items.push({
      text,
      completed: Boolean(item.completed),
    });
  }
  return items.length > 0
    ? items
    : [
        { text: "Configurer l'espace client", completed: false },
        { text: "Valider la maquette avec le client", completed: false },
        { text: "Préparer la mise en production", completed: true },
      ];
}

function statsFromSeed(
  seed: DemoSeedPayload | null | undefined,
  tasks: DemoTaskItem[],
): DemoStats {
  const s = seed?.stats;
  if (
    s &&
    typeof s.total === "number" &&
    typeof s.active === "number" &&
    typeof s.done === "number"
  ) {
    return {
      total: Math.max(0, Math.round(s.total)),
      active: Math.max(0, Math.round(s.active)),
      done: Math.max(0, Math.round(s.done)),
    };
  }
  return statsFromTasks(tasks);
}

export function customizationFromSeed(
  seed: DemoSeedPayload | null | undefined,
  fallbackTitle = "Mon application",
): DemoCustomization {
  const tasks = tasksFromSeed(seed);
  const titleSource =
    seed?.title?.trim() || seed?.brand_name?.trim() || fallbackTitle;
  return {
    title: titleSource.slice(0, TITLE_MAX),
    subtitle:
      seed?.subtitle?.trim() ||
      "Planifiez, priorisez et terminez vos actions en un seul endroit.",
    brand_name: seed?.brand_name?.trim() || titleSource.slice(0, TITLE_MAX),
    user_name: seed?.user_name?.trim() || "Alex Martin",
    user_role: seed?.user_role?.trim() || "Utilisateur",
    primary_color: seed?.primary_color?.trim() || DEFAULT_PRIMARY,
    secondary_color: seed?.secondary_color?.trim() || DEFAULT_SECONDARY,
    logo_data_url: seed?.logo_data_url ?? null,
    tasks,
    stats: statsFromSeed(seed, tasks),
  };
}

/** Copie profonde pour réinitialisation. */
export function cloneCustomization(value: DemoCustomization): DemoCustomization {
  return {
    ...value,
    tasks: value.tasks.map((t) => ({ ...t })),
    stats: { ...value.stats },
  };
}

export function mergeCustomizationIntoSeed(
  base: DemoSeedPayload | null | undefined,
  custom: DemoCustomization,
): DemoSeedPayload {
  const title = custom.title.trim().slice(0, TITLE_MAX);
  const merged: DemoSeedPayload = {
    ...(base ?? {}),
    title,
    subtitle: custom.subtitle.trim(),
    brand_name: custom.brand_name.trim() || title,
    user_name: custom.user_name.trim(),
    user_role: custom.user_role.trim(),
    user_initials: deriveInitials(custom.user_name),
    primary_color: custom.primary_color.trim() || DEFAULT_PRIMARY,
    secondary_color: custom.secondary_color.trim() || DEFAULT_SECONDARY,
    tasks: custom.tasks.map((t) => ({
      text: t.text.trim(),
      completed: t.completed,
    })),
    stats: {
      total: Math.max(0, Math.round(custom.stats.total)),
      active: Math.max(0, Math.round(custom.stats.active)),
      done: Math.max(0, Math.round(custom.stats.done)),
    },
  };
  if (custom.logo_data_url) {
    merged.logo_data_url = custom.logo_data_url;
  } else {
    delete merged.logo_data_url;
  }
  return merged;
}

export function readImageFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!/^image\/(png|jpeg|jpg)$/i.test(file.type)) {
      reject(new Error("Format accepté : PNG ou JPG uniquement."));
      return;
    }
    if (file.size > 512 * 1024) {
      reject(new Error("Image trop lourde (max 512 Ko)."));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result === "string") resolve(result);
      else reject(new Error("Lecture du fichier impossible."));
    };
    reader.onerror = () => reject(new Error("Lecture du fichier impossible."));
    reader.readAsDataURL(file);
  });
}

export const CUSTOMIZATION_TITLE_MAX = TITLE_MAX;

import type { DemoSeedPayload } from "@shared/types";

export interface DemoCustomization {
  title: string;
  user_name: string;
  user_role: string;
  primary_color: string;
  logo_data_url: string | null;
}

const DEFAULT_COLOR = "#6366f1";

export function customizationFromSeed(
  seed: DemoSeedPayload | null | undefined,
  fallbackTitle = "Mon application",
): DemoCustomization {
  return {
    title: seed?.title?.trim() || seed?.brand_name?.trim() || fallbackTitle,
    user_name: seed?.user_name?.trim() || "Alex Martin",
    user_role: seed?.user_role?.trim() || "Utilisateur",
    primary_color: seed?.primary_color?.trim() || DEFAULT_COLOR,
    logo_data_url: seed?.logo_data_url ?? null,
  };
}

export function mergeCustomizationIntoSeed(
  base: DemoSeedPayload | null | undefined,
  custom: DemoCustomization,
): DemoSeedPayload {
  const merged: DemoSeedPayload = {
    ...(base ?? {}),
    title: custom.title.trim(),
    brand_name: custom.title.trim(),
    user_name: custom.user_name.trim(),
    user_role: custom.user_role.trim(),
    primary_color: custom.primary_color.trim() || DEFAULT_COLOR,
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

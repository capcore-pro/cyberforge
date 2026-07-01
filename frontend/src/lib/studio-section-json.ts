export function parseJsonArray<T>(raw: string | undefined, fallback: T[]): T[] {
  if (!raw?.trim()) return fallback;
  try {
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as T[]) : fallback;
  } catch {
    return fallback;
  }
}

export function stringifyJsonArray<T>(items: T[]): string {
  return JSON.stringify(items);
}

export interface ServiceItem {
  nom: string;
  description: string;
  prix: string;
  icone: string;
}

export interface ProductItem {
  nom: string;
  description: string;
  prix: string;
  statut: "Disponible" | "Bientôt disponible" | "Épuisé";
}

export interface FaqItem {
  question: string;
  reponse: string;
}

export interface TemoignageItem {
  nom_client: string;
  poste: string;
  texte: string;
  note: string;
}

export interface RealisationItem {
  titre: string;
  description: string;
  image_url: string;
}

export interface FonctionnaliteItem {
  icone: string;
  titre: string;
  description: string;
}

export const EMPTY_SERVICE: ServiceItem = {
  nom: "",
  description: "",
  prix: "",
  icone: "",
};

export const EMPTY_PRODUCT: ProductItem = {
  nom: "",
  description: "",
  prix: "",
  statut: "Disponible",
};

export const EMPTY_FAQ: FaqItem = { question: "", reponse: "" };

export const EMPTY_TEMOIGNAGE: TemoignageItem = {
  nom_client: "",
  poste: "",
  texte: "",
  note: "5",
};

export const EMPTY_REALISATION: RealisationItem = {
  titre: "",
  description: "",
  image_url: "",
};

export const EMPTY_FONCTIONNALITE: FonctionnaliteItem = {
  icone: "",
  titre: "",
  description: "",
};

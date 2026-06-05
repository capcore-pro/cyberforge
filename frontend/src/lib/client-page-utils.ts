import type { ClientRecord } from "@/lib/clients-api";

const AVATAR_PALETTE = [
  "bg-amber-500/20 text-amber-200 border-amber-400/30",
  "bg-blue-500/20 text-blue-200 border-blue-400/30",
  "bg-emerald-500/20 text-emerald-200 border-emerald-400/30",
  "bg-violet-500/20 text-violet-200 border-violet-400/30",
  "bg-cyan-500/20 text-cyan-200 border-cyan-400/30",
  "bg-orange-500/20 text-orange-200 border-orange-400/30",
  "bg-rose-500/20 text-rose-200 border-rose-400/30",
] as const;

export function clientInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
  }
  return (parts[0]?.slice(0, 2) ?? "?").toUpperCase();
}

export function avatarClasses(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash + seed.charCodeAt(i)) % AVATAR_PALETTE.length;
  }
  return AVATAR_PALETTE[hash] ?? AVATAR_PALETTE[0];
}

export function splitClientName(name: string): {
  firstName: string;
  lastName: string;
} {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length <= 1) {
    return { firstName: parts[0] ?? "", lastName: "" };
  }
  return { firstName: parts[0], lastName: parts.slice(1).join(" ") };
}

export function joinClientName(firstName: string, lastName: string): string {
  return `${firstName.trim()} ${lastName.trim()}`.trim();
}

export function formatRelativeDate(iso: string): string {
  try {
    const date = new Date(iso);
    const diffMs = Date.now() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 60) return "à l'instant";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `il y a ${diffMin} min`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `il y a ${diffHours} h`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return "il y a 1 jour";
    if (diffDays < 30) return `il y a ${diffDays} jours`;
    const diffMonths = Math.floor(diffDays / 30);
    if (diffMonths === 1) return "il y a 1 mois";
    if (diffMonths < 12) return `il y a ${diffMonths} mois`;
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(date);
  } catch {
    return iso;
  }
}

export interface ClientLocalMeta {
  website: string;
  notes: string;
}

function metaKey(clientId: string): string {
  return `cyberforge.clientMeta.${clientId}`;
}

export function loadClientMeta(clientId: string): ClientLocalMeta {
  try {
    const raw = localStorage.getItem(metaKey(clientId));
    if (!raw) return { website: "", notes: "" };
    const parsed = JSON.parse(raw) as Partial<ClientLocalMeta>;
    return {
      website: typeof parsed.website === "string" ? parsed.website : "",
      notes: typeof parsed.notes === "string" ? parsed.notes : "",
    };
  } catch {
    return { website: "", notes: "" };
  }
}

export function saveClientMeta(clientId: string, meta: ClientLocalMeta): void {
  try {
    localStorage.setItem(metaKey(clientId), JSON.stringify(meta));
  } catch {
    /* quota / mode privé */
  }
}

export function displayClientName(client: ClientRecord): string {
  return client.name.trim();
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "").replace(/\/$/, "")

export interface PostResult {
  success: boolean
  post: string
  accroche: string
  conseil: string
  format: string
  label: string
}

export interface HashtagsResult {
  success: boolean
  hashtags: string[]
  conseil: string
}

export interface BioResult {
  success: boolean
  bios: { version: string; texte: string }[]
  format: string
  limite: string
}

export interface FormatInfo {
  id: string
  label: string
  ton: string
  longueur: string
}

export async function fetchFormats(): Promise<{ formats: FormatInfo[]; secteurs: string[] }> {
  const res = await fetch(`${API_BASE}/api/content/formats`)
  return res.json()
}

export async function generatePost(params: {
  sujet: string
  secteur: string
  format_reseau: string
  ton_personnalise?: string
  nom_entreprise?: string
}): Promise<PostResult> {
  const res = await fetch(`${API_BASE}/api/content/post`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  })
  return res.json()
}

export async function generateHashtags(params: {
  sujet: string
  secteur: string
  format_reseau: string
  nb_hashtags?: number
}): Promise<HashtagsResult> {
  const res = await fetch(`${API_BASE}/api/content/hashtags`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  })
  return res.json()
}

export async function generateBio(params: {
  nom_entreprise: string
  secteur: string
  valeur_ajoutee: string
  format_reseau: string
}): Promise<BioResult> {
  const res = await fetch(`${API_BASE}/api/content/bio`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  })
  return res.json()
}

const API_BASE = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "").replace(/\/$/, "")

export interface VisualFormat {
  key: string
  label: string
  width: number
  height: number
  usage: string
}

export interface AvatarPose {
  key: string
  label: string
  description: string
}

export interface VisualStyle {
  key: string
  label: string
}

export interface VisualConfig {
  formats: VisualFormat[]
  poses: AvatarPose[]
  styles: VisualStyle[]
}

export interface AvatarPoseResult {
  success: boolean
  image_url?: string
  pose_key?: string
  pose_label?: string
  format?: string
  error?: string
}

export interface SocialVisualResult {
  success: boolean
  image_url?: string
  format?: string
  format_label?: string
  texte_principal?: string
  sous_texte?: string
  error?: string
}

export async function fetchVisualConfig(): Promise<VisualConfig> {
  const res = await fetch(`${API_BASE}/api/visual/config`)
  return res.json()
}

export async function generateAvatarPose(
  pose_key: string,
  format_key: string = "1:1"
): Promise<AvatarPoseResult> {
  const res = await fetch(`${API_BASE}/api/visual/avatar-pose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pose_key, format_key }),
  })
  return res.json()
}

export async function generateSocialVisual(params: {
  texte_principal: string
  sous_texte: string
  format_key: string
  style: string
  pose_key: string
  sujet_context?: string
  image_prompt?: string | null
  image_prompt_strength?: number
}): Promise<SocialVisualResult> {
  const res = await fetch(`${API_BASE}/api/visual/social-visual`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  })
  return res.json()
}

// --- Galerie poses ---

export interface PoseItem {
  id: string
  pose_key: string
  image_url: string
  storage_path: string
  created_at: string
}

export interface SavePoseRequest {
  pose_key: string
  image_url: string
}

export async function fetchPoseGallery(): Promise<PoseItem[]> {
  const res = await fetch(`${API_BASE}/api/visual/poses`)
  if (!res.ok) throw new Error("Erreur chargement galerie poses")
  const data = await res.json()
  return data.poses as PoseItem[]
}

export async function savePoseToGallery(request: SavePoseRequest): Promise<void> {
  const res = await fetch(`${API_BASE}/api/visual/poses/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })
  if (!res.ok) throw new Error("Erreur sauvegarde pose")
}

export async function deletePoseFromGallery(poseKey: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/visual/poses/${poseKey}`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error("Erreur suppression pose")
}

// --- Upload référence ---

export async function uploadReferenceImage(
  file: File,
): Promise<{ reference_url: string; storage_path: string }> {
  const formData = new FormData()
  formData.append("file", file)
  const res = await fetch(`${API_BASE}/api/visual/upload-reference`, {
    method: "POST",
    body: formData,
  })
  if (!res.ok) throw new Error("Erreur upload image référence")
  return res.json()
}

// --- Carrousel ---

export interface CarouselSlide {
  slide_index: number
  role: string
  image_url: string
  titre: string
  sous_texte: string
}

export interface CarouselRequest {
  sujet_type: string
  sujet_label: string
  format_reseau: string
}

export interface CarouselResponse {
  slides: CarouselSlide[]
  textes_utilises: Array<{ role: string; titre: string; sous_texte: string }>
}

export async function generateCarousel(request: CarouselRequest): Promise<CarouselResponse> {
  const res = await fetch(`${API_BASE}/api/visual/carousel`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  })
  if (!res.ok) throw new Error("Erreur génération carrousel")
  return res.json()
}

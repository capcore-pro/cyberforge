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
}): Promise<SocialVisualResult> {
  const res = await fetch(`${API_BASE}/api/visual/social-visual`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  })
  return res.json()
}

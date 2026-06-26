const API_BASE = (import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "").replace(/\/$/, "")

export interface ImageToVideoResult {
  success: boolean
  task_id?: string
  error?: string
}

export interface ImageToVideoStatus {
  success: boolean
  status?: string
  task_id?: string
  video_url?: string
  duration?: number
  error?: string
}

export async function generateImageToVideo(params: {
  image_base64: string
  prompt: string
  duration: number
  aspect_ratio: string
}): Promise<ImageToVideoResult> {
  const res = await fetch(`${API_BASE}/api/video/image2video`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  })
  return res.json()
}

export async function checkImageVideoStatus(task_id: string): Promise<ImageToVideoStatus> {
  const res = await fetch(`${API_BASE}/api/video/image2video/${task_id}/status`)
  return res.json()
}

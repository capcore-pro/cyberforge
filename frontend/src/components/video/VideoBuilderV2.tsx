import { useState, useRef, useCallback } from "react"
import { generateImageToVideo, checkImageVideoStatus } from "@/lib/video-api"

const ASPECT_RATIOS = [
  { key: "9:16", label: "9:16", usage: "TikTok / Stories" },
  { key: "1:1", label: "1:1", usage: "Instagram Feed" },
  { key: "16:9", label: "16:9", usage: "LinkedIn / YouTube" },
]

const DURATIONS = [
  { value: 5, label: "5 secondes" },
  { value: 10, label: "10 secondes" },
]

const PROMPT_SUGGESTIONS = [
  "zoom in lent, lumière dorée, ambiance cinématique",
  "caméra qui tourne autour du sujet, fond flou",
  "travelling avant dynamique, éclairage tech cyan",
  "rotation lente, effet parallaxe, atmosphère sombre",
  "pan gauche-droite fluide, profondeur de champ",
]

export default function VideoBuilderV2() {
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [imageBase64, setImageBase64] = useState<string>("")
  const [prompt, setPrompt] = useState<string>("")
  const [duration, setDuration] = useState<number>(5)
  const [aspectRatio, setAspectRatio] = useState<string>("9:16")
  const [loading, setLoading] = useState<boolean>(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [status, setStatus] = useState<string>("")
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState<boolean>(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const handleFileSelect = useCallback((file: File) => {
    if (!file.type.startsWith("image/")) return
    setVideoUrl(null)
    setError(null)
    setTaskId(null)
    setStatus("")

    const reader = new FileReader()
    reader.onload = (e) => {
      const result = e.target?.result as string
      setImagePreview(result)
      const base64 = result.split(",")[1]
      setImageBase64(base64)
    }
    reader.readAsDataURL(file)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileSelect(file)
  }, [handleFileSelect])

  const startPolling = useCallback((tid: string) => {
    if (pollRef.current) clearInterval(pollRef.current)
    setStatus("processing")

    pollRef.current = setInterval(async () => {
      try {
        const result = await checkImageVideoStatus(tid)
        if (result.status === "succeed" && result.video_url) {
          clearInterval(pollRef.current!)
          setStatus("succeed")
          setVideoUrl(result.video_url)
          setLoading(false)
        } else if (result.status === "failed") {
          clearInterval(pollRef.current!)
          setError("Génération échouée — réessaie avec un autre prompt ou une autre image.")
          setStatus("failed")
          setLoading(false)
        }
      } catch {
        clearInterval(pollRef.current!)
        setError("Erreur lors du polling status.")
        setLoading(false)
      }
    }, 15000)
  }, [])

  const handleGenerate = async () => {
    if (!imageBase64 || !prompt) return
    setLoading(true)
    setError(null)
    setVideoUrl(null)
    setTaskId(null)
    setStatus("starting")

    try {
      const result = await generateImageToVideo({
        image_base64: imageBase64,
        prompt,
        duration,
        aspect_ratio: aspectRatio,
      })

      if (!result.success || !result.task_id) {
        setError(result.error || "Erreur démarrage génération.")
        setLoading(false)
        return
      }

      setTaskId(result.task_id)
      startPolling(result.task_id)
    } catch {
      setError("Erreur connexion backend.")
      setLoading(false)
    }
  }

  const handleReset = () => {
    if (pollRef.current) clearInterval(pollRef.current)
    setImagePreview(null)
    setImageBase64("")
    setPrompt("")
    setVideoUrl(null)
    setTaskId(null)
    setStatus("")
    setError(null)
    setLoading(false)
  }

  return (
    <div className="space-y-6">

      <div>
        <h2 className="text-lg font-medium text-white">Image-to-Video</h2>
        <p className="text-sm text-white/40 mt-1">
          Uploade une image → Kling l&apos;anime → vidéo prête à publier
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        <div className="space-y-5">

          <div>
            <label className="block text-sm text-white/60 mb-2">Image source</label>
            {!imagePreview ? (
              <div
                onDrop={handleDrop}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onClick={() => fileInputRef.current?.click()}
                className={`w-full h-48 rounded-xl border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-colors ${
                  dragOver
                    ? "border-cyan-400 bg-cyan-400/5"
                    : "border-white/10 hover:border-white/30 bg-white/5"
                }`}
              >
                <span className="text-3xl mb-2">📷</span>
                <p className="text-sm text-white/40">Glisse une image ici</p>
                <p className="text-xs text-white/20 mt-1">ou clique pour choisir</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) handleFileSelect(file)
                  }}
                />
              </div>
            ) : (
              <div className="relative">
                <img
                  src={imagePreview}
                  alt="Source"
                  className="w-full h-48 object-cover rounded-xl border border-white/10"
                />
                <button
                  type="button"
                  onClick={handleReset}
                  className="absolute top-2 right-2 px-2 py-1 bg-black/60 text-white/70 text-xs rounded-lg hover:bg-black/80 transition-colors"
                >
                  ✕ Changer
                </button>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm text-white/60 mb-2">Prompt d&apos;animation</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Décris le mouvement souhaité..."
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-white/20 focus:outline-none focus:border-cyan-400 resize-none"
            />
            <div className="flex flex-wrap gap-1.5 mt-2">
              {PROMPT_SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setPrompt(s)}
                  className="px-2 py-1 bg-white/5 text-white/40 text-xs rounded-lg hover:bg-white/10 hover:text-white/60 transition-colors"
                >
                  {s.length > 35 ? `${s.slice(0, 35)}…` : s}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm text-white/60 mb-2">Format</label>
            <div className="flex gap-2">
              {ASPECT_RATIOS.map(r => (
                <button
                  key={r.key}
                  type="button"
                  onClick={() => setAspectRatio(r.key)}
                  className={`flex-1 py-2 rounded-lg text-xs transition-colors ${
                    aspectRatio === r.key
                      ? "bg-cyan-400 text-black font-medium"
                      : "bg-white/5 text-white/60 hover:text-white"
                  }`}
                >
                  <div className="font-medium">{r.label}</div>
                  <div className="opacity-60 text-[10px] mt-0.5">{r.usage}</div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm text-white/60 mb-2">Durée</label>
            <div className="flex gap-2">
              {DURATIONS.map(d => (
                <button
                  key={d.value}
                  type="button"
                  onClick={() => setDuration(d.value)}
                  className={`flex-1 py-2 rounded-lg text-sm transition-colors ${
                    duration === d.value
                      ? "bg-cyan-400 text-black font-medium"
                      : "bg-white/5 text-white/60 hover:text-white"
                  }`}
                >
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          <button
            type="button"
            onClick={() => void handleGenerate()}
            disabled={loading || !imageBase64 || !prompt}
            className="w-full py-3 rounded-xl bg-cyan-400 text-black font-medium text-sm hover:bg-cyan-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {loading
              ? status === "starting"
                ? "Démarrage..."
                : `Génération en cours (~${duration === 5 ? "2-3" : "4-5"} min)...`
              : "▶ Générer la vidéo"}
          </button>

          {taskId && (
            <p className="text-xs text-white/20 text-center">
              Task ID : {taskId}
            </p>
          )}
        </div>

        <div className="flex flex-col items-center justify-start">

          {error && (
            <div className="w-full bg-red-500/10 rounded-xl p-4 border border-red-500/20 mb-4">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {loading && !videoUrl && (
            <div className="w-full aspect-video rounded-xl border border-white/10 bg-white/5 flex flex-col items-center justify-center gap-3">
              <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
              <p className="text-white/40 text-sm">
                {status === "starting" ? "Envoi à Kling..." : "Animation en cours..."}
              </p>
              <p className="text-white/20 text-xs">Polling toutes les 15s</p>
            </div>
          )}

          {videoUrl && (
            <div className="w-full space-y-3">
              <video
                src={videoUrl}
                controls
                autoPlay
                loop
                className="w-full rounded-xl border border-white/10 object-cover"
              />
              <div className="flex gap-2 flex-wrap">
                <a
                  href={videoUrl}
                  download
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 py-2 rounded-lg bg-cyan-400/10 text-cyan-400 text-xs text-center hover:bg-cyan-400/20 transition-colors"
                >
                  ↓ Télécharger
                </a>
                <button
                  type="button"
                  onClick={() => navigator.clipboard.writeText(videoUrl)}
                  className="flex-1 py-2 rounded-lg bg-white/5 text-white/60 text-xs hover:bg-white/10 transition-colors"
                >
                  Copier l&apos;URL
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  className="px-4 py-2 rounded-lg bg-white/5 text-white/60 text-xs hover:bg-white/10 transition-colors"
                >
                  Nouvelle vidéo
                </button>
              </div>
            </div>
          )}

          {!loading && !videoUrl && !error && (
            <div className="w-full aspect-video rounded-xl border border-white/5 bg-white/5 flex flex-col items-center justify-center gap-2">
              <span className="text-4xl opacity-20">🎬</span>
              <p className="text-white/20 text-sm">La vidéo apparaîtra ici</p>
            </div>
          )}

          <div className="w-full mt-4 p-3 bg-white/5 rounded-xl border border-white/5">
            <p className="text-xs text-white/30 text-center">
              Coût estimé : ~3–5 unités Kling · Durée : {duration}s · Format : {aspectRatio}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

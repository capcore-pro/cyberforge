// ============================================
// VIDEO STUDIO PANEL — CyberForge
// Panneau central de création vidéo
// ============================================

import { useState, useEffect, useRef } from "react";
import {
  Sparkles, Play, Loader, ChevronRight,
  Zap, AlertCircle
} from "lucide-react";
import { useVideoGeneration } from "@/context/VideoGenerationContext";
import SceneEditor from "./SceneEditor";
import MusicSelector from "./MusicSelector";

interface Scene {
  scene_number: number;
  title: string;
  description_fr: string;
  prompt: string;
  camera_move: string;
  mood: string;
  duration: number;
}

interface ScenesData {
  concept: string;
  color_palette: string;
  scenes: Scene[];
}

interface GenerationEvent {
  type: string;
  scene?: number;
  title?: string;
  task_id?: string;
  progress?: number;
  total?: number;
  url?: string;
  message?: string;
}

interface VideoStudioPanelProps {
  onProjectCreated?: () => void;
}

const BRANDS = [
  { id: "cyberforge", label: "CyberForge", color: "text-cyan-400" },
  { id: "capcopy", label: "Cap Copy", color: "text-blue-400" },
  { id: "lumio", label: "Lumio", color: "text-yellow-400" },
  { id: "vocali", label: "Vocali", color: "text-purple-400" }
];

const AMBIANCES = [
  "cinématique premium",
  "tech sombre futuriste",
  "épique et dramatique",
  "minimaliste élégant",
  "énergique et dynamique",
  "mystérieux et intrigant"
];

type Step = "brief" | "scenes" | "generate";

function notifyVideoReady(): void {
  const title = "CyberForge — Vidéo prête ! 🎬";
  const body = "Ta pub est générée et prête à télécharger.";
  window.cyberforge?.notify?.(title, body);
  window.electronAPI?.notify?.(title, body);
}

export default function VideoStudioPanel({
  onProjectCreated
}: VideoStudioPanelProps) {
  const { setActive: setVideoGenerationActive } = useVideoGeneration();
  // Brief
  const [step, setStep] = useState<Step>("brief");
  const [brand, setBrand] = useState("cyberforge");
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [slogan, setSlogan] = useState("");
  const [callToAction, setCallToAction] = useState("");
  const [keyMessage, setKeyMessage] = useState("");
  const [ambiance, setAmbiance] = useState("cinématique premium");

  // Scènes
  const [scenesData, setScenesData] = useState<ScenesData | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [generatingScenes, setGeneratingScenes] = useState(false);

  // Musique
  const [selectedMusicId, setSelectedMusicId] = useState<string | null>(null);

  // Génération
  const [generating, setGenerating] = useState(false);
  const [generationEvents, setGenerationEvents] = useState<GenerationEvent[]>([]);
  const [currentProgress, setCurrentProgress] = useState(0);
  const [totalClips, setTotalClips] = useState(6);
  const [finalUrl, setFinalUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentProjectId, setCurrentProjectId] = useState<string | null>(null);
  const videoReadyNotifiedRef = useRef(false);

  useEffect(() => {
    return () => setVideoGenerationActive(false);
  }, [setVideoGenerationActive]);

  const markVideoReady = () => {
    if (videoReadyNotifiedRef.current) return;
    videoReadyNotifiedRef.current = true;
    notifyVideoReady();
  };

  useEffect(() => {
    if (step !== "generate" || !currentProjectId || finalUrl || error) return;

    let cancelled = false;

    const pollProjectStatus = async () => {
      if (cancelled) return;

      try {
        const res = await fetch(
          `http://127.0.0.1:8002/api/video/projects/${currentProjectId}`,
        );
        const data = await res.json();
        if (!data.success || cancelled) return;

        const project = data.data;
        const clips = project.clips || [];
        const doneClips = clips.filter(
          (c: { status?: string }) => c.status === "done",
        ).length;

        if (clips.length > 0) {
          setTotalClips(clips.length);
        }
        setCurrentProgress(doneClips);

        if (project.status === "done") {
          setFinalUrl(project.final_video_url ?? null);
          setGenerating(false);
          setVideoGenerationActive(false);
          onProjectCreated?.();
          markVideoReady();
          return;
        }

        if (project.status === "failed") {
          setError("Génération échouée");
          setGenerating(false);
          setVideoGenerationActive(false);
        }
      } catch {
        // SSE ou polling suivant
      }
    };

    void pollProjectStatus();
    const interval = window.setInterval(() => void pollProjectStatus(), 10_000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [
    step,
    currentProjectId,
    finalUrl,
    error,
    onProjectCreated,
    setVideoGenerationActive,
  ]);

  // ─────────────────────────────────────────
  // ÉTAPE 1 — Générer les scènes via VideoAI
  // ─────────────────────────────────────────
  const handleGenerateScenes = async () => {
    if (!brief.trim() || !title.trim()) return;
    setGeneratingScenes(true);
    setError(null);

    try {
      const res = await fetch(
        "http://127.0.0.1:8002/api/video/scenes/generate",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            brand,
            brief,
            ambiance,
            slogan,
            key_message: keyMessage,
            call_to_action: callToAction,
          }),
        }
      );
      const data = await res.json();

      if (data.success) {
        setScenesData(data.data);
        setScenes(data.data.scenes);
        setStep("scenes");
      } else {
        setError(data.message || "Erreur génération scènes");
      }
    } catch (e) {
      setError("Erreur connexion backend");
    } finally {
      setGeneratingScenes(false);
    }
  };

  // ─────────────────────────────────────────
  // ÉTAPE 2 — Créer projet + lancer génération
  // ─────────────────────────────────────────
  const handleStartGeneration = async () => {
    setGenerating(true);
    setVideoGenerationActive(true);
    setError(null);
    setGenerationEvents([]);
    setFinalUrl(null);
    videoReadyNotifiedRef.current = false;

    try {
      // Créer projet
      const createRes = await fetch(
        "http://127.0.0.1:8002/api/video/projects",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title, brand, brief, ambiance, scenes })
        }
      );
      const createData = await createRes.json();

      if (!createData.success) {
        throw new Error(createData.message || "Erreur création projet");
      }

      const projectId = createData.project_id;
      setCurrentProjectId(projectId);
      setStep("generate");

      // Lancer génération SSE
      const response = await fetch(
        "http://127.0.0.1:8002/api/video/generate",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_id: projectId,
            music_id: selectedMusicId
          })
        }
      );

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;

          try {
            const event: GenerationEvent = JSON.parse(
              line.replace("data: ", "")
            );

            setGenerationEvents(prev => [...prev, event]);

            if (event.type === "start") {
              setTotalClips(event.total || 6);
            }
            if (event.type === "clip_done") {
              setCurrentProgress(event.progress || 0);
            }
            if (event.type === "done") {
              setFinalUrl(event.url || null);
              onProjectCreated?.();
              markVideoReady();
            }
            if (event.type === "error") {
              setError(event.message || "Erreur génération");
            }
          } catch {}
        }
      }
    } catch (e: any) {
      setError(e.message || "Erreur inattendue");
    } finally {
      setGenerating(false);
      setVideoGenerationActive(false);
    }
  };

  const resetStudio = () => {
    setStep("brief");
    setTitle("");
    setBrief("");
    setSlogan("");
    setCallToAction("");
    setKeyMessage("");
    setScenes([]);
    setScenesData(null);
    setGenerationEvents([]);
    setCurrentProgress(0);
    setFinalUrl(null);
    setError(null);
    setSelectedMusicId(null);
    setCurrentProjectId(null);
    videoReadyNotifiedRef.current = false;
  };

  // ─────────────────────────────────────────
  // RENDER — ÉTAPE BRIEF
  // ─────────────────────────────────────────
  if (step === "brief") {
    return (
      <div className="space-y-6">

        {/* Titre */}
        <div>
          <label className="text-xs text-gray-500 mb-2 block">
            Nom du projet
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Ex: Pub CyberForge Été 2026"
            className="w-full bg-gray-900 border border-gray-700 rounded-xl 
                       px-4 py-3 text-white placeholder-gray-600
                       focus:outline-none focus:border-cyan-500"
          />
        </div>

        {/* Marque */}
        <div>
          <label className="text-xs text-gray-500 mb-2 block">Marque</label>
          <div className="grid grid-cols-2 gap-2">
            {BRANDS.map((b) => (
              <button
                key={b.id}
                onClick={() => setBrand(b.id)}
                className={`px-4 py-2.5 rounded-xl border text-sm font-medium 
                           transition-colors ${
                  brand === b.id
                    ? "bg-gray-800 border-gray-600 text-white"
                    : "bg-gray-900 border-gray-800 text-gray-500 hover:border-gray-700"
                }`}
              >
                <span className={brand === b.id ? b.color : ""}>
                  {b.label}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Brief */}
        <div>
          <label className="text-xs text-gray-500 mb-2 block">
            Brief créatif
          </label>
          <textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder="Décris ta publicité... (produit, message clé, cible, émotion)"
            rows={4}
            className="w-full bg-gray-900 border border-gray-700 rounded-xl 
                       px-4 py-3 text-white placeholder-gray-600
                       focus:outline-none focus:border-cyan-500 resize-none"
          />
        </div>

        {/* Slogan */}
        <div>
          <label className="text-xs text-gray-500 mb-2 block">
            Slogan / Accroche
          </label>
          <input
            type="text"
            placeholder="Ex: L'IA qui forge votre succès digital"
            value={slogan}
            onChange={(e) => setSlogan(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-xl 
                       px-4 py-3 text-white placeholder-gray-600
                       focus:outline-none focus:border-cyan-500"
          />
        </div>

        {/* Message clé */}
        <div>
          <label className="text-xs text-gray-500 mb-2 block">
            Message clé
          </label>
          <input
            type="text"
            placeholder="Ex: Générez un site pro en 3 minutes"
            value={keyMessage}
            onChange={(e) => setKeyMessage(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-xl 
                       px-4 py-3 text-white placeholder-gray-600
                       focus:outline-none focus:border-cyan-500"
          />
        </div>

        {/* Call to action */}
        <div>
          <label className="text-xs text-gray-500 mb-2 block">
            Call to action
          </label>
          <input
            type="text"
            placeholder="Ex: Essayez gratuitement sur cyberforge.io"
            value={callToAction}
            onChange={(e) => setCallToAction(e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-xl 
                       px-4 py-3 text-white placeholder-gray-600
                       focus:outline-none focus:border-cyan-500"
          />
        </div>

        {/* Ambiance */}
        <div>
          <label className="text-xs text-gray-500 mb-2 block">Ambiance</label>
          <div className="flex flex-wrap gap-2">
            {AMBIANCES.map((a) => (
              <button
                key={a}
                onClick={() => setAmbiance(a)}
                className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${
                  ambiance === a
                    ? "bg-cyan-900 border-cyan-700 text-cyan-300"
                    : "bg-gray-900 border-gray-800 text-gray-500 hover:border-gray-700"
                }`}
              >
                {a}
              </button>
            ))}
          </div>
        </div>

        {/* Erreur */}
        {error && (
          <div className="flex items-center gap-2 text-red-400 text-sm 
                          bg-red-950 border border-red-800 rounded-xl px-4 py-3">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {/* CTA */}
        <button
          onClick={handleGenerateScenes}
          disabled={!brief.trim() || !title.trim() || generatingScenes}
          className="w-full flex items-center justify-center gap-2 py-3.5 
                     bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 
                     disabled:cursor-not-allowed text-white font-medium 
                     rounded-xl transition-colors"
        >
          {generatingScenes ? (
            <>
              <Loader size={16} className="animate-spin" />
              VideoAI génère les scènes...
            </>
          ) : (
            <>
              <Sparkles size={16} />
              Générer les scènes
              <ChevronRight size={16} />
            </>
          )}
        </button>
      </div>
    );
  }

  // ─────────────────────────────────────────
  // RENDER — ÉTAPE SCÈNES
  // ─────────────────────────────────────────
  if (step === "scenes") {
    return (
      <div className="space-y-6">

        {/* Concept */}
        {scenesData && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3">
            <p className="text-xs text-gray-500 mb-1">Concept VideoAI</p>
            <p className="text-white text-sm">{scenesData.concept}</p>
            <p className="text-gray-500 text-xs mt-1">
              🎨 {scenesData.color_palette}
            </p>
          </div>
        )}

        <div className="bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 mb-4">
          <p className="text-xs text-gray-400">
            💡 <strong className="text-white">Conseil économies</strong> — Lisez et
            modifiez vos scènes en français avant de lancer la génération. Chaque
            modification après génération coûte des crédits Kling.
          </p>
        </div>

        {/* Scènes */}
        <SceneEditor scenes={scenes} onChange={setScenes} />

        {/* Musique */}
        <div className="border-t border-gray-800 pt-6">
          <MusicSelector
            brand={brand}
            selectedId={selectedMusicId}
            onSelect={setSelectedMusicId}
          />
        </div>

        {/* Erreur */}
        {error && (
          <div className="flex items-center gap-2 text-red-400 text-sm 
                          bg-red-950 border border-red-800 rounded-xl px-4 py-3">
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={() => setStep("brief")}
            className="px-4 py-3 bg-gray-800 hover:bg-gray-700 text-gray-300 
                       rounded-xl text-sm transition-colors"
          >
            Retour
          </button>
          <button
            onClick={handleStartGeneration}
            disabled={generating}
            className="flex-1 flex items-center justify-center gap-2 py-3 
                       bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 
                       text-white font-medium rounded-xl transition-colors"
          >
            <Zap size={16} />
            Lancer la génération
          </button>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────
  // RENDER — ÉTAPE GÉNÉRATION
  // ─────────────────────────────────────────
  return (
    <div className="space-y-4">

      {/* Progress */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-white text-sm font-medium">
            Génération en cours
          </span>
          <span className="text-cyan-400 text-sm">
            {currentProgress}/{totalClips} clips
          </span>
        </div>

        <div className="w-full bg-gray-800 rounded-full h-2 mb-4">
          <div
            className="h-2 bg-cyan-500 rounded-full transition-all duration-500"
            style={{
              width: `${(currentProgress / totalClips) * 100}%`
            }}
          />
        </div>

        {/* Événements */}
        <div className="space-y-1.5 max-h-48 overflow-y-auto">
          {generationEvents.map((event, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              {event.type === "clip_done" && (
                <>
                  <span className="text-green-400">✓</span>
                  <span className="text-gray-300">
                    Scène {event.scene} générée
                  </span>
                </>
              )}
              {event.type === "clip_start" && (
                <>
                  <Loader size={10} className="text-cyan-400 animate-spin" />
                  <span className="text-gray-400">
                    Scène {event.scene} — {event.title}
                  </span>
                </>
              )}
              {event.type === "assembling" && (
                <>
                  <Loader size={10} className="text-yellow-400 animate-spin" />
                  <span className="text-yellow-400">
                    Assemblage vidéo finale...
                  </span>
                </>
              )}
              {event.type === "done" && (
                <>
                  <span className="text-green-400">🎬</span>
                  <span className="text-green-400 font-medium">
                    Vidéo prête !
                  </span>
                </>
              )}
              {event.type === "error" && (
                <>
                  <span className="text-red-400">✗</span>
                  <span className="text-red-400">{event.message}</span>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Vidéo finale */}
      {finalUrl && (
        <div className="bg-gray-900 border border-green-800 rounded-xl p-4">
          <p className="text-green-400 font-medium text-sm mb-3">
            🎬 Pub finale générée
          </p>
          <video
            src={`http://127.0.0.1:8002${finalUrl}`}
            controls
            className="w-full rounded-lg bg-black mb-3"
          />
          <div className="flex gap-2">
            <a
              href={
                currentProjectId
                  ? `http://127.0.0.1:8002/api/video/download/${currentProjectId}`
                  : undefined
              }
              download
              className="flex items-center gap-1.5 px-4 py-2 bg-cyan-600 
                         hover:bg-cyan-500 text-white text-sm rounded-lg 
                         transition-colors"
            >
              Télécharger MP4
            </a>
            <button
              onClick={resetStudio}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 
                         text-gray-300 text-sm rounded-lg transition-colors"
            >
              Nouveau projet
            </button>
          </div>
        </div>
      )}

      {/* Erreur */}
      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm 
                        bg-red-950 border border-red-800 rounded-xl px-4 py-3">
          <AlertCircle size={16} />
          {error}
          <button
            onClick={resetStudio}
            className="ml-auto text-xs underline"
          >
            Recommencer
          </button>
        </div>
      )}
    </div>
  );
}

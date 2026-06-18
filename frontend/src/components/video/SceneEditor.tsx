// ============================================
// SCENE EDITOR — CyberForge
// Éditeur de scènes cinématiques
// ============================================

import { useState } from "react";
import { Film, Camera, Edit3, RefreshCw, Check, X } from "lucide-react";

interface Scene {
  scene_number: number;
  title: string;
  description_fr: string;
  prompt: string;
  camera_move: string;
  mood: string;
  duration: number;
}

interface SceneEditorProps {
  scenes: Scene[];
  onChange: (scenes: Scene[]) => void;
}

const CAMERA_MOVES = [
  "slow dolly forward",
  "slow dolly backward",
  "pan left",
  "pan right",
  "crane up",
  "crane down",
  "static shot",
  "slow zoom in",
  "slow zoom out",
  "orbital shot",
  "handheld subtle",
];

const MOODS = [
  "opening",
  "build",
  "tension",
  "climax",
  "resolution",
  "reveal",
];

const MOOD_COLORS: Record<string, string> = {
  opening: "text-blue-400 bg-blue-950 border-blue-800",
  build: "text-cyan-400 bg-cyan-950 border-cyan-800",
  tension: "text-yellow-400 bg-yellow-950 border-yellow-800",
  climax: "text-orange-400 bg-orange-950 border-orange-800",
  resolution: "text-green-400 bg-green-950 border-green-800",
  reveal: "text-purple-400 bg-purple-950 border-purple-800",
};

export default function SceneEditor({ scenes, onChange }: SceneEditorProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingScene, setEditingScene] = useState<Scene | null>(null);
  const [refining, setRefining] = useState<number | null>(null);
  const [refineInstruction, setRefineInstruction] = useState("");

  const startEdit = (index: number) => {
    setEditingIndex(index);
    setEditingScene({ ...scenes[index] });
  };

  const saveEdit = () => {
    if (editingIndex === null || !editingScene) return;
    const updated = [...scenes];
    updated[editingIndex] = editingScene;
    onChange(updated);
    setEditingIndex(null);
    setEditingScene(null);
  };

  const cancelEdit = () => {
    setEditingIndex(null);
    setEditingScene(null);
  };

  const handleRefine = async (index: number) => {
    if (!refineInstruction.trim()) return;
    setRefining(index);

    try {
      const res = await fetch("http://127.0.0.1:8002/api/video/scenes/refine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scene: scenes[index],
          instruction: refineInstruction,
        }),
      });
      const data = await res.json();
      if (data.success) {
        const updated = [...scenes];
        updated[index] = { ...updated[index], ...data.data };
        onChange(updated);
        setRefineInstruction("");
      }
    } catch (e) {
      console.error("Refine error:", e);
    } finally {
      setRefining(null);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Film size={18} className="text-cyan-400" />
          <h3 className="text-white font-semibold">
            {scenes.length} Scènes Cinématiques
          </h3>
        </div>
        <span className="text-xs text-gray-500">
          {scenes.length * 5}s de contenu
        </span>
      </div>

      {scenes.map((scene, index) => (
        <div
          key={scene.scene_number}
          className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden"
        >
          <div
            className="flex items-center justify-between px-4 py-3 
                          border-b border-gray-800"
          >
            <div className="flex items-center gap-3">
              <span
                className="w-7 h-7 rounded-lg bg-gray-800 flex items-center 
                               justify-center text-cyan-400 text-sm font-bold"
              >
                {scene.scene_number}
              </span>
              <div>
                <p className="text-white text-sm font-medium">{scene.title}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full border 
                                   ${MOOD_COLORS[scene.mood] || "text-gray-400 bg-gray-800 border-gray-700"}`}
                  >
                    {scene.mood}
                  </span>
                  <span className="text-xs text-gray-500 flex items-center gap-1">
                    <Camera size={10} />
                    {scene.camera_move}
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={() =>
                editingIndex === index ? cancelEdit() : startEdit(index)
              }
              className="p-1.5 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <Edit3 size={14} className="text-gray-400" />
            </button>
          </div>

          {editingIndex !== index && (
            <div className="px-4 py-3">
              <div className="bg-blue-950 border border-blue-800 rounded-lg px-3 py-2 mb-2">
                <p className="text-xs text-blue-400 mb-1">🇫🇷 Ce que vous verrez</p>
                <p className="text-blue-100 text-xs leading-relaxed">
                  {scene.description_fr || "Description non disponible"}
                </p>
              </div>

              <details className="mb-2">
                <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300">
                  🇬🇧 Prompt Kling (avancé)
                </summary>
                <p className="text-gray-500 text-xs leading-relaxed mt-1 pl-2 border-l border-gray-700">
                  {scene.prompt}
                </p>
              </details>

              <div className="mt-3">
                <label className="text-xs text-gray-500 mb-1.5 block">
                  ✏️ Modifier en français — VideoAI traduit automatiquement
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Décris en français ce que tu veux changer..."
                    value={refineInstruction}
                    onChange={(e) => setRefineInstruction(e.target.value)}
                    className="flex-1 bg-gray-800 border border-gray-700 rounded-lg 
                             px-3 py-1.5 text-white text-xs placeholder-gray-600
                             focus:outline-none focus:border-cyan-500"
                  />
                  <button
                    onClick={() => void handleRefine(index)}
                    disabled={refining === index}
                    className="px-3 py-1.5 bg-cyan-900 hover:bg-cyan-800 
                             disabled:opacity-50 text-cyan-300 text-xs 
                             rounded-lg transition-colors flex items-center gap-1"
                  >
                    {refining === index ? (
                      <RefreshCw size={12} className="animate-spin" />
                    ) : (
                      <RefreshCw size={12} />
                    )}
                    {refining === index ? "..." : "IA"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {editingIndex === index && editingScene && (
            <div className="px-4 py-3 space-y-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Titre</label>
                <input
                  type="text"
                  value={editingScene.title}
                  onChange={(e) =>
                    setEditingScene({
                      ...editingScene,
                      title: e.target.value,
                    })
                  }
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg 
                             px-3 py-2 text-white text-sm focus:outline-none 
                             focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-xs text-gray-500 mb-1 block">
                  🇫🇷 Description (français)
                </label>
                <textarea
                  value={editingScene.description_fr || ""}
                  onChange={(e) =>
                    setEditingScene({
                      ...editingScene,
                      description_fr: e.target.value,
                    })
                  }
                  rows={3}
                  placeholder="Décris ce que tu veux voir dans cette scène..."
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg 
                             px-3 py-2 text-white text-sm focus:outline-none 
                             focus:border-cyan-500 resize-none"
                />
              </div>

              <div>
                <label className="text-xs text-gray-500 mb-1 block">
                  Prompt Kling (anglais)
                </label>
                <textarea
                  value={editingScene.prompt}
                  onChange={(e) =>
                    setEditingScene({
                      ...editingScene,
                      prompt: e.target.value,
                    })
                  }
                  rows={4}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg 
                             px-3 py-2 text-white text-sm focus:outline-none 
                             focus:border-cyan-500 resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">
                    Mouvement caméra
                  </label>
                  <select
                    value={editingScene.camera_move}
                    onChange={(e) =>
                      setEditingScene({
                        ...editingScene,
                        camera_move: e.target.value,
                      })
                    }
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg 
                               px-3 py-2 text-white text-sm focus:outline-none 
                               focus:border-cyan-500"
                  >
                    {CAMERA_MOVES.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Mood</label>
                  <select
                    value={editingScene.mood}
                    onChange={(e) =>
                      setEditingScene({
                        ...editingScene,
                        mood: e.target.value,
                      })
                    }
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg 
                               px-3 py-2 text-white text-sm focus:outline-none 
                               focus:border-cyan-500"
                  >
                    {MOODS.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex gap-2 pt-1">
                <button
                  onClick={saveEdit}
                  className="flex items-center gap-1 px-3 py-1.5 bg-green-600 
                             hover:bg-green-500 text-white text-xs rounded-lg 
                             transition-colors"
                >
                  <Check size={12} />
                  Sauvegarder
                </button>
                <button
                  onClick={cancelEdit}
                  className="flex items-center gap-1 px-3 py-1.5 bg-gray-800 
                             hover:bg-gray-700 text-gray-300 text-xs rounded-lg 
                             transition-colors"
                >
                  <X size={12} />
                  Annuler
                </button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

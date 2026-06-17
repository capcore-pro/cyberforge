// ============================================
// MEDIA BUILDER VIDEO — CyberForge
// Page principale Video Builder
// ============================================

import { useState } from "react";
import { Film, Sparkles, Library } from "lucide-react";
import VideoStudioPanel from "../components/video/VideoStudioPanel";
import VideoLibrary from "../components/video/VideoLibrary";
import KlingBalanceWidget from "../components/video/KlingBalanceWidget";

type Tab = "studio" | "library";

export default function MediaBuilderVideo() {
  const [activeTab, setActiveTab] = useState<Tab>("studio");
  const [libraryRefresh, setLibraryRefresh] = useState(0);

  const handleProjectCreated = () => {
    setLibraryRefresh(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-black text-white">

      {/* Header */}
      <div className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">

          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-950 border border-cyan-800 
                            flex items-center justify-center">
              <Film size={18} className="text-cyan-400" />
            </div>
            <div>
              <h1 className="text-white font-semibold text-lg">
                Media Builder — Vidéos
              </h1>
              <p className="text-gray-500 text-xs">
                Génération publicités cinématiques IA · Kling 3.0
              </p>
            </div>
          </div>

          {/* Balance Widget compact */}
          <div className="w-64">
            <KlingBalanceWidget />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-800 px-6">
        <div className="max-w-6xl mx-auto flex gap-1">
          {[
            { id: "studio", label: "Studio", icon: Sparkles },
            { id: "library", label: "Bibliothèque", icon: Library }
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id as Tab)}
              className={`flex items-center gap-2 px-4 py-3 text-sm 
                         border-b-2 transition-colors ${
                activeTab === id
                  ? "border-cyan-500 text-white"
                  : "border-transparent text-gray-500 hover:text-gray-300"
              }`}
            >
              <Icon size={15} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-6 py-6">
        {activeTab === "studio" ? (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            {/* Studio Panel — colonne principale */}
            <div className="lg:col-span-2">
              <VideoStudioPanel onProjectCreated={handleProjectCreated} />
            </div>

            {/* Sidebar droite */}
            <div className="space-y-4">

              {/* Info Kling */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <p className="text-xs text-gray-500 mb-3 font-medium uppercase tracking-wider">
                  Tarifs Kling 3.0
                </p>
                <div className="space-y-2">
                  {[
                    { label: "Clip 5s standard", cost: "~6 unités" },
                    { label: "Clip 5s pro", cost: "~10 unités" },
                    { label: "Pub 6 clips", cost: "~60 unités" },
                    { label: "Pack 100 unités", cost: "9,8 $" }
                  ].map(({ label, cost }) => (
                    <div key={label}
                      className="flex items-center justify-between">
                      <span className="text-gray-400 text-xs">{label}</span>
                      <span className="text-cyan-400 text-xs font-medium">
                        {cost}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Tips */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <p className="text-xs text-gray-500 mb-3 font-medium uppercase tracking-wider">
                  Tips cinématiques
                </p>
                <div className="space-y-2">
                  {[
                    "Commence toujours par le mouvement caméra",
                    "6 scènes = 30s de pub parfaite",
                    "Palette cohérente entre toutes les scènes",
                    "Mood progression : opening → reveal",
                    "Pas de texte dans les prompts vidéo"
                  ].map((tip, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-cyan-500 text-xs mt-0.5">⚡</span>
                      <span className="text-gray-400 text-xs">{tip}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Marques */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <p className="text-xs text-gray-500 mb-3 font-medium uppercase tracking-wider">
                  Marques CapCore
                </p>
                <div className="space-y-2">
                  {[
                    { name: "CyberForge", color: "text-cyan-400", desc: "Tech sombre" },
                    { name: "Cap Copy", color: "text-blue-400", desc: "Corporate élégant" },
                    { name: "Lumio", color: "text-yellow-400", desc: "Chaud bienveillant" },
                    { name: "Vocali", color: "text-purple-400", desc: "Sonore vibrant" }
                  ].map(({ name, color, desc }) => (
                    <div key={name} className="flex items-center justify-between">
                      <span className={`text-sm font-medium ${color}`}>
                        {name}
                      </span>
                      <span className="text-gray-600 text-xs">{desc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <VideoLibrary refreshTrigger={libraryRefresh} />
        )}
      </div>
    </div>
  );
}

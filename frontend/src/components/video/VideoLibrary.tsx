// ============================================
// VIDEO LIBRARY — CyberForge
// Bibliothèque des projets vidéo générés
// ============================================

import { useState, useEffect } from "react";
import {
  Film, Download, Play, Clock,
  CheckCircle, AlertCircle, Loader, Trash2
} from "lucide-react";

interface VideoProject {
  id: string;
  title: string;
  brand: string;
  status: string;
  final_video_url: string | null;
  kling_cost_units: number;
  total_duration: number;
  created_at: string;
}

interface VideoLibraryProps {
  onSelectProject?: (project: VideoProject) => void;
  refreshTrigger?: number;
}

const STATUS_CONFIG: Record<string, {
  label: string;
  color: string;
  icon: any;
}> = {
  draft: {
    label: "Brouillon",
    color: "text-gray-400 bg-gray-800 border-gray-700",
    icon: Clock
  },
  generating: {
    label: "Génération...",
    color: "text-cyan-400 bg-cyan-950 border-cyan-800",
    icon: Loader
  },
  assembling: {
    label: "Assemblage...",
    color: "text-yellow-400 bg-yellow-950 border-yellow-800",
    icon: Loader
  },
  done: {
    label: "Terminé",
    color: "text-green-400 bg-green-950 border-green-800",
    icon: CheckCircle
  },
  failed: {
    label: "Échec",
    color: "text-red-400 bg-red-950 border-red-800",
    icon: AlertCircle
  }
};

const BRAND_COLORS: Record<string, string> = {
  cyberforge: "text-cyan-400",
  capcopy: "text-blue-400",
  lumio: "text-yellow-400",
  vocali: "text-purple-400"
};

export default function VideoLibrary({
  onSelectProject,
  refreshTrigger
}: VideoLibraryProps) {
  const [projects, setProjects] = useState<VideoProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [playingId, setPlayingId] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects();
  }, [refreshTrigger]);

  // Auto-refresh si des projets sont en cours
  useEffect(() => {
    const hasActive = projects.some(p =>
      p.status === "generating" || p.status === "assembling"
    );
    if (!hasActive) return;

    const interval = setInterval(fetchProjects, 10000);
    return () => clearInterval(interval);
  }, [projects]);

  const fetchProjects = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8002/api/video/projects");
      const data = await res.json();
      if (data.success) setProjects(data.data);
    } catch (e) {
      console.error("Fetch projects error:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (project: VideoProject) => {
    try {
      const res = await fetch(
        `http://127.0.0.1:8002/api/video/download/${project.id}`
      );
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project.brand}-pub-${project.id.slice(0, 8)}.mp4`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Download error:", e);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map(i => (
          <div key={i}
            className="bg-gray-900 border border-gray-800 rounded-xl p-4 animate-pulse">
            <div className="h-4 bg-gray-800 rounded w-48 mb-2" />
            <div className="h-3 bg-gray-800 rounded w-32" />
          </div>
        ))}
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="text-center py-12">
        <Film size={40} className="text-gray-700 mx-auto mb-3" />
        <p className="text-gray-500 text-sm">Aucune vidéo générée</p>
        <p className="text-gray-600 text-xs mt-1">
          Lance ton premier projet dans le Studio
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Film size={18} className="text-cyan-400" />
          <h3 className="text-white font-semibold">
            Bibliothèque Vidéos
          </h3>
        </div>
        <span className="text-xs text-gray-500">
          {projects.length} projet{projects.length > 1 ? "s" : ""}
        </span>
      </div>

      {/* Liste projets */}
      {projects.map((project) => {
        const statusCfg = STATUS_CONFIG[project.status] || STATUS_CONFIG.draft;
        const StatusIcon = statusCfg.icon;
        const isActive = project.status === "generating" ||
                         project.status === "assembling";

        return (
          <div
            key={project.id}
            className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden
                       hover:border-gray-700 transition-colors"
          >
            {/* Card Header */}
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-gray-800 flex items-center
                                justify-center">
                  <Film size={16} className={
                    BRAND_COLORS[project.brand] || "text-gray-400"
                  } />
                </div>
                <div>
                  <p className="text-white text-sm font-medium">
                    {project.title}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={`text-xs font-medium ${
                      BRAND_COLORS[project.brand] || "text-gray-400"
                    }`}>
                      {project.brand}
                    </span>
                    <span className="text-gray-600 text-xs">·</span>
                    <span className="text-gray-500 text-xs">
                      {formatDate(project.created_at)}
                    </span>
                  </div>
                </div>
              </div>

              {/* Status Badge */}
              <span className={`flex items-center gap-1.5 text-xs px-2.5 py-1 
                               rounded-full border ${statusCfg.color}`}>
                <StatusIcon
                  size={11}
                  className={isActive ? "animate-spin" : ""}
                />
                {statusCfg.label}
              </span>
            </div>

            {/* Stats */}
            <div className="px-4 pb-3 flex items-center gap-4">
              <span className="text-xs text-gray-500">
                🎬 6 scènes · 30s
              </span>
              {project.kling_cost_units > 0 && (
                <span className="text-xs text-gray-500">
                  ⚡ {project.kling_cost_units} unités
                </span>
              )}
            </div>

            {/* Preview vidéo */}
            {project.status === "done" && project.final_video_url && (
              <div className="px-4 pb-3">
                {playingId === project.id ? (
                  <video
                    src={`http://127.0.0.1:8002${project.final_video_url}`}
                    controls
                    autoPlay
                    className="w-full rounded-lg max-h-48 bg-black"
                    onEnded={() => setPlayingId(null)}
                  />
                ) : (
                  <button
                    onClick={() => setPlayingId(project.id)}
                    className="w-full h-24 bg-gray-800 hover:bg-gray-750 rounded-lg 
                               flex items-center justify-center gap-2 
                               text-gray-400 hover:text-white transition-colors
                               border border-gray-700 hover:border-gray-600"
                  >
                    <Play size={20} />
                    <span className="text-sm">Aperçu vidéo</span>
                  </button>
                )}
              </div>
            )}

            {/* Actions */}
            {project.status === "done" && (
              <div className="px-4 pb-3 flex gap-2">
                <button
                  onClick={() => handleDownload(project)}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600 
                             hover:bg-cyan-500 text-white text-xs rounded-lg 
                             transition-colors"
                >
                  <Download size={12} />
                  Télécharger MP4
                </button>
              </div>
            )}

            {/* Progress bar si en cours */}
            {isActive && (
              <div className="h-0.5 bg-gray-800">
                <div className="h-0.5 bg-cyan-500 animate-pulse w-2/3" />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

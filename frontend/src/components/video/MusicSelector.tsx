// ============================================
// MUSIC SELECTOR — CyberForge
// Sélection musique pour vidéo finale
// ============================================

import { useState, useEffect, useRef } from "react";
import { Music, Play, Square, Check } from "lucide-react";

interface MusicTrack {
  id: string;
  name: string;
  url: string;
  duration: number;
  mood: string;
  brand: string;
}

interface MusicSelectorProps {
  brand: string;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

const MOOD_COLORS: Record<string, string> = {
  epic: "text-orange-400 bg-orange-950 border-orange-800",
  corporate: "text-blue-400 bg-blue-950 border-blue-800",
  calm: "text-green-400 bg-green-950 border-green-800",
  energetic: "text-purple-400 bg-purple-950 border-purple-800"
};

export default function MusicSelector({
  brand,
  selectedId,
  onSelect
}: MusicSelectorProps) {
  const [tracks, setTracks] = useState<MusicTrack[]>([]);
  const [loading, setLoading] = useState(true);
  const [playingId, setPlayingId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    fetchMusic();
  }, []);

  useEffect(() => {
    return () => {
      audioRef.current?.pause();
    };
  }, []);

  const fetchMusic = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8002/api/video/music");
      const data = await res.json();
      if (data.success) {
        // Filtrer par marque + tracks universelles
        const filtered = data.data.filter((t: MusicTrack) =>
          t.brand === "all" || t.brand === brand
        );
        setTracks(filtered);
      }
    } catch (e) {
      console.error("Music fetch error:", e);
    } finally {
      setLoading(false);
    }
  };

  const handlePlay = (track: MusicTrack) => {
    if (playingId === track.id) {
      audioRef.current?.pause();
      setPlayingId(null);
      return;
    }

    if (audioRef.current) {
      audioRef.current.pause();
    }

    const audio = new Audio(`http://127.0.0.1:8002${track.url}`);
    audio.volume = 0.4;
    audio.play().catch(() => {});
    audio.onended = () => setPlayingId(null);
    audioRef.current = audio;
    setPlayingId(track.id);
  };

  const handleSelect = (id: string) => {
    if (selectedId === id) {
      onSelect(null);
    } else {
      onSelect(id);
    }
  };

  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map(i => (
          <div key={i}
            className="bg-gray-900 border border-gray-800 rounded-xl 
                       h-14 animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2">

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Music size={16} className="text-cyan-400" />
          <h4 className="text-white text-sm font-medium">
            Musique de fond
          </h4>
        </div>
        {selectedId && (
          <button
            onClick={() => onSelect(null)}
            className="text-xs text-gray-500 hover:text-gray-300 
                       transition-colors"
          >
            Sans musique
          </button>
        )}
      </div>

      {/* Sans musique option */}
      <button
        onClick={() => onSelect(null)}
        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl 
                   border transition-colors text-left ${
          selectedId === null
            ? "bg-gray-800 border-gray-600 text-white"
            : "bg-gray-900 border-gray-800 text-gray-500 hover:border-gray-700"
        }`}
      >
        {selectedId === null && (
          <Check size={14} className="text-cyan-400 shrink-0" />
        )}
        <span className="text-sm">
          Sans musique
        </span>
      </button>

      {/* Tracks */}
      {tracks.map((track) => {
        const isSelected = selectedId === track.id;
        const isPlaying = playingId === track.id;

        return (
          <div
            key={track.id}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl border 
                       transition-colors ${
              isSelected
                ? "bg-cyan-950 border-cyan-700"
                : "bg-gray-900 border-gray-800 hover:border-gray-700"
            }`}
          >
            {/* Play button */}
            <button
              onClick={() => handlePlay(track)}
              className={`w-8 h-8 rounded-lg flex items-center justify-center 
                         shrink-0 transition-colors ${
                isPlaying
                  ? "bg-cyan-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              {isPlaying
                ? <Square size={12} />
                : <Play size={12} />
              }
            </button>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium truncate ${
                isSelected ? "text-white" : "text-gray-300"
              }`}>
                {track.name}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className={`text-xs px-1.5 py-0.5 rounded border ${
                  MOOD_COLORS[track.mood] || 
                  "text-gray-400 bg-gray-800 border-gray-700"
                }`}>
                  {track.mood}
                </span>
              </div>
            </div>

            {/* Select button */}
            <button
              onClick={() => handleSelect(track.id)}
              className={`shrink-0 px-3 py-1.5 rounded-lg text-xs 
                         transition-colors ${
                isSelected
                  ? "bg-cyan-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:text-white"
              }`}
            >
              {isSelected ? (
                <span className="flex items-center gap-1">
                  <Check size={11} />
                  Sélectionnée
                </span>
              ) : "Choisir"}
            </button>
          </div>
        );
      })}

      {tracks.length === 0 && (
        <p className="text-gray-600 text-xs text-center py-4">
          Aucune musique disponible pour cette marque
        </p>
      )}
    </div>
  );
}

import { useCallback, useEffect, useRef, useState } from "react";
import { buildBackendApiUrl } from "@/lib/backend-url";
import {
  deletePortalMedia,
  fetchPortalMedia,
  uploadPortalMedia,
  type MediaItem,
} from "@/lib/portal-api";

interface ProjectMediaPanelProps {
  siteUrl: string;
  isDelivered: boolean;
}

type PortalCheckResult = {
  exists?: boolean;
  client_id?: string;
};

const MAX_MEDIA_BYTES = 5 * 1024 * 1024;

export default function ProjectMediaPanel({
  siteUrl,
  isDelivered,
}: ProjectMediaPanelProps) {
  const [clientId, setClientId] = useState<string | null>(null);
  const [mediaList, setMediaList] = useState<MediaItem[]>([]);
  const [mediaCount, setMediaCount] = useState(0);
  const [mediaLimit, setMediaLimit] = useState(10);
  const [mediaPlan, setMediaPlan] = useState<string | null>(null);
  const [mediaUploading, setMediaUploading] = useState(false);
  const [mediaError, setMediaError] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadMedia = useCallback(async (resolvedClientId: string) => {
    const data = await fetchPortalMedia(resolvedClientId);
    setMediaList(data.media);
    setMediaCount(data.count);
    setMediaLimit(data.limit);
    setMediaPlan(data.plan);
  }, []);

  useEffect(() => {
    if (!isDelivered || !siteUrl.trim()) {
      setClientId(null);
      return;
    }

    let cancelled = false;

    void (async () => {
      try {
        const res = await fetch(
          buildBackendApiUrl(
            `/api/portal-onboarding/check?site_url=${encodeURIComponent(siteUrl.trim())}`,
          ),
        );
        const data = (await res.json()) as PortalCheckResult;
        if (cancelled) return;
        if (data.client_id) {
          setClientId(data.client_id);
          await loadMedia(data.client_id);
        } else {
          setClientId(null);
        }
      } catch {
        if (!cancelled) setClientId(null);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isDelivered, siteUrl, loadMedia]);

  const handleFileChange = async (file: File | null | undefined) => {
    if (!file || !clientId || mediaUploading) return;
    setMediaError(null);

    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setMediaError("Format non supporté — JPEG, PNG ou WebP uniquement");
      return;
    }
    if (file.size > MAX_MEDIA_BYTES) {
      setMediaError("Fichier trop lourd — max 5Mo");
      return;
    }

    setMediaUploading(true);
    try {
      await uploadPortalMedia(clientId, file, undefined, "capcore");
      await loadMedia(clientId);
    } catch (err) {
      setMediaError(err instanceof Error ? err.message : "Erreur upload");
    } finally {
      setMediaUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async (mediaId: string) => {
    if (!window.confirm("Supprimer ?")) return;
    setMediaError(null);
    try {
      await deletePortalMedia(mediaId);
      setMediaList((prev) => prev.filter((x) => x.id !== mediaId));
      setMediaCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      setMediaError(
        err instanceof Error ? err.message : "Erreur suppression photo",
      );
    }
  };

  return (
    <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <div
        role="button"
        tabIndex={0}
        onClick={() => setPanelOpen((open) => !open)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setPanelOpen((open) => !open);
          }
        }}
        className="flex cursor-pointer items-center justify-between border-b border-white/10 py-3"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white">📸 Photos client</span>
          {mediaCount > 0 ? (
            <span className="rounded-full bg-cyan-400/20 px-2 py-0.5 text-xs text-cyan-400">
              {mediaCount}
            </span>
          ) : null}
        </div>
        <span className="text-xs text-white/40">{panelOpen ? "▲" : "▼"}</span>
      </div>

      {panelOpen && clientId ? (
        <div className="space-y-4 pt-3">
          <div className="flex items-center justify-between text-xs text-white/50">
            <span>
              {mediaCount} / {mediaLimit === 500 ? "∞" : mediaLimit} photos
            </span>
            <span className="capitalize text-white/30">
              {mediaPlan || "essentiel"}
            </span>
          </div>

          <div>
            <label className="mb-1 block text-xs text-white/50">
              Ajouter une photo pour ce client
            </label>
            <div
              role="button"
              tabIndex={0}
              onClick={() => !mediaUploading && fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  if (!mediaUploading) fileInputRef.current?.click();
                }
              }}
              className="cursor-pointer rounded-lg border border-dashed border-white/20 p-3 text-center transition-colors hover:border-cyan-400/40"
            >
              <span className="text-xs text-white/30">
                {mediaUploading
                  ? "⏳ Upload en cours..."
                  : "+ Ajouter (JPEG, PNG, WebP — max 5Mo)"}
              </span>
            </div>
            <input
              ref={fileInputRef}
              id={`media-upload-${clientId}`}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              disabled={mediaUploading}
              onChange={(e) => void handleFileChange(e.target.files?.[0])}
            />
            {mediaError ? (
              <p className="mt-1 text-xs text-red-400">{mediaError}</p>
            ) : null}
          </div>

          {mediaList.length > 0 ? (
            <div className="grid grid-cols-3 gap-2">
              {mediaList.map((m) => (
                <div
                  key={m.id}
                  className="group relative aspect-square overflow-hidden rounded-lg"
                >
                  <img
                    src={m.r2_url}
                    alt={m.file_name}
                    className="h-full w-full object-cover"
                  />
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-black/60 p-1 opacity-0 transition-opacity group-hover:opacity-100">
                    <button
                      type="button"
                      onClick={() => void navigator.clipboard.writeText(m.r2_url)}
                      className="w-full rounded bg-white/20 px-2 py-0.5 text-xs text-white hover:bg-white/30"
                    >
                      Copier URL
                    </button>
                    <button
                      type="button"
                      onClick={() => void handleDelete(m.id)}
                      className="w-full rounded bg-red-500/80 px-2 py-0.5 text-xs text-white hover:bg-red-500"
                    >
                      🗑️ Supprimer
                    </button>
                  </div>
                  <p className="absolute bottom-0 left-0 right-0 truncate bg-black/40 px-1 py-0.5 text-xs text-white/60">
                    {m.uploaded_by === "capcore" ? "⚡ Mat" : "👤 Client"}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-4 text-center text-xs text-white/30">
              Aucune photo — le client n&apos;a rien uploadé encore
            </p>
          )}
        </div>
      ) : null}

      {panelOpen && !clientId && isDelivered ? (
        <p className="pt-3 text-xs text-white/30">
          Aucun compte portail associé à ce projet
        </p>
      ) : null}

      {panelOpen && !isDelivered ? (
        <p className="pt-3 text-xs text-white/30">
          Disponible après livraison du projet
        </p>
      ) : null}
    </div>
  );
}

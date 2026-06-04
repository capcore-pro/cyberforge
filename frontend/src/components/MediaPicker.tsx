import { useCallback, useEffect, useMemo, useState } from "react";
import { MediaAddPanel } from "@/components/media/MediaAddPanel";
import { MediaAssetCard } from "@/components/media/MediaAssetCard";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  fetchMediaAssets,
  setProjectCover,
  type MediaAsset,
} from "@/lib/media-api";

export type { MediaAsset } from "@/lib/media-api";

export interface MediaPickerProps {
  open: boolean;
  onClose: () => void;
  onSelect: (asset: MediaAsset) => void;
  title?: string;
  projectKey?: string;
  projectRefId?: string;
}

type PickerTab = "library" | "add";

/**
 * Sélection d'une image médiathèque — bibliothèque locale ou ajout Pexels/Replicate/import.
 */
export function MediaPicker({
  open,
  onClose,
  onSelect,
  title = "Choisir une image",
  projectKey,
  projectRefId,
}: MediaPickerProps) {
  const [tab, setTab] = useState<PickerTab>("library");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(t);
  }, [search]);

  useEffect(() => {
    if (open) {
      setTab("library");
      setError(null);
    }
  }, [open]);

  const load = useCallback(async () => {
    if (!open) return;
    setLoading(true);
    setError(null);
    const res = await fetchMediaAssets({
      type: "image",
      search: debouncedSearch || undefined,
      project_id: projectRefId,
      limit: 200,
    });
    setLoading(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Impossible de charger la médiathèque."));
      setAssets([]);
      return;
    }
    setAssets((res.data ?? []).filter((a) => a.type === "image"));
  }, [open, debouncedSearch, projectRefId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function pickAsset(asset: MediaAsset) {
    if (projectKey) {
      setBusyId(asset.id);
      const res = await setProjectCover(projectKey, asset.id);
      setBusyId(null);
      if (!res.ok) {
        setError(apiErrorMessage(res, "Association couverture échouée."));
        return;
      }
    }
    onSelect(asset);
    onClose();
  }

  const emptyLibrary = useMemo(
    () => !loading && assets.length === 0 && !debouncedSearch,
    [loading, assets.length, debouncedSearch],
  );

  if (!open) {
    return null;
  }

  return (
    <>
      <div
        className="fixed inset-0 z-[60] flex items-center justify-center bg-black/75 p-4"
        role="dialog"
        aria-modal
        aria-labelledby="media-picker-title"
      >
        <div className="cyber-panel flex max-h-[90vh] w-full max-w-5xl flex-col border-cyber-violet/40">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h2 id="media-picker-title" className="text-lg font-semibold text-cyber-text">
                {title}
              </h2>
              <p className="mt-1 text-xs text-cyber-muted">
                Bibliothèque locale ou recherche Pexels / Unsplash / Replicate.
              </p>
            </div>
            <div className="flex shrink-0 gap-2">
              <button
                type="button"
                className="cyber-action-btn cyber-action-btn-primary text-xs"
                onClick={() => setAddOpen(true)}
              >
                + Nouvelle image
              </button>
              <button type="button" className="cyber-action-btn text-xs" onClick={onClose}>
                Fermer
              </button>
            </div>
          </div>

          <div className="mb-4 flex gap-2">
            <button
              type="button"
              onClick={() => setTab("library")}
              className={`rounded px-3 py-1.5 text-xs ${
                tab === "library" ? "bg-cyber-accent/20 text-cyber-neon" : "text-cyber-muted"
              }`}
            >
              Bibliothèque
            </button>
          </div>

          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filtrer par nom ou tag…"
            className="cyber-prompt-field mb-4 min-h-0 w-full text-sm"
          />

          {error ? (
            <p className="mb-3 rounded border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
              {error}
            </p>
          ) : null}

          <div className="min-h-0 flex-1 overflow-y-auto">
            {loading ? (
              <p className="py-8 text-center text-sm text-cyber-muted animate-pulse">
                Chargement…
              </p>
            ) : emptyLibrary ? (
              <div className="space-y-4 py-8 text-center">
                <p className="text-sm text-cyber-muted">
                  Aucune image pour l&apos;instant — générez votre premier projet pour alimenter
                  la médiathèque
                </p>
                <button
                  type="button"
                  className="cyber-generate-btn px-5 py-2.5 text-xs"
                  onClick={() => setAddOpen(true)}
                >
                  Rechercher des photos
                </button>
              </div>
            ) : assets.length === 0 ? (
              <p className="py-8 text-center text-sm text-cyber-muted">
                Aucun résultat pour cette recherche.
              </p>
            ) : (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
                {assets.map((asset) => (
                  <MediaAssetCard
                    key={asset.id}
                    asset={asset}
                    selectable
                    busy={busyId === asset.id}
                    onSelect={(a) => void pickAsset(a)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <MediaAddPanel
        open={addOpen}
        initialTab="import"
        projectId={projectRefId}
        onClose={() => setAddOpen(false)}
        onAdded={(asset) => {
          setAddOpen(false);
          void load().then(() => void pickAsset(asset));
        }}
      />
    </>
  );
}

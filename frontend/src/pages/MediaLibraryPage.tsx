import { useCallback, useEffect, useState } from "react";
import { MediaAssetCard } from "@/components/media/MediaAssetCard";
import {
  MediaFiltersBar,
  type SourceFilter,
  type TypeFilter,
} from "@/components/media/MediaFiltersBar";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  deleteMediaAsset,
  fetchMediaAssets,
  getAssetPublicUrl,
  syncMediaAssetR2,
  uploadMediaAsset,
  type MediaAsset,
} from "@/lib/media-api";

function UploadModal({
  open,
  onClose,
  onUploaded,
}: {
  open: boolean;
  onClose: () => void;
  onUploaded: () => void;
}) {
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setError(null);
      setDragOver(false);
    }
  }, [open]);

  if (!open) return null;

  async function handleFiles(files: FileList | File[]) {
    const list = Array.from(files);
    if (!list.length) return;
    setBusy(true);
    setError(null);
    for (const file of list) {
      const res = await uploadMediaAsset(file);
      if (!res.ok) {
        setError(apiErrorMessage(res, `Échec upload : ${file.name}`));
        setBusy(false);
        return;
      }
    }
    setBusy(false);
    onUploaded();
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
      role="dialog"
      aria-modal
      aria-labelledby="upload-title"
    >
      <div className="cyber-panel w-full max-w-lg border-cyber-neon/30">
        <h2 id="upload-title" className="text-lg font-semibold text-cyber-text">
          Uploader des fichiers
        </h2>
        <p className="mt-1 text-xs text-cyber-muted">
          Images (JPEG, PNG, WebP, GIF), ZIP ou PDF — max 50 Mo par fichier.
        </p>
        {error ? (
          <p className="mt-3 rounded border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        ) : null}
        <div
          className={`mt-4 flex min-h-[160px] flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition ${
            dragOver
              ? "border-cyber-neon bg-cyber-accent/10"
              : "border-cyber-border bg-cyber-bg/40"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            void handleFiles(e.dataTransfer.files);
          }}
        >
          <p className="text-sm text-cyber-muted">Glissez-déposez ici</p>
          <p className="my-2 text-xs text-cyber-muted">ou</p>
          <label className="cyber-action-btn cyber-action-btn-primary cursor-pointer">
            Parcourir…
            <input
              type="file"
              className="sr-only"
              multiple
              accept="image/jpeg,image/png,image/webp,image/gif,application/zip,application/pdf,.zip,.pdf"
              disabled={busy}
              onChange={(e) => {
                const files = e.target.files;
                if (files?.length) void handleFiles(files);
                e.target.value = "";
              }}
            />
          </label>
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" className="cyber-action-btn" onClick={onClose} disabled={busy}>
            Annuler
          </button>
        </div>
        {busy ? (
          <p className="mt-2 text-center text-xs text-cyber-neon animate-pulse">
            Envoi en cours…
          </p>
        ) : null}
      </div>
    </div>
  );
}

/**
 * Médiathèque — grille d'assets, filtres et upload.
 */
export function MediaLibraryPage() {
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("");
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(t);
  }, [search]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await fetchMediaAssets({
      type: typeFilter || undefined,
      source: sourceFilter || undefined,
      search: debouncedSearch || undefined,
      limit: 200,
    });
    setLoading(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Impossible de charger la médiathèque."));
      setAssets([]);
      return;
    }
    setAssets(res.data ?? []);
  }, [typeFilter, sourceFilter, debouncedSearch]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCopyUrl(asset: MediaAsset) {
    const url = getAssetPublicUrl(asset);
    try {
      await navigator.clipboard.writeText(url);
      setToast("URL copiée.");
    } catch {
      setToast(url);
    }
    window.setTimeout(() => setToast(null), 2500);
  }

  async function handleSyncR2(asset: MediaAsset) {
    setBusyId(asset.id);
    const res = await syncMediaAssetR2(asset.id, true);
    setBusyId(null);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Synchronisation R2 échouée."));
      return;
    }
    setToast("Asset synchronisé sur R2.");
    window.setTimeout(() => setToast(null), 2500);
    void load();
  }

  async function handleDelete(asset: MediaAsset) {
    if (!window.confirm(`Supprimer « ${asset.filename} » ?`)) return;
    setBusyId(asset.id);
    const res = await deleteMediaAsset(asset.id);
    setBusyId(null);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Suppression impossible."));
      return;
    }
    void load();
  }

  return (
    <div className="mx-auto max-w-7xl">
      <header className="mb-6">
        <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-cyber-violet">
          Assets
        </p>
        <h1 className="cyber-glitch-title mt-1 text-2xl font-bold text-cyber-text md:text-3xl">
          Médiathèque
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-cyber-muted">
          Images générées (Replicate, Unsplash), uploads manuels et synchronisation Cloudflare R2.
        </p>
      </header>

      <MediaFiltersBar
        typeFilter={typeFilter}
        sourceFilter={sourceFilter}
        search={search}
        onTypeChange={setTypeFilter}
        onSourceChange={setSourceFilter}
        onSearchChange={setSearch}
        trailing={
          <button
            type="button"
            className="cyber-generate-btn px-5 py-2.5 text-xs"
            onClick={() => setUploadOpen(true)}
          >
            Uploader
          </button>
        }
      />

      {toast ? (
        <p className="mb-4 rounded border border-cyber-neon/40 bg-cyber-accent/10 px-3 py-2 text-sm text-cyber-neon">
          {toast}
        </p>
      ) : null}

      {error ? (
        <p className="mb-4 rounded border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="py-12 text-center text-sm text-cyber-muted animate-pulse">
          Chargement de la médiathèque…
        </p>
      ) : assets.length === 0 ? (
        <div className="cyber-panel py-12 text-center text-sm text-cyber-muted">
          Aucun asset. Utilisez « Uploader » ou générez des images via le pipeline.
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
          {assets.map((asset) => (
            <MediaAssetCard
              key={asset.id}
              asset={asset}
              busy={busyId === asset.id}
              onCopyUrl={handleCopyUrl}
              onSyncR2={handleSyncR2}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUploaded={() => void load()}
      />
    </div>
  );
}

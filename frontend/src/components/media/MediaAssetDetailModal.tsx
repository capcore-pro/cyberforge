import { useEffect, useState } from "react";
import { BackButton } from "@/components/BackButton";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  deleteMediaAsset,
  formatBytes,
  getAssetAbsolutePublicUrl,
  getAssetPublicUrl,
  providerLabel,
  setProjectCover,
  type MediaAsset,
} from "@/lib/media-api";
import { loadAllUnifiedProjects, type UnifiedProject } from "@/lib/unified-projects";

export interface MediaAssetDetailModalProps {
  asset: MediaAsset | null;
  onClose: () => void;
  onDeleted: () => void;
  onCoverSet?: () => void;
}

export function MediaAssetDetailModal({
  asset,
  onClose,
  onDeleted,
  onCoverSet,
}: MediaAssetDetailModalProps) {
  const [projects, setProjects] = useState<UnifiedProject[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [selectedProjectKey, setSelectedProjectKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [imgError, setImgError] = useState(false);

  useEffect(() => {
    if (!asset) return;
    setImgError(false);
    setError(null);
    setToast(null);
    setConfirmDelete(false);
    setSelectedProjectKey("");
  }, [asset?.id]);

  useEffect(() => {
    if (!asset) return;
    setProjectsLoading(true);
    void loadAllUnifiedProjects().then((items) => {
      setProjects(items);
      setProjectsLoading(false);
    });
  }, [asset?.id]);

  if (!asset) return null;

  const imageUrl = getAssetPublicUrl(asset);
  const shareUrl = getAssetAbsolutePublicUrl(asset);
  const source = providerLabel(asset);
  const dateLabel = new Date(asset.created_at).toLocaleString("fr-FR", {
    dateStyle: "long",
    timeStyle: "short",
  });

  async function copyUrl() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setToast("URL copiée.");
    } catch {
      setToast(shareUrl);
    }
    window.setTimeout(() => setToast(null), 2500);
  }

  async function handleUseInProject() {
    if (!selectedProjectKey) {
      setError("Sélectionnez un projet.");
      return;
    }
    setBusy(true);
    setError(null);
    const res = await setProjectCover(selectedProjectKey, asset!.id);
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Impossible d'associer l'image au projet."));
      return;
    }
    setToast("Image définie comme couverture du projet.");
    onCoverSet?.();
    window.setTimeout(() => setToast(null), 2500);
  }

  async function handleDelete() {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setBusy(true);
    setError(null);
    const res = await deleteMediaAsset(asset!.id);
    setBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Suppression impossible."));
      setConfirmDelete(false);
      return;
    }
    onDeleted();
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal
      aria-labelledby="media-detail-title"
      onClick={onClose}
    >
      <div
        className="cyber-panel flex max-h-[95vh] w-full max-w-4xl flex-col overflow-hidden border-cyber-neon/30"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-cyber-border px-4 py-3">
          <BackButton label="Fermer" onClick={onClose} />
          <h2 id="media-detail-title" className="truncate px-4 text-sm font-medium text-cyber-text">
            {asset.filename}
          </h2>
          <span className="w-16" aria-hidden />
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4 lg:flex-row">
          <div className="flex min-h-[200px] flex-1 items-center justify-center rounded-lg bg-cyber-bg/80 p-2 lg:min-h-[320px]">
            {asset.type === "image" && !imgError ? (
              <img
                src={imageUrl}
                alt={asset.filename}
                className="max-h-[60vh] max-w-full object-contain"
                onError={() => setImgError(true)}
              />
            ) : (
              <p className="text-sm text-cyber-muted">Aperçu non disponible</p>
            )}
          </div>

          <div className="flex w-full shrink-0 flex-col gap-4 lg:w-72">
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-cyber-muted">Fichier</dt>
                <dd className="break-all text-cyber-text">{asset.filename}</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-cyber-muted">Taille</dt>
                <dd className="text-cyber-text">{formatBytes(asset.size_bytes)}</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-cyber-muted">Date</dt>
                <dd className="text-cyber-text">{dateLabel}</dd>
              </div>
              <div>
                <dt className="text-[10px] uppercase tracking-wider text-cyber-muted">Source</dt>
                <dd className="text-cyber-text">{source}</dd>
              </div>
            </dl>

            {error ? (
              <p className="rounded border border-red-500/40 bg-red-950/30 px-3 py-2 text-xs text-red-200">
                {error}
              </p>
            ) : null}
            {toast ? (
              <p className="rounded border border-cyber-neon/40 bg-cyber-accent/10 px-3 py-2 text-xs text-cyber-neon">
                {toast}
              </p>
            ) : null}

            <div className="flex flex-col gap-2">
              <button
                type="button"
                disabled={busy}
                onClick={() => void copyUrl()}
                className="cyber-action-btn w-full text-xs"
              >
                Copier l&apos;URL
              </button>
              <a
                href={imageUrl}
                download={asset.filename}
                className="cyber-action-btn w-full text-center text-xs"
              >
                Télécharger
              </a>
              <label className="space-y-1">
                <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
                  Utiliser dans un projet
                </span>
                <select
                  value={selectedProjectKey}
                  disabled={busy || projectsLoading}
                  onChange={(e) => setSelectedProjectKey(e.target.value)}
                  className="cyber-prompt-field w-full text-xs"
                >
                  <option value="">— Choisir un projet —</option>
                  {projects.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                disabled={busy || !selectedProjectKey}
                onClick={() => void handleUseInProject()}
                className="cyber-action-btn cyber-action-btn-primary w-full text-xs disabled:opacity-50"
              >
                Définir comme couverture
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleDelete()}
                className={`cyber-action-btn w-full text-xs ${
                  confirmDelete
                    ? "border-red-500 bg-red-950/50 text-red-200"
                    : "border-red-500/40 text-red-300"
                }`}
              >
                {confirmDelete ? "Confirmer la suppression" : "Supprimer"}
              </button>
              {confirmDelete ? (
                <button
                  type="button"
                  className="cyber-action-btn w-full text-xs"
                  onClick={() => setConfirmDelete(false)}
                >
                  Annuler
                </button>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

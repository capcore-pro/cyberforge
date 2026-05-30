import { useCallback, useEffect, useState } from "react";
import { MediaAddPanel } from "@/components/media/MediaAddPanel";
import { MediaAssetCard } from "@/components/media/MediaAssetCard";
import { MediaAssetDetailModal } from "@/components/media/MediaAssetDetailModal";
import {
  MediaFiltersBar,
  type SourceFilter,
  type TypeFilter,
} from "@/components/media/MediaFiltersBar";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  deleteMediaAsset,
  fetchMediaAssets,
  getAssetAbsolutePublicUrl,
  getAssetPublicUrl,
  type MediaAsset,
} from "@/lib/media-api";

/**
 * Médiathèque — grille d'assets locaux, recherche et ajout manuel.
 */
export function MediaLibraryPage() {
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("");
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [addInitialTab, setAddInitialTab] = useState<"search" | "generate" | "import">("search");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [detailAsset, setDetailAsset] = useState<MediaAsset | null>(null);

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

  function openAdd(tab: "search" | "generate" | "import" = "search") {
    setAddInitialTab(tab);
    setAddOpen(true);
  }

  async function handleCopyUrl(asset: MediaAsset) {
    const url = getAssetAbsolutePublicUrl(asset);
    try {
      await navigator.clipboard.writeText(url);
      setToast("URL copiée.");
    } catch {
      setToast(url);
    }
    window.setTimeout(() => setToast(null), 2500);
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

  const imageCount = assets.filter((a) => a.type === "image").length;

  return (
    <div className="mx-auto max-w-7xl">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="cf-section-label">Ressources</p>
          <h1 className="cf-page-title mt-1">Médiathèque</h1>
          <p className="mt-2 max-w-2xl text-sm text-cf-muted">
            Images stockées localement — recherche Pexels/Unsplash, génération Replicate et
            imports manuels.
          </p>
        </div>
        <button
          type="button"
          aria-label="Ajouter une image"
          className="flex h-11 w-11 items-center justify-center rounded-full border border-cf-gold/50 bg-cf-active text-xl font-light text-cf-gold transition hover:border-cf-gold hover:bg-cf-gold-subtle"
          onClick={() => openAdd("search")}
        >
          +
        </button>
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
            className="cyber-action-btn cyber-action-btn-primary text-xs"
            onClick={() => openAdd("import")}
          >
            Importer un fichier
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
        <div className="cyber-panel space-y-4 py-12 text-center">
          <p className="text-sm text-cyber-muted">
            Aucune image pour l&apos;instant — générez votre premier projet pour alimenter la
            médiathèque
          </p>
          <button
            type="button"
            className="cyber-generate-btn px-5 py-2.5 text-xs"
            onClick={() => openAdd("search")}
          >
            Rechercher des photos
          </button>
        </div>
      ) : (
        <>
          {imageCount === 0 ? (
            <p className="mb-4 text-sm text-cf-muted">
              Aucune image — utilisez « + » pour en ajouter via Pexels, Unsplash ou Replicate.
            </p>
          ) : null}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
            {assets.map((asset) => (
              <MediaAssetCard
                key={asset.id}
                asset={asset}
                busy={busyId === asset.id}
                onOpen={setDetailAsset}
                onCopyUrl={handleCopyUrl}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </>
      )}

      <MediaAddPanel
        open={addOpen}
        initialTab={addInitialTab}
        onClose={() => setAddOpen(false)}
        onAdded={() => {
          void load();
          setToast("Image ajoutée à la médiathèque.");
          window.setTimeout(() => setToast(null), 2500);
        }}
      />

      <MediaAssetDetailModal
        asset={detailAsset}
        onClose={() => setDetailAsset(null)}
        onDeleted={() => void load()}
      />
    </div>
  );
}

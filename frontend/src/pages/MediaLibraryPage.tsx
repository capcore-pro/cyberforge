import { useCallback, useEffect, useMemo, useState } from "react";
import { ImageIcon } from "lucide-react";
import { MediaAddPanel } from "@/components/media/MediaAddPanel";
import { MediaAssetCard } from "@/components/media/MediaAssetCard";
import { MediaAssetDetailModal } from "@/components/media/MediaAssetDetailModal";
import {
  MediaFiltersBar,
  type SourceFilter,
  type TypeFilter,
} from "@/components/media/MediaFiltersBar";
import {
  GLASS_SECTION,
  GOLD_BTN,
  logAccountingApiError,
  shouldSilenceApiError,
} from "@/components/accounting/accounting-theme";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  deleteMediaAsset,
  fetchMediaAssets,
  getAssetAbsolutePublicUrl,
  upscaleMediaAsset,
  type MediaAsset,
} from "@/lib/media-api";
import { fetchSecretsStatus } from "@/lib/secrets-api";

function reportError(context: string, res: { ok: boolean; status?: number }) {
  const msg = apiErrorMessage(res, `${context} impossible.`);
  logAccountingApiError(`Médiathèque / ${context}`, msg);
  return shouldSilenceApiError(msg) ? null : msg;
}

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
  const [addInitialTab, setAddInitialTab] = useState<"generate" | "import" | "search">(
    "import",
  );
  const [replicateConfigured, setReplicateConfigured] = useState(true);
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
      setError(reportError("chargement", res));
      setAssets([]);
      return;
    }
    setAssets(res.data ?? []);
  }, [typeFilter, sourceFilter, debouncedSearch]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void fetchSecretsStatus().then((res) => {
      if (res.ok && res.data) {
        setReplicateConfigured(Boolean(res.data.replicate));
      }
    });
  }, []);

  function openAdd(tab: "generate" | "import" | "search" = "import") {
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

  async function handleUpscale(asset: MediaAsset, scale: 2 | 4) {
    setBusyId(asset.id);
    setError(null);
    const res = await upscaleMediaAsset(asset.id, scale);
    setBusyId(null);
    if (!res.ok || !res.data) {
      setError(
        reportError(
          "upscaling",
          res.ok ? { ok: false, status: 502 } : res,
        ) ?? `Upscaling échoué — vérifiez REPLICATE_API_KEY.`,
      );
      return;
    }
    setToast(`Image upscalée ×${scale}.`);
    window.setTimeout(() => setToast(null), 2500);
    void load();
  }

  async function handleDelete(asset: MediaAsset) {
    if (!window.confirm(`Supprimer « ${asset.filename} » ?`)) return;
    setBusyId(asset.id);
    const res = await deleteMediaAsset(asset.id);
    setBusyId(null);
    if (!res.ok) {
      setError(reportError("suppression", res));
      return;
    }
    void load();
  }

  const imageCount = useMemo(
    () => assets.filter((a) => a.type === "image").length,
    [assets],
  );

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-[#d4a843]">
            Ressources
          </p>
          <h1 className="mt-1 text-2xl font-semibold text-white">Médiathèque</h1>
          <p className="mt-2 max-w-2xl text-sm text-white/50">
            Images stockées localement — recherche Pexels/Unsplash, génération Replicate et
            imports manuels.
          </p>
        </div>
        <button
          type="button"
          aria-label="Ajouter une image"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-[#d4a843] text-xl font-light text-black shadow-lg transition hover:bg-[#d4a843]/80"
          onClick={() => openAdd("import")}
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
            className={GOLD_BTN}
            onClick={() => openAdd("import")}
          >
            Importer un fichier
          </button>
        }
      />

      {toast ? (
        <p className="rounded-lg border border-[#d4a843]/30 bg-[#d4a843]/10 px-4 py-3 text-sm text-[#d4a843]">
          {toast}
        </p>
      ) : null}

      {error ? (
        <p className="rounded-lg border border-red-500/30 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="animate-pulse py-12 text-center text-sm text-white/50">
          Chargement de la médiathèque…
        </p>
      ) : assets.length === 0 ? (
        <div
          className={`${GLASS_SECTION} flex min-h-[300px] flex-col items-center justify-center gap-4 text-center`}
        >
          <ImageIcon className="h-12 w-12 text-white/20" aria-hidden />
          <p className="text-sm text-white/30">Aucune image pour l&apos;instant</p>
          <p className="text-xs text-white/20">
            Générez, importez ou recherchez des visuels pour vos projets clients
          </p>
          <button
            type="button"
            className={`${GOLD_BTN} px-6 py-2.5`}
            onClick={() => openAdd("search")}
          >
            Rechercher des photos
          </button>
        </div>
      ) : (
        <>
          {imageCount === 0 ? (
            <p className="text-sm text-white/50">
              Aucune image — utilisez « + » pour en ajouter via Pexels, Unsplash ou Replicate.
            </p>
          ) : null}
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
            {assets.map((asset) => (
              <MediaAssetCard
                key={asset.id}
                asset={asset}
                busy={busyId === asset.id}
                replicateConfigured={replicateConfigured}
                onOpen={setDetailAsset}
                onCopyUrl={handleCopyUrl}
                onDelete={handleDelete}
                onUpscale={handleUpscale}
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

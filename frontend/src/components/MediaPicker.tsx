import { useCallback, useEffect, useMemo, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  fetchMediaAssets,
  type MediaAsset,
  type MediaType,
} from "@/lib/media-api";
import { MediaAssetCard } from "@/components/media/MediaAssetCard";
import {
  MediaFiltersBar,
  type SourceFilter,
  type TypeFilter,
} from "@/components/media/MediaFiltersBar";

export type { MediaAsset } from "@/lib/media-api";

export interface MediaPickerProps {
  open: boolean;
  onClose: () => void;
  onSelect: (asset: MediaAsset) => void;
  /** Filtre par type : une valeur ou plusieurs types acceptés. */
  accept?: MediaType | MediaType[];
  title?: string;
  projectId?: string;
}

function acceptToTypeFilter(
  accept: MediaType | MediaType[] | undefined,
): TypeFilter {
  if (!accept) return "";
  if (Array.isArray(accept)) {
    return accept.length === 1 ? accept[0] : "";
  }
  return accept;
}

/**
 * Modal de sélection d'un asset médiathèque (fiches projet, vitrines, etc.).
 */
export function MediaPicker({
  open,
  onClose,
  onSelect,
  accept,
  title = "Choisir un média",
  projectId,
}: MediaPickerProps) {
  const lockedType = useMemo(() => acceptToTypeFilter(accept), [accept]);
  const acceptSet = useMemo(() => {
    if (!accept) return null;
    return new Set(Array.isArray(accept) ? accept : [accept]);
  }, [accept]);

  const [typeFilter, setTypeFilter] = useState<TypeFilter>(lockedType);
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setTypeFilter(lockedType);
  }, [lockedType]);

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(t);
  }, [search]);

  const load = useCallback(async () => {
    if (!open) return;
    setLoading(true);
    setError(null);
    const res = await fetchMediaAssets({
      type: typeFilter || undefined,
      source: sourceFilter || undefined,
      project_id: projectId,
      search: debouncedSearch || undefined,
      limit: 200,
    });
    setLoading(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Impossible de charger la médiathèque."));
      setAssets([]);
      return;
    }
    let rows = res.data ?? [];
    if (acceptSet && acceptSet.size > 1) {
      rows = rows.filter((a) => acceptSet.has(a.type));
    }
    setAssets(rows);
  }, [open, typeFilter, sourceFilter, debouncedSearch, projectId, acceptSet]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/75 p-4"
      role="dialog"
      aria-modal
      aria-labelledby="media-picker-title"
    >
      <div className="cyber-panel flex max-h-[90vh] w-full max-w-5xl flex-col border-cyber-violet/40">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 id="media-picker-title" className="text-lg font-semibold text-cyber-text">
              {title}
            </h2>
            <p className="mt-1 text-xs text-cyber-muted">
              Cliquez sur un asset pour le sélectionner.
            </p>
          </div>
          <button type="button" className="cyber-action-btn" onClick={onClose}>
            Fermer
          </button>
        </div>

        <MediaFiltersBar
          typeFilter={typeFilter}
          sourceFilter={sourceFilter}
          search={search}
          onTypeChange={setTypeFilter}
          onSourceChange={setSourceFilter}
          onSearchChange={setSearch}
          typeDisabled={Boolean(lockedType)}
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
          ) : assets.length === 0 ? (
            <p className="py-8 text-center text-sm text-cyber-muted">
              Aucun asset trouvé.
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
              {assets.map((asset) => (
                <MediaAssetCard
                  key={asset.id}
                  asset={asset}
                  selectable
                  onSelect={(a) => {
                    onSelect(a);
                    onClose();
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

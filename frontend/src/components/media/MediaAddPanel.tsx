import { useEffect, useState } from "react";
import { BackButton } from "@/components/BackButton";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  generateMediaImage,
  getAssetPublicUrl,
  searchMediaPhotos,
  uploadMediaAsset,
  type MediaAsset,
} from "@/lib/media-api";

type AddTab = "generate" | "import" | "search";

export interface PexelsSearchPreview {
  url: string;
  thumbnail: string;
  author: string;
  source: string;
}

export interface MediaAddPanelProps {
  open: boolean;
  onClose: () => void;
  onAdded: (asset: MediaAsset) => void;
  /** Onglet ouvert par défaut (ex. depuis état vide). */
  initialTab?: AddTab;
  projectId?: string;
}

export function MediaAddPanel({
  open,
  onClose,
  onAdded,
  initialTab = "import",
  projectId,
}: MediaAddPanelProps) {
  const [tab, setTab] = useState<AddTab>(initialTab);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [generatePrompt, setGeneratePrompt] = useState("");
  const [importDrag, setImportDrag] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<PexelsSearchPreview[]>([]);
  const [savedAssets, setSavedAssets] = useState<MediaAsset[]>([]);

  useEffect(() => {
    if (open) {
      setTab(initialTab);
      setError(null);
      setBusy(false);
      setSearchResults([]);
      setSavedAssets([]);
    }
  }, [open, initialTab]);

  if (!open) return null;

  async function handleGenerate() {
    const prompt = generatePrompt.trim();
    if (prompt.length < 3) {
      setError("Décrivez l'image à générer (3 caractères minimum).");
      return;
    }
    setBusy(true);
    setError(null);
    const res = await generateMediaImage({ prompt, project_id: projectId });
    setBusy(false);
    if (!res.ok || !res.data) {
      setError(
        apiErrorMessage(
          res,
          "Génération Replicate échouée — vérifiez REPLICATE_API_KEY.",
        ),
      );
      return;
    }
    onAdded(res.data);
    onClose();
  }

  async function handleSearch() {
    const q = searchQuery.trim();
    if (q.length < 2) {
      setError("Saisissez au moins 2 caractères pour la recherche.");
      return;
    }
    setBusy(true);
    setError(null);
    const res = await searchMediaPhotos(q, 12);
    setBusy(false);
    if (!res.ok || !res.data) {
      setError(apiErrorMessage(res, "Recherche Pexels impossible."));
      setSearchResults([]);
      setSavedAssets([]);
      return;
    }
    setSavedAssets(res.data);
    setSearchResults(
      res.data.map((asset) => ({
        url: asset.local_url ?? "",
        thumbnail: asset.local_url ?? "",
        author: asset.tags.find((t) => t.startsWith("author:"))?.replace("author:", "") ?? "",
        source: "pexels",
      })),
    );
  }

  async function handleAddSearchResult(index: number) {
    const asset = savedAssets[index];
    if (!asset) return;
    onAdded(asset);
    onClose();
  }

  async function handleFiles(files: FileList | File[]) {
    const list = Array.from(files).filter(
      (f) => f.type.startsWith("image/") || f.type === "application/pdf",
    );
    if (!list.length) {
      setError("Sélectionnez une image (JPEG, PNG, WebP, GIF).");
      return;
    }
    setBusy(true);
    setError(null);
    for (const file of list) {
      const res = await uploadMediaAsset(file, {
        project_id: projectId,
        tags: "import,manual",
      });
      if (!res.ok || !res.data) {
        setError(apiErrorMessage(res, `Import échoué : ${file.name}`));
        setBusy(false);
        return;
      }
      onAdded(res.data);
      onClose();
      return;
    }
    setBusy(false);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
      role="dialog"
      aria-modal
      aria-labelledby="media-add-title"
    >
      <div className="cyber-panel flex max-h-[90vh] w-full max-w-2xl flex-col border-cyber-neon/30">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <BackButton onClick={onClose} />
            <h2 id="media-add-title" className="mt-2 text-lg font-semibold text-cyber-text">
              Ajouter une image
            </h2>
          </div>
        </div>

        <div className="mb-4 flex gap-2 border-b border-cyber-border pb-2">
          {(
            [
              ["search", "Rechercher"],
              ["generate", "Générer"],
              ["import", "Importer"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => {
                setTab(id);
                setError(null);
              }}
              className={`rounded px-3 py-1.5 text-xs font-medium transition ${
                tab === id
                  ? "bg-cyber-accent/20 text-cyber-neon"
                  : "text-cyber-muted hover:text-cyber-text"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {error ? (
          <p className="mb-3 rounded border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        ) : null}

        <div className="min-h-0 flex-1 overflow-y-auto">
          {tab === "search" ? (
            <div className="space-y-4">
              <label className="block space-y-2">
                <span className="text-xs text-cyber-muted">Rechercher des photos…</span>
                <div className="flex gap-2">
                  <input
                    type="search"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    disabled={busy}
                    placeholder="Ex : boulangerie artisanale"
                    className="cyber-prompt-field min-h-0 flex-1 text-sm"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void handleSearch();
                    }}
                  />
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void handleSearch()}
                    className="cyber-generate-btn shrink-0 px-4 py-2 text-xs"
                  >
                    {busy ? "…" : "Chercher"}
                  </button>
                </div>
              </label>
              {searchResults.length > 0 ? (
                <div className="grid grid-cols-3 gap-3">
                  {searchResults.map((hit, idx) => {
                    const asset = savedAssets[idx];
                    const thumb = asset
                      ? getAssetPublicUrl(asset)
                      : hit.thumbnail || hit.url;
                    return (
                      <div
                        key={`${hit.url}-${idx}`}
                        className="overflow-hidden rounded-lg border border-white/10 bg-white/[0.03]"
                      >
                        <div className="aspect-[4/3] bg-black/30">
                          {thumb ? (
                            <img
                              src={thumb}
                              alt={hit.author || "Pexels"}
                              className="h-full w-full object-cover"
                            />
                          ) : null}
                        </div>
                        <div className="space-y-2 p-2">
                          {hit.author ? (
                            <p className="truncate text-[10px] text-white/45">{hit.author}</p>
                          ) : null}
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => void handleAddSearchResult(idx)}
                            className="w-full rounded-lg border border-[#d4a843]/40 bg-[#d4a843]/10 px-2 py-1.5 text-[11px] font-semibold text-[#d4a843] transition hover:bg-[#d4a843]/20"
                          >
                            Ajouter
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-xs text-cyber-muted">
                  Résultats Pexels affichés ici — recherche via l&apos;API backend.
                </p>
              )}
            </div>
          ) : null}

          {tab === "generate" ? (
            <div className="space-y-4">
              <label className="block space-y-2">
                <span className="text-xs text-cyber-muted">Prompt Replicate (Flux)</span>
                <textarea
                  value={generatePrompt}
                  onChange={(e) => setGeneratePrompt(e.target.value)}
                  rows={5}
                  disabled={busy}
                  placeholder="Ex : Photo professionnelle d'une boulangerie artisanale, lumière chaude"
                  className="cyber-prompt-field w-full text-sm"
                />
              </label>
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleGenerate()}
                className="cyber-generate-btn px-5 py-2.5 text-xs"
              >
                {busy ? "Génération en cours…" : "Générer l'image"}
              </button>
            </div>
          ) : null}

          {tab === "import" ? (
            <div
              className={`flex min-h-[180px] flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition ${
                importDrag
                  ? "border-cyber-neon bg-cyber-accent/10"
                  : "border-cyber-border bg-cyber-bg/40"
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setImportDrag(true);
              }}
              onDragLeave={() => setImportDrag(false)}
              onDrop={(e) => {
                e.preventDefault();
                setImportDrag(false);
                void handleFiles(e.dataTransfer.files);
              }}
            >
              <p className="text-sm text-cyber-muted">Glissez une image ici</p>
              <label className="cyber-action-btn cyber-action-btn-primary mt-3 cursor-pointer">
                Parcourir…
                <input
                  type="file"
                  className="sr-only"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  disabled={busy}
                  onChange={(e) => {
                    const files = e.target.files;
                    if (files?.length) void handleFiles(files);
                    e.target.value = "";
                  }}
                />
              </label>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

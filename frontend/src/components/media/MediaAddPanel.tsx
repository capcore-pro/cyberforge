import { useEffect, useState } from "react";
import { BackButton } from "@/components/BackButton";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  generateMediaImage,
  importMediaFromUrl,
  uploadMediaAsset,
  type MediaAsset,
} from "@/lib/media-api";
import { searchToolboxPhotos, type ToolboxPhoto } from "@/lib/toolbox-api";

type AddTab = "search" | "generate" | "import";

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
  initialTab = "search",
  projectId,
}: MediaAddPanelProps) {
  const [tab, setTab] = useState<AddTab>(initialTab);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [searchQuery, setSearchQuery] = useState("");
  const [photos, setPhotos] = useState<ToolboxPhoto[]>([]);
  const [photosLoading, setPhotosLoading] = useState(false);

  const [generatePrompt, setGeneratePrompt] = useState("");
  const [importDrag, setImportDrag] = useState(false);

  useEffect(() => {
    if (open) {
      setTab(initialTab);
      setError(null);
      setBusy(false);
    }
  }, [open, initialTab]);

  if (!open) return null;

  async function runPhotoSearch() {
    const q = searchQuery.trim();
    if (!q) {
      setError("Saisissez un mot-clé pour rechercher des photos.");
      return;
    }
    setPhotosLoading(true);
    setError(null);
    const res = await searchToolboxPhotos({ query: q, per_page: 20 });
    setPhotosLoading(false);
    if (!res.ok) {
      setError(
        apiErrorMessage(
          res,
          "Recherche impossible — vérifiez PEXELS_API_KEY et UNSPLASH_ACCESS_KEY.",
        ),
      );
      setPhotos([]);
      return;
    }
    const rows = res.data?.photos ?? [];
    if (!rows.length) {
      setError("Aucun résultat Pexels/Unsplash pour cette recherche.");
    }
    setPhotos(rows);
  }

  async function importPhoto(photo: ToolboxPhoto) {
    setBusy(true);
    setError(null);
    const res = await importMediaFromUrl({
      url: photo.url_full,
      filename: `photo-${photo.source}-${photo.id}.jpg`,
      tags: ["photo", photo.source, "pexels_unsplash"],
      project_id: projectId,
    });
    setBusy(false);
    if (!res.ok || !res.data) {
      setError(apiErrorMessage(res, "Import de la photo échoué."));
      return;
    }
    onAdded(res.data);
    onClose();
  }

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

  async function handleFiles(files: FileList | File[]) {
    const list = Array.from(files).filter((f) => f.type.startsWith("image/") || f.type === "application/pdf");
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
              <div className="flex gap-2">
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void runPhotoSearch();
                  }}
                  placeholder="Mot-clé (ex : boulangerie, restaurant…)"
                  className="cyber-prompt-field min-h-0 flex-1 text-sm"
                  disabled={busy || photosLoading}
                />
                <button
                  type="button"
                  disabled={busy || photosLoading}
                  onClick={() => void runPhotoSearch()}
                  className="cyber-action-btn cyber-action-btn-primary shrink-0 text-xs"
                >
                  {photosLoading ? "Recherche…" : "Rechercher"}
                </button>
              </div>
              <p className="text-xs text-cyber-muted">
                Sources : Pexels puis complément Unsplash si besoin.
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {photos.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    disabled={busy}
                    onClick={() => void importPhoto(p)}
                    className="group overflow-hidden rounded border border-cyber-border text-left transition hover:border-cyber-neon/50"
                  >
                    <img
                      src={p.url_thumb}
                      alt=""
                      className="aspect-[4/3] w-full object-cover"
                      loading="lazy"
                    />
                    <p className="truncate px-2 py-1 text-[10px] uppercase text-cyber-muted">
                      {p.source}
                      {p.author ? ` · ${p.author}` : ""}
                    </p>
                  </button>
                ))}
              </div>
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

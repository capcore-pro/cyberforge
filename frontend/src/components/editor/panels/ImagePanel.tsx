import { useCallback, useState } from "react";
import { Button } from "@/components/ui";
import { apiErrorMessage } from "@/lib/api-errors";
import { uploadImage } from "@/lib/editor-api";
import type { SelectedElementPayload } from "@/lib/editor-inject";
import { getAssetPublicUrl, searchMediaPhotos, type MediaAsset } from "@/lib/media-api";

interface ImagePanelProps {
  projectId: string;
  element: SelectedElementPayload;
  onReplace: (src: string, alt?: string) => void;
  logoMode?: boolean;
}

type Tab = "upload" | "pexels" | "url";

export function ImagePanel({ projectId, element, onReplace, logoMode }: ImagePanelProps) {
  const [tab, setTab] = useState<Tab>("upload");
  const [urlInput, setUrlInput] = useState(element.src ?? "");
  const [alt, setAlt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pexelsQuery, setPexelsQuery] = useState("");
  const [pexelsHits, setPexelsHits] = useState<MediaAsset[]>([]);

  const maxMb = logoMode ? 2 : 5;

  const handleFile = useCallback(
    async (file: File) => {
      if (file.size > maxMb * 1024 * 1024) {
        setError(`Taille max ${maxMb} Mo`);
        return;
      }
      setBusy(true);
      setError(null);
      const res = await uploadImage(projectId, file);
      setBusy(false);
      if (!res.ok || !res.data?.image_url) {
        setError(apiErrorMessage(res, "Upload impossible"));
        return;
      }
      onReplace(res.data.image_url, alt || undefined);
    },
    [alt, maxMb, onReplace, projectId],
  );

  async function searchPexels() {
    const q = pexelsQuery.trim();
    if (q.length < 2) return;
    setBusy(true);
    setError(null);
    const res = await searchMediaPhotos(q, 9);
    setBusy(false);
    if (!res.ok || !Array.isArray(res.data)) {
      setError(apiErrorMessage(res, "Recherche Pexels impossible"));
      return;
    }
    setPexelsHits(res.data.slice(0, 9));
  }

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium uppercase tracking-wider text-cf-label">
        {logoMode ? "Logo" : "Image"}
      </p>
      {element.src ? (
        <img
          src={element.src}
          alt=""
          className="max-h-28 w-full rounded border border-cf-border-input object-contain"
        />
      ) : null}
      <div className="flex gap-1 text-xs">
        {(["upload", "pexels", "url"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded px-2 py-1 capitalize ${tab === t ? "bg-cf-gold/20 text-cf-gold" : "text-cf-muted"}`}
          >
            {t === "upload" ? "Upload" : t === "pexels" ? "Pexels" : "URL"}
          </button>
        ))}
      </div>
      {tab === "upload" ? (
        <label className="flex cursor-pointer flex-col items-center justify-center rounded border border-dashed border-cf-border-input px-3 py-6 text-xs text-cf-muted hover:border-cf-gold/50">
          Glisser-déposer ou cliquer (max {maxMb} Mo)
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp,image/svg+xml"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void handleFile(f);
            }}
          />
        </label>
      ) : null}
      {tab === "pexels" ? (
        <div className="space-y-2">
          <div className="flex gap-2">
            <input
              value={pexelsQuery}
              onChange={(e) => setPexelsQuery(e.target.value)}
              placeholder="Rechercher…"
              className="flex-1 rounded border border-cf-border-input bg-cf-secondary px-2 py-1 text-xs"
            />
            <Button variant="ghost" size="sm" onClick={() => void searchPexels()} loading={busy}>
              OK
            </Button>
          </div>
          <div className="grid grid-cols-3 gap-1">
            {pexelsHits.map((hit) => (
              <button
                key={hit.id}
                type="button"
                className="aspect-square overflow-hidden rounded border border-cf-border-input hover:border-cf-gold"
                onClick={() => onReplace(getAssetPublicUrl(hit), alt || undefined)}
              >
                <img
                  src={getAssetPublicUrl(hit)}
                  alt=""
                  className="h-full w-full object-cover"
                />
              </button>
            ))}
          </div>
        </div>
      ) : null}
      {tab === "url" ? (
        <input
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          placeholder="https://…"
          className="w-full rounded border border-cf-border-input bg-cf-secondary px-2 py-1 text-xs"
        />
      ) : null}
      <input
        value={alt}
        onChange={(e) => setAlt(e.target.value)}
        placeholder="Texte alternatif (accessibilité)"
        className="w-full rounded border border-cf-border-input bg-cf-secondary px-2 py-1 text-xs"
      />
      {tab === "url" ? (
        <Button
          variant="primary"
          size="sm"
          onClick={() => onReplace(urlInput.trim(), alt || undefined)}
          disabled={!urlInput.trim()}
        >
          Remplacer
        </Button>
      ) : null}
      {error ? <p className="text-xs text-red-300">{error}</p> : null}
    </div>
  );
}

export function LogoPanel(props: ImagePanelProps) {
  return <ImagePanel {...props} logoMode />;
}

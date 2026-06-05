import { memo, useCallback, useMemo, useState } from "react";
import { LazyImage } from "@/components/LazyImage";
import { GLASS_PILL_BTN } from "@/components/accounting/accounting-theme";
import {
  formatBytes,
  getAssetPublicUrl,
  getAssetThumbnailUrl,
  providerLabel,
  type MediaAsset,
} from "@/lib/media-api";

function typeIcon(type: MediaAsset["type"]): string {
  if (type === "zip") return "📦";
  if (type === "pdf") return "📄";
  return "🖼️";
}

function sourceBadge(source: MediaAsset["source"]) {
  if (source === "upload") {
    return "border-sky-400/35 bg-sky-500/15 text-sky-300";
  }
  return "border-violet-400/35 bg-violet-500/15 text-violet-300";
}

export interface MediaAssetCardProps {
  asset: MediaAsset;
  onOpen?: (asset: MediaAsset) => void;
  onCopyUrl?: (asset: MediaAsset) => void;
  onDelete?: (asset: MediaAsset) => void;
  onSelect?: (asset: MediaAsset) => void;
  selectable?: boolean;
  busy?: boolean;
}

export const MediaAssetCard = memo(function MediaAssetCard({
  asset,
  onOpen,
  onCopyUrl,
  onDelete,
  onSelect,
  selectable = false,
  busy = false,
}: MediaAssetCardProps) {
  const [imgError, setImgError] = useState(false);
  const thumb = asset.type === "image" && !imgError ? getAssetThumbnailUrl(asset) : "";
  const provider = providerLabel(asset);

  const dateLabel = useMemo(
    () =>
      new Date(asset.created_at).toLocaleString("fr-FR", {
        dateStyle: "short",
        timeStyle: "short",
      }),
    [asset.created_at],
  );

  const handleCardClick = useCallback(() => {
    if (selectable && onSelect) {
      onSelect(asset);
      return;
    }
    if (onOpen) {
      onOpen(asset);
    }
  }, [asset, onOpen, onSelect, selectable]);

  return (
    <article
      className={`group relative flex flex-col overflow-hidden rounded-xl border border-white/10 bg-white/[0.03] transition-all hover:border-[#d4a843]/50 ${
        selectable || onOpen ? "cursor-pointer" : ""
      } ${busy ? "pointer-events-none opacity-60" : ""}`}
      onClick={handleCardClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleCardClick();
        }
      }}
      role={selectable || onOpen ? "button" : undefined}
      tabIndex={selectable || onOpen ? 0 : undefined}
    >
      <div className="relative aspect-[4/3] w-full bg-black/20">
        {asset.type === "image" && thumb ? (
          <LazyImage
            src={thumb}
            alt={asset.filename}
            className="h-full w-full"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-white/40">
            <span className="text-4xl" aria-hidden>
              {typeIcon(asset.type)}
            </span>
            <span className="text-[10px] uppercase tracking-wider">
              {asset.type}
            </span>
          </div>
        )}

        {!selectable && (onCopyUrl || onDelete) ? (
          <div className="absolute inset-0 flex items-center justify-center gap-2 bg-black/60 opacity-0 transition-opacity group-hover:opacity-100">
            {onCopyUrl ? (
              <button
                type="button"
                className={GLASS_PILL_BTN}
                onClick={(e) => {
                  e.stopPropagation();
                  onCopyUrl(asset);
                }}
              >
                Copier URL
              </button>
            ) : null}
            {onDelete ? (
              <button
                type="button"
                className={`${GLASS_PILL_BTN} border-red-400/30 text-red-300 hover:border-red-400/50`}
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(asset);
                }}
              >
                Supprimer
              </button>
            ) : null}
            {asset.type !== "image" ? (
              <a
                href={getAssetPublicUrl(asset)}
                download={asset.filename}
                className={GLASS_PILL_BTN}
                onClick={(e) => e.stopPropagation()}
              >
                Télécharger
              </a>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="flex flex-1 flex-col gap-2 p-3">
        <p className="truncate text-sm font-medium text-white" title={asset.filename}>
          {asset.filename}
        </p>
        <p className="text-[11px] text-white/45">
          {formatBytes(asset.size_bytes)} · {dateLabel}
        </p>
        <div className="flex flex-wrap gap-1">
          <span
            className={`rounded-full border px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${sourceBadge(asset.source)}`}
          >
            {asset.source === "upload" ? "Upload" : "Généré"}
          </span>
          <span className="rounded-full border border-white/10 bg-white/5 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-white/45">
            {provider}
          </span>
        </div>
        {asset.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {asset.tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[9px] text-white/45"
              >
                {tag}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );
});

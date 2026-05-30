import { useState } from "react";
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
    return "border-sky-500/50 bg-sky-500/15 text-sky-200";
  }
  return "border-violet-500/50 bg-violet-500/15 text-violet-200";
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

export function MediaAssetCard({
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

  const dateLabel = new Date(asset.created_at).toLocaleString("fr-FR", {
    dateStyle: "short",
    timeStyle: "short",
  });

  function handleCardClick() {
    if (selectable && onSelect) {
      onSelect(asset);
      return;
    }
    if (onOpen) {
      onOpen(asset);
    }
  }

  return (
    <article
      className={`group relative flex flex-col overflow-hidden rounded-lg border border-cyber-border bg-cyber-surface/90 transition ${
        selectable || onOpen ? "cursor-pointer hover:border-cyber-neon/60" : ""
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
      <div className="relative aspect-[4/3] w-full bg-cyber-bg/80">
        {asset.type === "image" && thumb ? (
          <img
            src={thumb}
            alt={asset.filename}
            className="h-full w-full object-cover"
            loading="lazy"
            decoding="async"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center gap-2 text-cyber-muted">
            <span className="text-4xl" aria-hidden>
              {typeIcon(asset.type)}
            </span>
            <span className="text-[10px] uppercase tracking-wider">
              {asset.type}
            </span>
          </div>
        )}

        {!selectable && (onCopyUrl || onDelete) ? (
          <div className="absolute inset-0 flex items-center justify-center gap-2 bg-black/70 opacity-0 transition group-hover:opacity-100">
            {onCopyUrl ? (
              <button
                type="button"
                className="cyber-action-btn text-[10px]"
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
                className="cyber-action-btn border-red-500/40 text-[10px] text-red-300"
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
                className="cyber-action-btn text-[10px]"
                onClick={(e) => e.stopPropagation()}
              >
                Télécharger
              </a>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="flex flex-1 flex-col gap-2 p-3">
        <p className="truncate text-sm font-medium text-cyber-text" title={asset.filename}>
          {asset.filename}
        </p>
        <p className="text-[11px] text-cyber-muted">
          {formatBytes(asset.size_bytes)} · {dateLabel}
        </p>
        <div className="flex flex-wrap gap-1">
          <span
            className={`rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${sourceBadge(asset.source)}`}
          >
            {asset.source === "upload" ? "Upload" : "Généré"}
          </span>
          <span className="rounded border border-cyber-border bg-cyber-bg/50 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-cyber-muted">
            {provider}
          </span>
        </div>
        {asset.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {asset.tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-cyber-border/80 bg-cyber-bg/50 px-2 py-0.5 text-[9px] text-cyber-muted"
              >
                {tag}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </article>
  );
}

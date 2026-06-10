import { useEffect, useRef, useState } from "react";
import {
  prepareInternalPreviewSrcDoc,
  withCyberforgeInternalPreview,
} from "@/lib/cyberforge-preview";

const PREVIEW_IFRAME_SANDBOX =
  "allow-scripts allow-same-origin allow-forms allow-modals";

interface ProjectPreviewThumbnailProps {
  html?: string | null;
  /** URL externe (ex. démo Cloudflare) — distinct du srcDoc HTML local. */
  previewUrl?: string | null;
  title: string;
  width?: number;
  height?: number;
  /** Occupe toute la largeur du parent (cartes projet). */
  fill?: boolean;
  className?: string;
}

/** Dimensions visibles par défaut (px). */
const DEFAULT_THUMB_W = 280;
const DEFAULT_THUMB_H = 160;
const SCALE = 0.25;

function ThumbnailPlaceholder({
  title,
  width,
  height,
  className,
  message,
  fill,
}: {
  title: string;
  width: number;
  height: number;
  className: string;
  message?: string;
  fill?: boolean;
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-lg border border-cyber-border bg-zinc-800/90 text-center ${fill ? "w-full" : ""} ${className}`}
      style={fill ? { height, maxWidth: "100%" } : { width, height, maxWidth: "100%" }}
      aria-hidden
    >
      <p className="line-clamp-3 px-3 text-xs font-medium text-zinc-200">{title}</p>
      {message ? (
        <p className="mt-1 px-3 text-[10px] text-cyber-muted">{message}</p>
      ) : null}
    </div>
  );
}

/**
 * Miniature d'aperçu — iframe srcdoc ou URL externe réduite (scale 0.25).
 * En cas d'échec de chargement, affiche un placeholder gris avec le nom du projet.
 */
export function ProjectPreviewThumbnail({
  html,
  previewUrl,
  title,
  width = DEFAULT_THUMB_W,
  height = DEFAULT_THUMB_H,
  fill = false,
  className = "",
}: ProjectPreviewThumbnailProps) {
  const [loadFailed, setLoadFailed] = useState(false);
  const loadTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const srcDoc = html?.trim() ? prepareInternalPreviewSrcDoc(html) : null;
  const externalUrl = previewUrl?.trim()
    ? withCyberforgeInternalPreview(previewUrl.trim())
    : null;

  useEffect(() => {
    setLoadFailed(false);
    if (loadTimeoutRef.current) {
      clearTimeout(loadTimeoutRef.current);
      loadTimeoutRef.current = null;
    }
    if (!srcDoc && !externalUrl) return;
    loadTimeoutRef.current = setTimeout(() => setLoadFailed(true), 12_000);
    return () => {
      if (loadTimeoutRef.current) {
        clearTimeout(loadTimeoutRef.current);
        loadTimeoutRef.current = null;
      }
    };
  }, [srcDoc, externalUrl]);

  function handleIframeLoad() {
    if (loadTimeoutRef.current) {
      clearTimeout(loadTimeoutRef.current);
      loadTimeoutRef.current = null;
    }
  }

  const frameStyle = fill
    ? {
        width: "200%",
        height: height * 2,
        transform: "scale(0.5)",
        transformOrigin: "top left",
      }
    : {
        width: Math.round(width / SCALE),
        height: Math.round(height / SCALE),
        transform: `scale(${SCALE})`,
        transformOrigin: "top left",
      };

  const containerStyle = fill
    ? { width: "100%", height, maxWidth: "100%" }
    : { width, height, maxWidth: "100%" };

  if (!srcDoc && !externalUrl) {
    return (
      <ThumbnailPlaceholder
        title={title}
        width={width}
        height={height}
        fill={fill}
        className={className}
        message="Aperçu non disponible"
      />
    );
  }

  if (loadFailed) {
    return (
      <ThumbnailPlaceholder
        title={title}
        width={width}
        height={height}
        fill={fill}
        className={className}
        message="Aperçu indisponible"
      />
    );
  }

  return (
    <div
      className={`relative overflow-hidden rounded-lg border border-cyber-border bg-[#0a0a0f] ${fill ? "w-full" : ""} ${className}`}
      style={containerStyle}
    >
      <iframe
        title={`Aperçu ${title}`}
        className="pointer-events-none absolute left-0 top-0 border-0"
        style={frameStyle}
        sandbox={PREVIEW_IFRAME_SANDBOX}
        src={externalUrl ?? undefined}
        srcDoc={externalUrl ? undefined : srcDoc ?? undefined}
        loading="lazy"
        onLoad={handleIframeLoad}
        onError={() => setLoadFailed(true)}
      />
    </div>
  );
}

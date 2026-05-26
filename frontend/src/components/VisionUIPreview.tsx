import type { VisionPreviewSource } from "@shared/types";

interface VisionUIPreviewProps {
  screenshotUrl: string | null;
  previewSource: VisionPreviewSource | null;
  html: string | null;
  message?: string;
  compact?: boolean;
}

/**
 * Aperçu VisionUI — screenshot Replicate ou iframe HTML local (fallback).
 */
export function VisionUIPreview({
  screenshotUrl,
  previewSource,
  html,
  message,
  compact = false,
}: VisionUIPreviewProps) {
  const showIframe =
    previewSource === "local" && Boolean(html && html.trim().length > 0);
  const showImage =
    Boolean(screenshotUrl) &&
    !showIframe &&
    (previewSource === "replicate" ||
      (screenshotUrl?.startsWith("http") ?? false));

  if (!showIframe && !showImage) {
    return null;
  }

  return (
    <section
      className={`cyber-panel overflow-hidden border-cyber-violet/40 ${
        compact ? "p-3" : "p-4"
      }`}
      aria-label="Aperçu VisionUI"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-cyber-violet">
          VisionUI
        </h3>
        <span className="rounded border border-cyber-accent/30 bg-cyber-accent/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-cyber-neon">
          {previewSource === "replicate" ? "Screenshot Replicate" : "HTML local"}
        </span>
      </div>
      {message ? (
        <p className="mb-3 text-xs text-cyber-muted">{message}</p>
      ) : null}
      {showImage && screenshotUrl ? (
        <div className="overflow-hidden rounded-md border border-cyber-border bg-cyber-bg/80">
          <img
            src={screenshotUrl}
            alt="Capture VisionUI du livrable généré"
            className="max-h-[min(70vh,520px)] w-full object-contain object-top"
          />
        </div>
      ) : null}
      {showIframe ? (
        <div className="overflow-hidden rounded-md border border-cyber-border bg-white">
          <iframe
            title="Aperçu HTML VisionUI"
            srcDoc={html}
            sandbox="allow-scripts allow-same-origin"
            className="h-[min(70vh,520px)] w-full bg-white"
          />
        </div>
      ) : null}
      <p className="mt-2 text-[10px] text-cyber-muted">
        Aperçu affiché avant la validation BugHunterAI.
      </p>
    </section>
  );
}

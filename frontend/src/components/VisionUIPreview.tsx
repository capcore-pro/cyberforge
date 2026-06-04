import type { VisionPreviewSource } from "@shared/types";
import { CyberForgePreviewFrame } from "@/components/PreviewFullscreenActions";
import {
  isUsablePreviewHtml,
  prepareInternalPreviewSrcDoc,
} from "@/lib/cyberforge-preview";

interface VisionUIPreviewProps {
  screenshotUrl: string | null;
  previewSource: VisionPreviewSource | null;
  html: string | null;
  message?: string;
  compact?: boolean;
  /** Aperçu popup Chrome 380×500 (extension_navigateur). */
  extensionPopup?: boolean;
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
  extensionPopup = false,
}: VisionUIPreviewProps) {
  const previewDoc = html ? prepareInternalPreviewSrcDoc(html) : "";
  const showIframe = isUsablePreviewHtml(previewDoc);
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
          {extensionPopup ? "Popup extension" : "VisionUI"}
        </h3>
        <span className="rounded border border-cyber-accent/30 bg-cyber-accent/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-cyber-neon">
          {extensionPopup
            ? "380×500"
            : previewSource === "replicate"
              ? "Screenshot Replicate"
              : "HTML local"}
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
        <CyberForgePreviewFrame
          srcDoc={previewDoc}
          rawHtml={html}
          title={
            extensionPopup ? "Aperçu popup extension Chrome" : "Aperçu HTML VisionUI"
          }
          wrapperClassName={
            extensionPopup
              ? "flex justify-center rounded-md border border-cyber-border bg-slate-900/40 p-4"
              : "overflow-hidden rounded-md border border-cyber-border bg-white"
          }
          iframeClassName={
            extensionPopup
              ? "h-[500px] w-[380px] max-w-full shrink-0 rounded-lg border border-slate-700 bg-white shadow-lg"
              : "h-[min(70vh,520px)] w-full bg-white"
          }
        />
      ) : null}
      <p className="mt-2 text-[10px] text-cyber-muted">
        {extensionPopup
          ? "Aperçu de la popup Chrome (pas une page pleine largeur)."
          : "Aperçu affiché avant la validation BugHunterAI."}
      </p>
    </section>
  );
}

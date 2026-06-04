import {
  GENERATOR_PREVIEW_IFRAME_H,
  GENERATOR_PREVIEW_IFRAME_W,
  GENERATOR_PREVIEW_SCALE,
  PreviewFullscreenHost,
} from "@/components/PreviewFullscreenActions";
import { prepareInternalPreviewSrcDoc } from "@/lib/cyberforge-preview";

interface GeneratorPreviewModalProps {
  html: string;
  onClose: () => void;
}

const VIEWPORT_W = Math.round(GENERATOR_PREVIEW_IFRAME_W * GENERATOR_PREVIEW_SCALE);
const VIEWPORT_H = Math.round(GENERATOR_PREVIEW_IFRAME_H * GENERATOR_PREVIEW_SCALE);

/** Prévisualisation inline (navigateur ou repli Electron). */
export function GeneratorPreviewModal({
  html,
  onClose,
}: GeneratorPreviewModalProps) {
  const previewDoc = prepareInternalPreviewSrcDoc(html);
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Prévisualisation du code généré"
    >
      <div className="flex max-h-[95vh] w-full max-w-[min(96vw,920px)] flex-col overflow-hidden rounded-card border border-cf-border-input bg-cf-card shadow-card">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cyber-border px-4 py-3">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-cyber-neon">
              Aperçu visuel
            </h2>
            <p className="text-[10px] text-cyber-muted">
              Desktop simulé {GENERATOR_PREVIEW_IFRAME_W}×{GENERATOR_PREVIEW_IFRAME_H}px (×
              {GENERATOR_PREVIEW_SCALE})
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-cyber-border px-3 py-1 text-xs text-cyber-muted hover:border-cyber-violet hover:text-cyber-text"
          >
            Fermer
          </button>
        </div>
        <PreviewFullscreenHost
          html={html}
          fullscreenMode="fixed"
          className="flex min-h-0 flex-1 flex-col px-4 pb-4"
        >
          <div
            className="mx-auto flex min-h-0 flex-1 items-start justify-center overflow-auto rounded-md border border-cyber-border bg-[#0a0a0f] py-3"
            style={{ minWidth: VIEWPORT_W, minHeight: VIEWPORT_H }}
          >
            <div
              className="relative shrink-0 overflow-hidden"
              style={{ width: VIEWPORT_W, height: VIEWPORT_H }}
            >
              <iframe
                title="Prévisualisation CyberForge"
                className="absolute left-0 top-0 border-0 bg-white"
                style={{
                  width: GENERATOR_PREVIEW_IFRAME_W,
                  height: GENERATOR_PREVIEW_IFRAME_H,
                  transform: `scale(${GENERATOR_PREVIEW_SCALE})`,
                  transformOrigin: "top left",
                }}
                sandbox="allow-scripts allow-same-origin allow-forms"
                srcDoc={previewDoc}
              />
            </div>
          </div>
        </PreviewFullscreenHost>
      </div>
    </div>
  );
}

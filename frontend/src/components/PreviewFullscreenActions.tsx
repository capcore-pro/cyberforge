import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { prepareInternalPreviewSrcDoc } from "@/lib/cyberforge-preview";
import { openProjectUrl } from "@/lib/unified-projects";

export type PreviewFullscreenMode = "native" | "fixed";

interface PreviewFullscreenToolbarProps {
  html?: string | null;
  externalUrl?: string | null;
  fullscreenTargetRef: React.RefObject<HTMLElement | null>;
  className?: string;
  /** fixed = iframe 100vw×100vh en overlay (z-index 9999), sans limite du conteneur parent */
  fullscreenMode?: PreviewFullscreenMode;
}

/** Barre d'actions Plein écran / nouvel onglet pour les aperçus iframe. */
export function PreviewFullscreenToolbar({
  html,
  externalUrl,
  fullscreenTargetRef,
  className = "",
  fullscreenMode = "fixed",
}: PreviewFullscreenToolbarProps) {
  const [fixedOverlayOpen, setFixedOverlayOpen] = useState(false);
  const previewDoc = html?.trim() ? prepareInternalPreviewSrcDoc(html) : "";
  const useFixedOverlay = fullscreenMode === "fixed" && Boolean(previewDoc);

  useEffect(() => {
    if (!fixedOverlayOpen || !useFixedOverlay) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [fixedOverlayOpen, useFixedOverlay]);

  const openInNewTab = useCallback(() => {
    const url = externalUrl?.trim();
    if (url) {
      openProjectUrl(url);
      return;
    }
    const doc = html?.trim();
    if (!doc) return;
    const blob = new Blob([prepareInternalPreviewSrcDoc(doc)], {
      type: "text/html;charset=utf-8",
    });
    const objectUrl = URL.createObjectURL(blob);
    window.open(objectUrl, "_blank", "noopener,noreferrer");
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
  }, [externalUrl, html]);

  const toggleFullscreen = useCallback(async () => {
    if (useFixedOverlay) {
      setFixedOverlayOpen((open) => !open);
      return;
    }
    const el = fullscreenTargetRef.current;
    if (!el) {
      openInNewTab();
      return;
    }
    try {
      if (document.fullscreenElement === el) {
        await document.exitFullscreen();
      } else {
        await el.requestFullscreen();
      }
    } catch {
      openInNewTab();
    }
  }, [useFixedOverlay, fullscreenTargetRef, openInNewTab]);

  const canOpenTab = Boolean(externalUrl?.trim() || html?.trim());

  const fixedOverlay =
    fixedOverlayOpen && useFixedOverlay
      ? createPortal(
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Aperçu plein écran"
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              width: "100vw",
              height: "100vh",
              zIndex: 9999,
              margin: 0,
              padding: 0,
              overflow: "hidden",
              boxSizing: "border-box",
              background: "#000",
            }}
          >
            <iframe
              title="Aperçu plein écran"
              srcDoc={previewDoc}
              sandbox="allow-scripts allow-same-origin allow-forms allow-modals"
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100vw",
                height: "100vh",
                border: "none",
                display: "block",
              }}
            />
            <button
              type="button"
              onClick={() => setFixedOverlayOpen(false)}
              style={{
                position: "absolute",
                top: 16,
                right: 16,
                zIndex: 10000,
              }}
              className="rounded border border-cyber-border bg-cf-card/95 px-3 py-1.5 text-xs text-cyber-text shadow-lg hover:border-cyber-violet"
            >
              Fermer
            </button>
          </div>,
          document.body,
        )
      : null;

  return (
    <>
      <div className={`flex flex-wrap items-center gap-2 ${className}`}>
        <button
          type="button"
          onClick={() => void toggleFullscreen()}
          className="rounded border border-cyber-border px-2.5 py-1 text-[10px] text-cyber-muted hover:border-cyber-violet hover:text-cyber-text"
        >
          Plein écran
        </button>
        <button
          type="button"
          onClick={openInNewTab}
          disabled={!canOpenTab}
          className="rounded border border-cyber-border px-2.5 py-1 text-[10px] text-cyber-muted hover:border-cyber-violet hover:text-cyber-text disabled:opacity-40"
        >
          Ouvrir dans un onglet
        </button>
      </div>
      {fixedOverlay}
    </>
  );
}

interface CyberForgePreviewFrameProps {
  srcDoc: string;
  title: string;
  externalUrl?: string | null;
  rawHtml?: string | null;
  iframeClassName?: string;
  wrapperClassName?: string;
  toolbarClassName?: string;
}

/** Iframe d'aperçu avec barre Plein écran / nouvel onglet. */
export function CyberForgePreviewFrame({
  srcDoc,
  title,
  externalUrl,
  rawHtml,
  iframeClassName = "h-[min(70vh,520px)] w-full bg-white",
  wrapperClassName = "overflow-hidden rounded-md border border-cyber-border bg-white",
  toolbarClassName = "mb-2",
}: CyberForgePreviewFrameProps) {
  const hostRef = useRef<HTMLDivElement>(null);

  return (
    <div>
      <PreviewFullscreenToolbar
        html={rawHtml ?? srcDoc}
        externalUrl={externalUrl}
        fullscreenTargetRef={hostRef}
        fullscreenMode={(rawHtml ?? srcDoc) ? "fixed" : "native"}
        className={toolbarClassName}
      />
      <div ref={hostRef} className={wrapperClassName}>
        <iframe
          title={title}
          srcDoc={srcDoc}
          sandbox="allow-scripts allow-same-origin allow-forms allow-modals"
          className={iframeClassName}
        />
      </div>
    </div>
  );
}

/** Enveloppe optionnelle autour d'un aperçu existant (toolbar seule). */
export function PreviewFullscreenHost({
  children,
  html,
  externalUrl,
  className = "",
  fullscreenMode = "fixed",
}: {
  children: ReactNode;
  html?: string | null;
  externalUrl?: string | null;
  className?: string;
  fullscreenMode?: PreviewFullscreenMode;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  return (
    <div className={className}>
      <PreviewFullscreenToolbar
        html={html}
        externalUrl={externalUrl}
        fullscreenTargetRef={hostRef}
        fullscreenMode={fullscreenMode}
        className="mb-2"
      />
      <div ref={hostRef} className="min-h-0 flex-1">
        {children}
      </div>
    </div>
  );
}

/** Dimensions iframe « desktop » + scale pour l’aperçu dans la modal. */
export const GENERATOR_PREVIEW_IFRAME_W = 1280;
export const GENERATOR_PREVIEW_IFRAME_H = 720;
export const GENERATOR_PREVIEW_SCALE = 0.6;

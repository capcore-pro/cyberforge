import { useCallback, useRef, type ReactNode } from "react";
import { prepareInternalPreviewSrcDoc } from "@/lib/cyberforge-preview";
import { openProjectUrl } from "@/lib/unified-projects";

interface PreviewFullscreenToolbarProps {
  html?: string | null;
  externalUrl?: string | null;
  fullscreenTargetRef: React.RefObject<HTMLElement | null>;
  className?: string;
}

/** Barre d'actions Plein écran / nouvel onglet pour les aperçus iframe. */
export function PreviewFullscreenToolbar({
  html,
  externalUrl,
  fullscreenTargetRef,
  className = "",
}: PreviewFullscreenToolbarProps) {
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
  }, [fullscreenTargetRef, openInNewTab]);

  const canOpenTab = Boolean(externalUrl?.trim() || html?.trim());

  return (
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
        className={toolbarClassName}
      />
      <div ref={hostRef} className={wrapperClassName}>
        <iframe
          title={title}
          srcDoc={srcDoc}
          sandbox="allow-scripts allow-same-origin allow-forms"
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
}: {
  children: ReactNode;
  html?: string | null;
  externalUrl?: string | null;
  className?: string;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  return (
    <div className={className}>
      <PreviewFullscreenToolbar
        html={html}
        externalUrl={externalUrl}
        fullscreenTargetRef={hostRef}
        className="mb-2"
      />
      <div ref={hostRef} className="min-h-0 flex-1">
        {children}
      </div>
    </div>
  );
}

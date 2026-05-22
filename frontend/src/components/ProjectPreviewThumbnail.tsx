interface ProjectPreviewThumbnailProps {
  html: string | null;
  title: string;
}

/** Dimensions visibles de la miniature (px). */
const THUMB_W = 280;
const THUMB_H = 160;
const SCALE = 0.25;
const IFRAME_W = Math.round(THUMB_W / SCALE);
const IFRAME_H = Math.round(THUMB_H / SCALE);

/**
 * Miniature d'aperçu — iframe srcdoc réduit (scale 0.25, cadre 280×160).
 */
export function ProjectPreviewThumbnail({
  html,
  title,
}: ProjectPreviewThumbnailProps) {
  if (!html?.trim()) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-cyber-border bg-cyber-bg/80 text-center"
        style={{ width: THUMB_W, height: THUMB_H, maxWidth: "100%" }}
        aria-hidden
      >
        <p className="px-3 text-[10px] text-cyber-muted">Aperçu non disponible</p>
      </div>
    );
  }

  return (
    <div
      className="relative overflow-hidden rounded-lg border border-cyber-border bg-[#0a0a0f]"
      style={{ width: THUMB_W, height: THUMB_H, maxWidth: "100%" }}
    >
      <iframe
        title={`Aperçu ${title}`}
        className="pointer-events-none absolute left-0 top-0 border-0"
        style={{
          width: IFRAME_W,
          height: IFRAME_H,
          transform: `scale(${SCALE})`,
          transformOrigin: "top left",
        }}
        sandbox="allow-scripts"
        srcDoc={html}
      />
    </div>
  );
}

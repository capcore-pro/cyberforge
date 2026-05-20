interface ProjectPreviewThumbnailProps {
  html: string | null;
  title: string;
}

/**
 * Miniature d'aperçu — iframe srcdoc (HTML statique, sans réseau externe).
 */
export function ProjectPreviewThumbnail({
  html,
  title,
}: ProjectPreviewThumbnailProps) {
  if (!html?.trim()) {
    return (
      <div
        className="flex h-full min-h-[140px] items-center justify-center rounded-lg border border-dashed border-cyber-border bg-cyber-bg/80 p-4 text-center"
        aria-hidden
      >
        <p className="text-[10px] text-cyber-muted">Aperçu non disponible</p>
      </div>
    );
  }

  return (
    <div className="relative h-[140px] overflow-hidden rounded-lg border border-cyber-border bg-[#0a0a0f]">
      <iframe
        title={`Aperçu ${title}`}
        className="pointer-events-none absolute left-0 top-0 h-[560px] w-[800px] origin-top-left scale-[0.25] border-0"
        sandbox=""
        srcDoc={html}
      />
    </div>
  );
}

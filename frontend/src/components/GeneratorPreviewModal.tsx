interface GeneratorPreviewModalProps {
  html: string;
  onClose: () => void;
}

/** Prévisualisation inline (navigateur ou repli Electron). */
export function GeneratorPreviewModal({
  html,
  onClose,
}: GeneratorPreviewModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Prévisualisation du code généré"
    >
      <div className="flex h-[min(90vh,720px)] w-full max-w-5xl flex-col overflow-hidden rounded-lg border border-cyber-accent/40 bg-cyber-surface shadow-neonCyan">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cyber-border px-4 py-3">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-cyber-neon">
              Aperçu visuel
            </h2>
            <p className="text-[10px] text-cyber-muted">
              Maquette HTML simplifiée (titre, sections, couleurs)
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
        <iframe
          title="Prévisualisation CyberForge"
          className="min-h-0 flex-1 bg-[#0a0a0f]"
          sandbox="allow-same-origin"
          srcDoc={html}
        />
      </div>
    </div>
  );
}

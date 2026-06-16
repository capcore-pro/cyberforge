import type { SelectedElementPayload } from "@/lib/editor-inject";

interface DefaultPanelProps {
  onHint?: () => void;
}

export function DefaultPanel({ onHint }: DefaultPanelProps) {
  return (
    <div className="space-y-4 text-sm text-cf-muted">
      <p className="text-cf-text">
        👆 Cliquez sur n&apos;importe quel élément du site pour le modifier
      </p>
      <ul className="space-y-2 text-xs">
        <li>✏️ Textes — titres, paragraphes, boutons</li>
        <li>🖼️ Images — upload, Pexels ou URL</li>
        <li>🎨 Couleurs — texte et thème global</li>
        <li>📐 Sections — réordonner, dupliquer, masquer</li>
      </ul>
      <p className="text-[11px] text-cf-label">
        Raccourcis : Ctrl+Z annuler · Ctrl+S sauvegarder
      </p>
      {onHint ? (
        <button
          type="button"
          onClick={onHint}
          className="text-xs text-cf-gold hover:underline"
        >
          Recharger l&apos;aperçu
        </button>
      ) : null}
    </div>
  );
}

export type { SelectedElementPayload };

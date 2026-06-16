import { useState } from "react";
import { Button } from "@/components/ui";
import type { SelectedElementPayload } from "@/lib/editor-inject";

interface SectionPanelProps {
  element: SelectedElementPayload;
  onMove: (direction: "up" | "down") => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onToggleVisibility: (hidden: boolean) => void;
}

export function SectionPanel({
  element,
  onMove,
  onDuplicate,
  onDelete,
  onToggleVisibility,
}: SectionPanelProps) {
  const [hidden, setHidden] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium uppercase tracking-wider text-cf-label">Section</p>
      <p className="text-[11px] text-cf-muted">
        &lt;{element.tagName.toLowerCase()}&gt;
      </p>
      <div className="flex flex-wrap gap-2">
        <Button variant="ghost" size="sm" onClick={() => onMove("up")}>
          ↑ Monter
        </Button>
        <Button variant="ghost" size="sm" onClick={() => onMove("down")}>
          ↓ Descendre
        </Button>
        <Button variant="ghost" size="sm" onClick={onDuplicate}>
          Dupliquer
        </Button>
      </div>
      <label className="flex items-center gap-2 text-xs text-cf-text">
        <input
          type="checkbox"
          checked={hidden}
          onChange={(e) => {
            setHidden(e.target.checked);
            onToggleVisibility(e.target.checked);
          }}
        />
        Masquer la section
      </label>
      {!confirmDelete ? (
        <Button variant="danger" size="sm" onClick={() => setConfirmDelete(true)}>
          Supprimer
        </Button>
      ) : (
        <div className="flex gap-2">
          <Button variant="danger" size="sm" onClick={onDelete}>
            Confirmer
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setConfirmDelete(false)}>
            Annuler
          </Button>
        </div>
      )}
    </div>
  );
}

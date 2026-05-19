interface CodeOutputActionsProps {
  onPreview: () => void;
  onCopy: () => void;
  onExportZip: () => void;
  copyLabel?: string;
  disabled?: boolean;
}

/** Actions sur le code généré : prévisualiser, copier, exporter. */
export function CodeOutputActions({
  onPreview,
  onCopy,
  onExportZip,
  copyLabel = "Copier le code",
  disabled = false,
}: CodeOutputActionsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        type="button"
        disabled={disabled}
        onClick={onPreview}
        className="cyber-action-btn cyber-action-btn-primary"
      >
        Prévisualiser
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={onCopy}
        className="cyber-action-btn"
      >
        {copyLabel}
      </button>
      <button
        type="button"
        disabled={disabled}
        onClick={onExportZip}
        className="cyber-action-btn"
      >
        Export ZIP
      </button>
    </div>
  );
}

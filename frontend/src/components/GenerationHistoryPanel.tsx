import type { GenerationHistoryEntry } from "@/lib/generation-history";
import { formatHistoryDate } from "@/lib/generation-history";
import { PROJECT_TYPE_OPTIONS } from "@/lib/project-types";

interface GenerationHistoryPanelProps {
  entries: GenerationHistoryEntry[];
  onRestore: (entry: GenerationHistoryEntry) => void;
  onRemove: (id: string) => void;
  onClear: () => void;
}

/** Historique local des générations (localStorage). */
export function GenerationHistoryPanel({
  entries,
  onRestore,
  onRemove,
  onClear,
}: GenerationHistoryPanelProps) {
  if (entries.length === 0) {
    return (
      <section className="cyber-panel p-5">
        <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-cyber-violet">
          Historique
        </h2>
        <p className="mt-2 text-xs text-cyber-muted">
          Les générations réussies sont enregistrées automatiquement sur cet appareil.
        </p>
      </section>
    );
  }

  return (
    <section className="cyber-panel space-y-3 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-cyber-violet">
          Historique ({entries.length})
        </h2>
        <button
          type="button"
          onClick={onClear}
          className="text-[10px] uppercase tracking-wider text-cyber-muted hover:text-red-400"
        >
          Tout effacer
        </button>
      </div>

      <ul className="max-h-64 space-y-2 overflow-y-auto pr-1">
        {entries.map((entry) => {
          const typeLabel =
            PROJECT_TYPE_OPTIONS.find((o) => o.id === entry.projectType)?.label ??
            entry.projectType;

          return (
            <li
              key={entry.id}
              className="rounded-lg border border-cyber-border bg-cyber-bg/60 p-3"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-cyber-text">
                    {entry.prompt}
                  </p>
                  <p className="mt-1 text-[10px] text-cyber-muted">
                    {formatHistoryDate(entry.createdAt)} · {typeLabel} ·{" "}
                    {entry.result.metrics.model}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button
                    type="button"
                    onClick={() => onRestore(entry)}
                    className="cyber-action-btn cyber-action-btn-primary"
                  >
                    Restaurer
                  </button>
                  <button
                    type="button"
                    onClick={() => onRemove(entry.id)}
                    className="cyber-action-btn"
                    aria-label="Supprimer"
                  >
                    ×
                  </button>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

import { useRef } from "react";
import { prepareInternalPreviewSrcDoc } from "@/lib/cyberforge-preview";
import {
  CUSTOMIZATION_TITLE_MAX,
  cloneCustomization,
  deriveInitials,
  readImageFileAsDataUrl,
  statsFromTasks,
  type DemoCustomization,
  type DemoTaskItem,
} from "@/lib/demo-customization";

interface CustomizePanelProps {
  value: DemoCustomization;
  onChange: (next: DemoCustomization) => void;
  previewHtml: string | null;
  previewLoading?: boolean;
  onSave: () => void;
  onReset: () => void;
  onOpenFullPreview?: () => void;
  saveBusy?: boolean;
}

function SectionTitle({ children }: { children: string }) {
  return (
    <h3 className="text-[10px] font-bold uppercase tracking-[0.18em] text-cyber-violet">
      {children}
    </h3>
  );
}

/** Panneau de personnalisation client — aperçu live à droite. */
export function CustomizePanel({
  value,
  onChange,
  previewHtml,
  previewLoading = false,
  onSave,
  onReset,
  onOpenFullPreview,
  saveBusy = false,
}: CustomizePanelProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const initials = deriveInitials(value.user_name);

  function patch(partial: Partial<DemoCustomization>) {
    onChange({ ...value, ...partial });
  }

  function updateTasks(next: DemoTaskItem[]) {
    const stats = value.stats;
    const autoStats = statsFromTasks(next);
    onChange({
      ...value,
      tasks: next,
      stats:
        stats.total === statsFromTasks(value.tasks).total &&
        stats.active === statsFromTasks(value.tasks).active &&
        stats.done === statsFromTasks(value.tasks).done
          ? autoStats
          : stats,
    });
  }

  function updateStat(key: keyof DemoCustomization["stats"], raw: string) {
    const num = Math.max(0, parseInt(raw, 10) || 0);
    patch({ stats: { ...value.stats, [key]: num } });
  }

  return (
    <section className="cyber-panel space-y-4 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-cyber-violet">
            Personnaliser
          </h2>
          <p className="mt-1 text-[10px] text-cyber-muted">
            Prévisualisation fidèle pour le client — modifications en direct à
            droite.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onReset}
            className="rounded-md border border-cyber-border px-3 py-1.5 text-[10px] uppercase tracking-wider text-cyber-muted hover:border-cyber-violet hover:text-cyber-text"
          >
            Réinitialiser
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={saveBusy}
            className="cyber-action-btn cyber-action-btn-primary text-[10px]"
          >
            {saveBusy ? "Sauvegarde…" : "Sauvegarder"}
          </button>
          {onOpenFullPreview ? (
            <button
              type="button"
              onClick={onOpenFullPreview}
              disabled={!previewHtml}
              className="cyber-action-btn text-[10px]"
            >
              Aperçu plein écran
            </button>
          ) : null}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,42%)]">
        <div className="max-h-[70vh] space-y-5 overflow-y-auto pr-1">
          <div className="space-y-3">
            <SectionTitle>Identité</SectionTitle>
            <label className="block text-[10px] uppercase tracking-wider text-cyber-muted">
              Titre de l&apos;application
              <span className="float-right font-mono normal-case text-cyber-violet">
                {value.title.length}/{CUSTOMIZATION_TITLE_MAX}
              </span>
              <input
                type="text"
                value={value.title}
                maxLength={CUSTOMIZATION_TITLE_MAX}
                onChange={(e) => patch({ title: e.target.value })}
                className="mt-1 w-full rounded border border-cyber-border bg-cyber-bg px-3 py-2 text-sm text-cyber-text"
              />
            </label>
            <label className="block text-[10px] uppercase tracking-wider text-cyber-muted">
              Sous-titre / accroche
              <input
                type="text"
                value={value.subtitle}
                maxLength={140}
                onChange={(e) => patch({ subtitle: e.target.value })}
                className="mt-1 w-full rounded border border-cyber-border bg-cyber-bg px-3 py-2 text-sm text-cyber-text"
              />
            </label>
            <label className="block text-[10px] uppercase tracking-wider text-cyber-muted">
              Nom de l&apos;entreprise cliente
              <input
                type="text"
                value={value.brand_name}
                maxLength={40}
                onChange={(e) => patch({ brand_name: e.target.value })}
                className="mt-1 w-full rounded border border-cyber-border bg-cyber-bg px-3 py-2 text-sm text-cyber-text"
              />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="flex flex-col gap-2 text-[10px] uppercase tracking-wider text-cyber-muted">
                Couleur principale
                <span className="flex items-center gap-2 normal-case">
                  <input
                    type="color"
                    value={value.primary_color}
                    onChange={(e) => patch({ primary_color: e.target.value })}
                    className="h-10 w-14 cursor-pointer rounded border border-cyber-border bg-transparent"
                  />
                  <span className="font-mono text-xs text-cyber-text">
                    {value.primary_color}
                  </span>
                </span>
              </label>
              <label className="flex flex-col gap-2 text-[10px] uppercase tracking-wider text-cyber-muted">
                Couleur secondaire
                <span className="flex items-center gap-2 normal-case">
                  <input
                    type="color"
                    value={value.secondary_color}
                    onChange={(e) => patch({ secondary_color: e.target.value })}
                    className="h-10 w-14 cursor-pointer rounded border border-cyber-border bg-transparent"
                  />
                  <span className="font-mono text-xs text-cyber-text">
                    {value.secondary_color}
                  </span>
                </span>
              </label>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
                Logo client (PNG / JPG)
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                <input
                  ref={fileRef}
                  type="file"
                  accept="image/png,image/jpeg"
                  className="hidden"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    e.target.value = "";
                    if (!file) return;
                    try {
                      const url = await readImageFileAsDataUrl(file);
                      patch({ logo_data_url: url });
                    } catch (err) {
                      alert(
                        err instanceof Error ? err.message : "Import logo échoué.",
                      );
                    }
                  }}
                />
                <button
                  type="button"
                  className="cyber-action-btn text-[10px]"
                  onClick={() => fileRef.current?.click()}
                >
                  Choisir une image
                </button>
                {value.logo_data_url ? (
                  <>
                    <img
                      src={value.logo_data_url}
                      alt="Logo"
                      className="h-10 w-10 rounded-lg border border-cyber-border object-contain"
                    />
                    <button
                      type="button"
                      className="text-[10px] text-cyber-muted underline hover:text-cyber-text"
                      onClick={() => patch({ logo_data_url: null })}
                    >
                      Retirer
                    </button>
                  </>
                ) : null}
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <SectionTitle>Utilisateur fictif</SectionTitle>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-[10px] uppercase tracking-wider text-cyber-muted">
                Nom et prénom
                <input
                  type="text"
                  value={value.user_name}
                  maxLength={48}
                  onChange={(e) => patch({ user_name: e.target.value })}
                  className="mt-1 w-full rounded border border-cyber-border bg-cyber-bg px-3 py-2 text-sm text-cyber-text"
                />
              </label>
              <label className="block text-[10px] uppercase tracking-wider text-cyber-muted">
                Rôle / poste
                <input
                  type="text"
                  value={value.user_role}
                  maxLength={48}
                  onChange={(e) => patch({ user_role: e.target.value })}
                  className="mt-1 w-full rounded border border-cyber-border bg-cyber-bg px-3 py-2 text-sm text-cyber-text"
                />
              </label>
            </div>
            <div className="flex items-center gap-3 rounded-md border border-cyber-border bg-cyber-bg/60 px-3 py-2">
              <div
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-sm font-bold text-white"
                style={{
                  background: `linear-gradient(135deg, ${value.primary_color}, ${value.secondary_color})`,
                }}
                aria-hidden
              >
                {initials}
              </div>
              <p className="text-[10px] text-cyber-muted normal-case">
                Avatar initiales généré automatiquement :{" "}
                <span className="font-mono text-cyber-text">{initials}</span>
              </p>
            </div>
          </div>

          <div className="space-y-3">
            <SectionTitle>Contenu métier</SectionTitle>
            <div className="space-y-2">
              <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
                Tâches / éléments de la démo
              </p>
              <ul className="space-y-2">
                {value.tasks.map((task, index) => (
                  <li
                    key={`task-${index}`}
                    className="flex flex-wrap items-center gap-2 rounded border border-cyber-border bg-cyber-bg/50 p-2"
                  >
                    <input
                      type="checkbox"
                      checked={task.completed}
                      onChange={(e) => {
                        const next = [...value.tasks];
                        next[index] = {
                          ...task,
                          completed: e.target.checked,
                        };
                        updateTasks(next);
                      }}
                      className="accent-cyber-accent"
                      aria-label="Terminée"
                    />
                    <input
                      type="text"
                      value={task.text}
                      maxLength={140}
                      onChange={(e) => {
                        const next = [...value.tasks];
                        next[index] = { ...task, text: e.target.value };
                        updateTasks(next);
                      }}
                      className="min-w-0 flex-1 rounded border border-cyber-border bg-cyber-bg px-2 py-1 text-xs text-cyber-text"
                    />
                    <button
                      type="button"
                      className="text-[10px] text-red-400 hover:underline"
                      onClick={() => {
                        const next = value.tasks.filter((_, i) => i !== index);
                        updateTasks(next.length ? next : [{ text: "Nouvelle tâche", completed: false }]);
                      }}
                    >
                      Suppr.
                    </button>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className="cyber-action-btn text-[10px]"
                onClick={() =>
                  updateTasks([
                    ...value.tasks,
                    { text: "Nouvelle tâche", completed: false },
                  ])
                }
              >
                + Ajouter une tâche
              </button>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {(
                [
                  ["total", "Total"],
                  ["active", "En cours"],
                  ["done", "Terminées"],
                ] as const
              ).map(([key, label]) => (
                <label
                  key={key}
                  className="block text-[10px] uppercase tracking-wider text-cyber-muted"
                >
                  {label}
                  <input
                    type="number"
                    min={0}
                    value={value.stats[key]}
                    onChange={(e) => updateStat(key, e.target.value)}
                    className="mt-1 w-full rounded border border-cyber-border bg-cyber-bg px-2 py-1.5 font-mono text-sm text-cyber-text"
                  />
                </label>
              ))}
            </div>
            <button
              type="button"
              className="text-[10px] text-cyber-muted underline hover:text-cyber-text"
              onClick={() => patch({ stats: statsFromTasks(value.tasks) })}
            >
              Recalculer les stats depuis les tâches
            </button>
          </div>
        </div>

        <div className="flex min-h-[360px] flex-col overflow-hidden rounded-lg border border-cyber-border xl:sticky xl:top-4 xl:min-h-[70vh]">
          <div className="border-b border-cyber-border px-3 py-2 text-[10px] text-cyber-muted">
            Aperçu en direct
            {previewLoading ? " · mise à jour…" : ""}
          </div>
          {previewHtml ? (
            <iframe
              title="Aperçu personnalisation"
              className="min-h-0 flex-1 bg-[#0b0f1a]"
              sandbox="allow-scripts allow-same-origin allow-forms"
              srcDoc={prepareInternalPreviewSrcDoc(previewHtml)}
            />
          ) : (
            <div className="flex flex-1 items-center justify-center p-4 text-center text-xs text-cyber-muted">
              Aperçu en cours de chargement…
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export { cloneCustomization };

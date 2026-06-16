import type { MobileAppRecord } from "@/lib/mobile-builder-api";
import { Button } from "@/components/ui";

function statusBadge(status: string): { label: string; className: string } {
  switch (status) {
    case "building":
      return {
        label: "Build",
        className: "border-cyan-500/40 bg-cyan-500/10 text-cyan-200",
      };
    case "ready":
      return {
        label: "Prêt",
        className: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200",
      };
    case "generated":
      return {
        label: "Généré",
        className: "border-violet-500/40 bg-violet-500/10 text-violet-200",
      };
    case "failed":
      return {
        label: "Échec",
        className: "border-red-500/40 bg-red-500/10 text-red-200",
      };
    default:
      return {
        label: "Brouillon",
        className: "border-white/10 bg-white/5 text-cf-muted",
      };
  }
}

export function MobileBuilderSidebar({
  apps,
  selectedId,
  loading,
  onSelect,
  onNew,
  onDelete,
  onBuild,
}: {
  apps: MobileAppRecord[];
  selectedId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onBuild: (id: string) => void;
}) {
  return (
    <aside className="w-[280px] shrink-0 border-r border-white/10 bg-[#0f1117]/60 p-4">
      <div className="mb-4 flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
          Apps mobiles
        </p>
        <Button variant="primary" size="sm" icon="ti ti-plus" onClick={onNew}>
          Nouvelle app
        </Button>
      </div>

      {loading ? (
        <p className="text-sm text-cf-muted">Chargement…</p>
      ) : apps.length === 0 ? (
        <p className="text-sm text-cf-muted">
          Aucune app. Créez votre première application mobile.
        </p>
      ) : (
        <div className="space-y-2">
          {apps.map((app) => {
            const selected = app.id === selectedId;
            const badge = statusBadge(app.status);
            return (
              <div
                key={app.id}
                className={[
                  "rounded-card border p-3",
                  selected
                    ? "border-cyan-500/40 bg-white/7"
                    : "border-white/10 bg-white/5 hover:border-white/20",
                ].join(" ")}
              >
                <button
                  type="button"
                  onClick={() => onSelect(app.id)}
                  className="w-full text-left"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-white">
                        {app.name}
                      </p>
                      <p className="truncate text-xs text-cf-muted">
                        {app.app_slug}
                      </p>
                    </div>
                    <span
                      className={[
                        "shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase",
                        badge.className,
                      ].join(" ")}
                    >
                      {badge.label}
                    </span>
                  </div>
                  <p className="mt-1 text-[10px] uppercase tracking-wider text-cf-muted">
                    {app.mode === "product" ? "Produit SaaS" : "Client"} ·{" "}
                    {app.sector}
                  </p>
                </button>
                <div className="mt-2 flex gap-1">
                  <button
                    type="button"
                    onClick={() => onSelect(app.id)}
                    className="rounded px-2 py-1 text-[10px] text-cyan-300 hover:bg-white/5"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => onBuild(app.id)}
                    disabled={app.status === "draft"}
                    className="rounded px-2 py-1 text-[10px] text-violet-300 hover:bg-white/5 disabled:opacity-40"
                  >
                    Build
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(app.id)}
                    className="rounded px-2 py-1 text-[10px] text-red-300 hover:bg-white/5"
                  >
                    Delete
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </aside>
  );
}

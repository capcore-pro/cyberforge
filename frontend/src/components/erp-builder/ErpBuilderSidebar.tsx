import type { ErpProjectRecord } from "@/lib/erp-builder-api";
import { ERP_TYPE_LABELS } from "@/lib/erp-builder-api";
import { Button } from "@/components/ui";

function statusBadge(status: string): { label: string; className: string } {
  switch (status) {
    case "installing":
      return { label: "Installation", className: "border-cyan-500/40 bg-cyan-500/10 text-cyan-200" };
    case "running":
      return { label: "En ligne", className: "border-emerald-500/40 bg-emerald-500/10 text-emerald-200" };
    case "stopped":
      return { label: "Arrêté", className: "border-white/20 bg-white/5 text-cf-muted" };
    case "error":
      return { label: "Erreur", className: "border-red-500/40 bg-red-500/10 text-red-200" };
    case "configuring":
      return { label: "Config", className: "border-violet-500/40 bg-violet-500/10 text-violet-200" };
    default:
      return { label: "Brouillon", className: "border-white/10 bg-white/5 text-cf-muted" };
  }
}

function erpBadge(type: string | null): string {
  if (type === "odoo") return "border-violet-500/40 text-violet-200";
  if (type === "erpnext") return "border-cyan-500/40 text-cyan-200";
  if (type === "custom") return "border-emerald-500/40 text-emerald-200";
  return "border-white/10 text-cf-muted";
}

export function ErpBuilderSidebar({
  projects,
  selectedId,
  loading,
  onSelect,
  onNew,
  onDelete,
  onOpen,
  onStop,
}: {
  projects: ErpProjectRecord[];
  selectedId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onOpen: (project: ErpProjectRecord) => void;
  onStop: (id: string) => void;
}) {
  return (
    <aside className="w-[280px] shrink-0 border-r border-white/10 bg-[#0f1117]/60 p-4">
      <div className="mb-4 flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
          Projets ERP
        </p>
        <Button variant="primary" size="sm" icon="ti ti-plus" onClick={onNew}>
          Nouveau
        </Button>
      </div>

      {loading ? (
        <p className="text-sm text-cf-muted">Chargement…</p>
      ) : projects.length === 0 ? (
        <p className="text-sm text-cf-muted">Aucun projet ERP. Créez-en un pour commencer.</p>
      ) : (
        <div className="space-y-2">
          {projects.map((p) => {
            const selected = p.id === selectedId;
            const badge = statusBadge(p.status);
            const erpLabel = p.erp_type ? ERP_TYPE_LABELS[p.erp_type] : "—";
            return (
              <div
                key={p.id}
                className={[
                  "rounded-card border p-3",
                  selected ? "border-cyan-500/40 bg-white/7" : "border-white/10 bg-white/5",
                ].join(" ")}
              >
                <button type="button" onClick={() => onSelect(p.id)} className="w-full text-left">
                  <div className="flex items-start justify-between gap-2">
                    <p className="truncate text-sm font-semibold text-white">{p.name}</p>
                    <span className={["shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold", badge.className].join(" ")}>
                      {badge.label}
                    </span>
                  </div>
                  <span className={["mt-1 inline-block rounded border px-2 py-0.5 text-[10px]", erpBadge(p.erp_type)].join(" ")}>
                    {erpLabel}
                  </span>
                </button>
                <div className="mt-2 flex gap-1">
                  <button
                    type="button"
                    disabled={!p.url}
                    onClick={() => onOpen(p)}
                    className="rounded px-2 py-1 text-[10px] text-cyan-300 hover:bg-white/5 disabled:opacity-40"
                  >
                    Ouvrir
                  </button>
                  <button
                    type="button"
                    disabled={p.status !== "running"}
                    onClick={() => onStop(p.id)}
                    className="rounded px-2 py-1 text-[10px] text-amber-300 hover:bg-white/5 disabled:opacity-40"
                  >
                    Arrêter
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(p.id)}
                    className="rounded px-2 py-1 text-[10px] text-red-300 hover:bg-white/5"
                  >
                    Supprimer
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

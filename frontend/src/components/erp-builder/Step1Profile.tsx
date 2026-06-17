import type { ErpProjectUpsert } from "@/lib/erp-builder-api";
import {
  BUDGET_OPTIONS,
  COMPANY_SIZE_OPTIONS,
  MODULE_OPTIONS,
} from "@/lib/erp-builder-api";

export function Step1Profile({
  value,
  onChange,
  disabled,
}: {
  value: ErpProjectUpsert;
  onChange: (next: ErpProjectUpsert) => void;
  disabled?: boolean;
}) {
  function toggleModule(id: ErpProjectUpsert["modules"][number]) {
    const next = value.modules.includes(id)
      ? value.modules.filter((m) => m !== id)
      : [...value.modules, id];
    onChange({ ...value, modules: next });
  }

  return (
    <div className="space-y-8">
      <section>
        <h3 className="mb-3 text-lg font-semibold text-white">1. Vous êtes…</h3>
        <div className="grid gap-3 sm:grid-cols-2">
          {COMPANY_SIZE_OPTIONS.map((opt) => {
            const active = value.company_size === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                disabled={disabled}
                onClick={() => onChange({ ...value, company_size: opt.id })}
                className={[
                  "rounded-card border p-4 text-left transition-all",
                  active
                    ? "border-cyan-500/50 bg-cyan-500/10 ring-1 ring-cyan-500/30"
                    : "border-white/10 bg-white/5 hover:border-white/20",
                ].join(" ")}
              >
                <span className="text-2xl">{opt.icon}</span>
                <p className="mt-2 font-semibold text-white">{opt.label}</p>
                <p className="text-sm text-cf-muted">{opt.description}</p>
              </button>
            );
          })}
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-lg font-semibold text-white">
          2. Votre budget pour ce projet
        </h3>
        <div className="grid gap-3 sm:grid-cols-3">
          {BUDGET_OPTIONS.map((opt) => {
            const active = value.budget === opt.id;
            return (
              <button
                key={opt.id}
                type="button"
                disabled={disabled}
                onClick={() => onChange({ ...value, budget: opt.id })}
                className={[
                  "rounded-card border p-4 text-center transition-all",
                  active
                    ? "border-violet-500/50 bg-violet-500/10"
                    : "border-white/10 bg-white/5 hover:border-white/20",
                ].join(" ")}
              >
                <span className="text-2xl">{opt.icon}</span>
                <p className="mt-2 text-sm font-medium text-white">{opt.label}</p>
              </button>
            );
          })}
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-lg font-semibold text-white">
          3. Ce dont vous avez besoin
        </h3>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {MODULE_OPTIONS.map((opt) => {
            const active = value.modules.includes(opt.id);
            return (
              <button
                key={opt.id}
                type="button"
                disabled={disabled}
                onClick={() => toggleModule(opt.id)}
                className={[
                  "rounded-card border p-4 text-left transition-all",
                  active
                    ? "border-emerald-500/50 bg-emerald-500/10"
                    : "border-white/10 bg-white/5 hover:border-white/20",
                ].join(" ")}
              >
                <span className="text-xl">{opt.icon}</span>
                <p className="mt-2 text-sm font-medium text-white">{opt.label}</p>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}

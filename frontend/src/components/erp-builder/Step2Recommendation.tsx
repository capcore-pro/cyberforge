import type { ErpRecommendation, ErpType } from "@/lib/erp-builder-api";
import { ERP_TYPE_LABELS } from "@/lib/erp-builder-api";
import { Button } from "@/components/ui";

const ERP_ICONS: Record<ErpType, string> = {
  odoo: "ti ti-building-warehouse",
  erpnext: "ti ti-box",
  custom: "ti ti-leaf",
};

export function Step2Recommendation({
  recommendation,
  loading,
  showAlternatives,
  onToggleAlternatives,
  onChoose,
  onChooseAlt,
}: {
  recommendation: ErpRecommendation | null;
  loading: boolean;
  showAlternatives: boolean;
  onToggleAlternatives: () => void;
  onChoose: () => void;
  onChooseAlt: (type: ErpType) => void;
}) {
  if (loading) {
    return (
      <div className="flex min-h-[240px] items-center justify-center rounded-card border border-white/10 bg-[#0f1117]/60 p-8">
        <p className="animate-pulse text-cf-muted">CyberForge analyse votre profil…</p>
      </div>
    );
  }

  if (!recommendation) {
    return (
      <p className="text-sm text-cf-muted">
        Complétez l&apos;étape 1 puis passez à la recommandation.
      </p>
    );
  }

  const rec = recommendation;

  return (
    <div className="space-y-6">
      <div className="rounded-card border-2 border-cyan-500/40 bg-gradient-to-br from-cyan-500/10 to-violet-500/10 p-6">
        <div className="mb-2 flex items-center gap-2">
          <i className={`${ERP_ICONS[rec.erp_type]} text-2xl text-cyan-300`} />
          <span className="rounded-full border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-cyan-200">
            Recommandé pour vous
          </span>
        </div>
        <h3 className="text-2xl font-bold text-white">{rec.label}</h3>
        <p className="mt-2 text-sm leading-relaxed text-cf-muted">{rec.reason}</p>
        <p className="mt-3 text-sm text-white/90">{rec.description}</p>

        <ul className="mt-4 space-y-1">
          {rec.module_labels.map((label) => (
            <li key={label} className="flex items-center gap-2 text-sm text-emerald-200">
              <i className="ti ti-check text-emerald-400" />
              {label}
            </li>
          ))}
        </ul>

        <p className="mt-4 text-lg font-semibold text-violet-300">
          Prestation estimée : {rec.estimated_price_eur.toLocaleString("fr-FR")} € HT
        </p>

        <Button variant="primary" className="mt-4" icon="ti ti-check" onClick={onChoose}>
          Choisir cet ERP
        </Button>
      </div>

      <button
        type="button"
        onClick={onToggleAlternatives}
        className="text-xs text-cf-muted underline hover:text-white"
      >
        {showAlternatives ? "Masquer les autres options" : "Voir les autres options"}
      </button>

      {showAlternatives ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {rec.alternatives.map((alt) => (
            <div
              key={alt.erp_type}
              className="rounded-card border border-white/10 bg-white/5 p-4"
            >
              <p className="font-semibold text-white">
                {ERP_TYPE_LABELS[alt.erp_type as ErpType] ?? alt.label}
              </p>
              <p className="mt-1 text-xs text-cf-muted">{alt.description}</p>
              <button
                type="button"
                onClick={() => onChooseAlt(alt.erp_type as ErpType)}
                className="mt-3 text-xs text-cyan-300 hover:underline"
              >
                Choisir cette option
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

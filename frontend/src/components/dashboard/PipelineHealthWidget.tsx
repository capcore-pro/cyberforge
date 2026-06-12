import type { SupervisorStats } from "@/lib/dashboard-api";

interface PipelineHealthWidgetProps {
  data: SupervisorStats | null;
  loading?: boolean;
}

function passRateColor(rate: number): string {
  if (rate >= 0.9) return "text-teal-300";
  if (rate < 0.75) return "text-red-300";
  return "text-amber-200";
}

function qualityColor(score: number): string {
  if (score >= 70) return "text-amber-300";
  if (score < 50) return "text-red-300";
  return "text-amber-200";
}

function attemptsColor(attempts: number): string {
  if (attempts <= 1.5) return "text-teal-300";
  if (attempts > 2.5) return "text-red-300";
  return "text-white/80";
}

function formatPct(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

export function PipelineHealthWidget({
  data,
  loading,
}: PipelineHealthWidgetProps) {
  const stats = data ?? {
    total_validations: 0,
    pass_rate: 0,
    avg_quality_score: 0,
    avg_attempts: 0,
  };
  const hasData = stats.total_validations > 0;

  const passRateDisplay = formatPct(stats.pass_rate);
  const qualityDisplay = `${Math.round(stats.avg_quality_score)}/100`;
  const attemptsDisplay = stats.avg_attempts.toFixed(1);

  return (
    <div className="rounded-card border border-white/10 bg-white/5 p-5 shadow-[0_1px_0_rgba(255,255,255,0.04)_inset] backdrop-blur-xl">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className="inline-flex h-7 w-7 items-center justify-center rounded-control border border-white/10 bg-white/5 text-cf-gold"
            aria-hidden
          >
            <i className="ti ti-heart-rate-monitor text-sm" />
          </span>
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
            Santé du pipeline
          </h2>
        </div>
        <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-semibold text-cf-muted">
          30 derniers jours
        </span>
      </div>

      {loading ? (
        <div className="space-y-3 animate-pulse" aria-hidden>
          <div className="grid grid-cols-3 gap-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-14 rounded-control bg-white/10" />
            ))}
          </div>
        </div>
      ) : !hasData ? (
        <p className="text-sm text-cf-muted">
          Aucune validation enregistrée sur la période.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cf-muted">
                Taux validation
              </p>
              <p
                className={`mt-1 text-2xl font-semibold tabular-nums ${passRateColor(stats.pass_rate)}`}
              >
                {passRateDisplay}
              </p>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cf-muted">
                Score qualité
              </p>
              <p
                className={`mt-1 text-2xl font-semibold tabular-nums ${qualityColor(stats.avg_quality_score)}`}
              >
                {qualityDisplay}
              </p>
            </div>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cf-muted">
                Tentatives moy.
              </p>
              <p
                className={`mt-1 text-2xl font-semibold tabular-nums ${attemptsColor(stats.avg_attempts)}`}
              >
                {attemptsDisplay}
              </p>
            </div>
          </div>

          <div className="my-4 border-t border-white/10" />

          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-cf-muted">
            Validations ce mois
          </p>
          <p className="mt-1 text-sm text-cf-text">
            {stats.total_validations} validation
            {stats.total_validations > 1 ? "s" : ""}
          </p>

          {stats.avg_attempts > 2 ? (
            <p className="mt-3 rounded-control border border-amber-400/25 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-100">
              ⚠️ Nombre de retries élevé — vérifier les prompts ou le modèle
            </p>
          ) : null}

          {stats.pass_rate < 0.8 ? (
            <p className="mt-3 rounded-control border border-red-400/25 bg-red-500/10 px-3 py-2 text-[11px] text-red-100">
              ❌ Taux de validation bas — vérifier SupervisorAI
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}

import type { SupervisorStats } from "@/lib/dashboard-api";

interface PipelineHealthWidgetProps {
  data: SupervisorStats | null;
  loading?: boolean;
}

const V2_CARD =
  "rounded-[10px] border border-[rgba(0,212,255,0.1)] bg-[#0a0a12]";

function passRateColor(rate: number): string {
  if (rate >= 0.9) return "text-cf-green";
  if (rate < 0.75) return "text-cf-red";
  return "text-[#f59e0b]";
}

function qualityColor(score: number): string {
  if (score >= 70) return "text-cf-green";
  if (score < 50) return "text-cf-red";
  return "text-[#f59e0b]";
}

function attemptsColor(attempts: number): string {
  if (attempts <= 1.5) return "text-cf-green";
  if (attempts > 2.5) return "text-cf-red";
  return "text-cf-text";
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
    <div className={`${V2_CARD} p-5`}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-mono text-xs tracking-wide text-cf-cyan">
          // santé du pipeline
        </h2>
        <span className="rounded-full border border-[rgba(0,212,255,0.15)] bg-[#0d0d14] px-2 py-0.5 font-mono text-[10px] text-cf-muted">
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
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-cf-muted">
                Taux validation
              </p>
              <p
                className={`mt-1 font-mono text-2xl font-semibold tabular-nums ${passRateColor(stats.pass_rate)}`}
              >
                {passRateDisplay}
              </p>
            </div>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-cf-muted">
                Score qualité
              </p>
              <p
                className={`mt-1 font-mono text-2xl font-semibold tabular-nums ${qualityColor(stats.avg_quality_score)}`}
              >
                {qualityDisplay}
              </p>
            </div>
            <div>
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-cf-muted">
                Tentatives moy.
              </p>
              <p
                className={`mt-1 font-mono text-2xl font-semibold tabular-nums ${attemptsColor(stats.avg_attempts)}`}
              >
                {attemptsDisplay}
              </p>
            </div>
          </div>

          <div className="my-4 border-t border-[rgba(0,212,255,0.1)]" />

          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-cf-muted">
            Validations ce mois
          </p>
          <p className="mt-1 font-mono text-sm text-cf-text">
            {stats.total_validations} validation
            {stats.total_validations > 1 ? "s" : ""}
          </p>

          {stats.avg_attempts > 2 ? (
            <p className="mt-3 rounded-control border border-[#f59e0b]/25 bg-[#f59e0b]/10 px-3 py-2 text-[11px] text-[#f59e0b]">
              ⚠️ Nombre de retries élevé — vérifier les prompts ou le modèle
            </p>
          ) : null}

          {stats.pass_rate < 0.8 ? (
            <p className="mt-3 rounded-control border border-cf-red/25 bg-cf-red/10 px-3 py-2 text-[11px] text-cf-red">
              ❌ Taux de validation bas — vérifier SupervisorAI
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}

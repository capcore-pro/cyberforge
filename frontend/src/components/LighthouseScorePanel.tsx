import { useMemo, useState } from "react";
import type { LighthouseReportSummary } from "@shared/types";

interface LighthouseScorePanelProps {
  report: LighthouseReportSummary | null | undefined;
}

function barColor(score: number): string {
  if (score >= 90) return "bg-green-500";
  if (score >= 70) return "bg-orange-500";
  return "bg-red-500";
}

function barTrackColor(score: number): string {
  if (score >= 90) return "border-green-400/40 bg-green-400/10";
  if (score >= 70) return "border-orange-400/40 bg-orange-400/10";
  return "border-red-400/40 bg-red-400/10";
}

function globalBadgeClass(score: number): string {
  if (score >= 90) return "border-green-400/50 bg-green-400/10 text-green-400";
  if (score >= 70) return "border-orange-400/50 bg-orange-400/10 text-orange-300";
  return "border-red-400/50 bg-red-400/10 text-red-400";
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const clamped = Math.max(0, Math.min(100, score));
  return (
    <div className={`rounded-md border px-3 py-2 ${barTrackColor(clamped)}`}>
      <div className="mb-1 flex items-center justify-between text-[11px]">
        <span className="font-medium text-cf-text">{label}</span>
        <span className="tabular-nums text-cf-muted">{clamped}/100</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-cf-main/60">
        <div
          className={`h-full rounded-full transition-all ${barColor(clamped)}`}
          style={{ width: `${clamped}%` }}
          role="progressbar"
          aria-valuenow={clamped}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${label} : ${clamped} sur 100`}
        />
      </div>
    </div>
  );
}

/** Scores Lighthouse — 4 barres + badge global + rapport complet. */
export function LighthouseScorePanel({ report }: LighthouseScorePanelProps) {
  const [reportOpen, setReportOpen] = useState(false);

  const fullReportJson = useMemo(() => {
    if (!report?.full_report) return null;
    try {
      return JSON.stringify(report.full_report, null, 2);
    } catch {
      return null;
    }
  }, [report?.full_report]);

  if (!report || report.skipped) {
    return null;
  }

  const global = report.score_global ?? 0;
  const globalLabel =
    global >= 70 ? `Qualité OK ${global}/100` : `Qualité faible ${global}/100`;

  return (
    <div className="space-y-3 rounded-lg border border-cf-border-input bg-cf-secondary/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-cf-label">
          Lighthouse
        </p>
        <span
          className={`rounded-full border px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide ${globalBadgeClass(global)}`}
        >
          {globalLabel}
        </span>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        <ScoreBar label="Performance" score={report.performance} />
        <ScoreBar label="SEO" score={report.seo} />
        <ScoreBar label="Accessibilité" score={report.accessibility} />
        <ScoreBar label="Bonnes pratiques" score={report.best_practices} />
      </div>

      {report.recommendations && report.recommendations.length > 0 ? (
        <div className="text-[11px] text-cf-muted">
          <p className="font-medium text-cf-label">Recommandations</p>
          <ul className="mt-1 list-inside list-disc">
            {report.recommendations.slice(0, 5).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {(fullReportJson || report.recommendations?.length) ? (
        <button
          type="button"
          onClick={() => setReportOpen(true)}
          className="text-xs text-cf-gold hover:text-cf-gold-hover hover:underline"
        >
          Voir le rapport complet
        </button>
      ) : null}

      {reportOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Rapport Lighthouse complet"
        >
          <div className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-card border border-cf-border-input bg-cf-card shadow-card">
            <div className="flex items-center justify-between border-b border-cf-border-input px-4 py-3">
              <h3 className="text-sm font-semibold text-cf-text">Rapport Lighthouse</h3>
              <button
                type="button"
                onClick={() => setReportOpen(false)}
                className="text-cf-muted hover:text-cf-text"
              >
                Fermer
              </button>
            </div>
            <div className="overflow-auto p-4 text-xs">
              {report.recommendations && report.recommendations.length > 0 ? (
                <div className="mb-4">
                  <p className="mb-2 font-medium text-cf-label">Recommandations</p>
                  <ul className="list-inside list-disc space-y-1 text-cf-muted">
                    {report.recommendations.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {fullReportJson ? (
                <pre className="whitespace-pre-wrap break-words rounded-md bg-cf-main/80 p-3 text-[10px] text-cf-muted">
                  {fullReportJson}
                </pre>
              ) : (
                <p className="text-cf-muted">Rapport détaillé non disponible.</p>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

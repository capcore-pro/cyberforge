import type { PlaywrightReportSummary } from "@shared/types";

interface PlaywrightScoreBadgeProps {
  report: PlaywrightReportSummary | null | undefined;
  /** Affiche la liste passed/failed */
  showDetails?: boolean;
}

/**
 * Badge score Playwright — vert si score ≥ 70, rouge sinon.
 */
export function PlaywrightScoreBadge({
  report,
  showDetails = false,
}: PlaywrightScoreBadgeProps) {
  if (!report || report.skipped) {
    return null;
  }

  const score = report.score ?? 0;
  const ok = score >= 70;
  const label = ok ? `Tests OK ${score}/100` : `Tests échoués ${score}/100`;

  return (
    <div
      className={`inline-flex flex-col gap-2 rounded-lg border px-3 py-2 ${
        ok
          ? "border-green-400/50 bg-green-400/10"
          : "border-red-400/50 bg-red-400/10"
      }`}
      role="status"
      aria-label={`Tests Playwright : ${label}`}
    >
      <span
        className={`text-xs font-bold uppercase tracking-wider ${
          ok ? "text-green-400" : "text-red-400"
        }`}
      >
        {label}
      </span>
      {showDetails ? (
        <div className="space-y-2 text-left text-[11px]">
          {report.passed.length > 0 ? (
            <div>
              <p className="font-medium text-cf-label">Réussis</p>
              <ul className="mt-1 list-inside list-disc text-cf-muted">
                {report.passed.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {report.failed.length > 0 ? (
            <div>
              <p className="font-medium text-red-400/90">Échoués</p>
              <ul className="mt-1 list-inside list-disc text-cf-muted">
                {report.failed.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

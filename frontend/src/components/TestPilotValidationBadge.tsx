import type { ValidationStatus } from "@shared/types";

interface TestPilotValidationBadgeProps {
  status: ValidationStatus | null | undefined;
  summary?: string | null;
  passed?: boolean | null;
}

/**
 * Badge de validation TestPilotAI — Validé (vert) ou Corrigé (orange).
 */
export function TestPilotValidationBadge({
  status,
  summary,
  passed,
}: TestPilotValidationBadgeProps) {
  if (!status) {
    return null;
  }

  const isValidated = status === "validated";
  const label = isValidated ? "Validé" : "Corrigé";

  return (
    <div
      className={`inline-flex flex-col gap-1 rounded-lg border px-3 py-2 ${
        isValidated
          ? "border-green-400/50 bg-green-400/10"
          : "border-amber-400/50 bg-amber-400/10"
      }`}
      role="status"
      aria-label={`Validation TestPilotAI : ${label}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`text-[10px] font-bold uppercase tracking-wider ${
            isValidated ? "text-green-400" : "text-amber-400"
          }`}
        >
          TestPilotAI
        </span>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
            isValidated
              ? "bg-green-400/20 text-green-300"
              : "bg-amber-400/20 text-amber-300"
          }`}
        >
          {label}
        </span>
        {passed === false ? (
          <span className="text-[10px] text-cyber-muted">(avec réserves)</span>
        ) : null}
      </div>
      {summary ? (
        <p className="text-xs text-cyber-muted">{summary}</p>
      ) : null}
    </div>
  );
}

import type { PipelineAgentId, PipelineStepEvent } from "@shared/types";

export type PipelineStepStatus = "pending" | "active" | "done" | "error";

export interface PipelineStepState {
  id: PipelineAgentId;
  label: string;
  status: PipelineStepStatus;
  message?: string;
}

const DEFAULT_STEPS: PipelineStepState[] = [
  { id: "architect", label: "ArchitectAI", status: "pending" },
  { id: "builder", label: "BuilderAI", status: "pending" },
  { id: "coremind", label: "CoreMindAI", status: "pending" },
  { id: "visionui", label: "VisionUI", status: "pending" },
  { id: "bughunter", label: "BugHunterAI", status: "pending" },
];

const FRIENDLY_LABELS: Record<string, string> = {
  architect: "Plan du projet",
  openhands: "Code avancé OpenHands",
  builder: "Structure des pages",
  coremind: "Rédaction du contenu",
  visionui: "Mise en forme visuelle",
  bughunter: "Contrôle qualité",
  testpilot: "Tests finaux",
  playwright: "Tests Playwright",
  export: "Publication en ligne",
  autofix: "Ajustements automatiques",
};

function friendlyLabel(step: PipelineStepState): string {
  return FRIENDLY_LABELS[step.id] ?? step.label.replace(/AI$/i, "").trim();
}

const STATUS_STYLES: Record<PipelineStepStatus, string> = {
  pending: "border-cyber-border text-cyber-muted",
  active: "border-cf-gold text-cf-gold",
  done: "border-green-400/50 text-green-400",
  error: "border-red-400/50 text-red-400",
};

export function initialPipelineSteps(): PipelineStepState[] {
  return DEFAULT_STEPS.map((s) => ({ ...s }));
}

export function applyPipelineStepEvent(
  steps: PipelineStepState[],
  event: PipelineStepEvent,
): PipelineStepState[] {
  if (event.type === "pipeline_start") {
    return initialPipelineSteps();
  }
  const agent = event.agent;
  if (!agent || agent === "finalize") {
    return steps;
  }

  let next = [...steps];
  const idx = next.findIndex((s) => s.id === agent);
  if (
    idx < 0 &&
    (agent === "autofix" ||
      agent === "testpilot" ||
      agent === "export" ||
      agent === "openhands" ||
      agent === "playwright")
  ) {
    const label =
      agent === "autofix"
        ? "AutoFixAI"
        : agent === "testpilot"
          ? "TestPilotAI"
          : agent === "openhands"
            ? "OpenHands"
            : agent === "playwright"
              ? "Playwright"
              : "ExportAI";
    next = [
      ...next,
      { id: agent, label, status: "pending" as const },
    ];
  }

  const targetIdx = next.findIndex((s) => s.id === agent);
  if (targetIdx < 0) {
    return next;
  }

  const updated = { ...next[targetIdx] };
  if (event.type === "step_start") {
    updated.status = "active";
    updated.message = event.message;
  } else if (event.type === "step_done") {
    updated.status = event.ok === false ? "error" : "done";
    updated.message = event.message;
  } else if (event.type === "step_error") {
    updated.status = "error";
    updated.message = event.message;
  }

  next[targetIdx] = updated;

  if (event.type === "step_start" && agent !== "architect") {
    for (let i = 0; i < targetIdx; i += 1) {
      if (next[i].status === "pending" || next[i].status === "active") {
        next[i] = { ...next[i], status: "done" };
      }
    }
  }

  return next;
}

interface PipelineProgressProps {
  steps: PipelineStepState[];
  /** Libellés grand public (sans jargon technique). */
  friendly?: boolean;
}

export function PipelineProgress({ steps, friendly = false }: PipelineProgressProps) {
  return (
    <ul
      className="space-y-2"
      aria-live="polite"
      aria-label={friendly ? "Progression de la génération" : "Progression du pipeline IA"}
    >
      {steps.map((step) => (
        <li
          key={step.id}
          className={`flex items-start gap-3 rounded-md border px-3 py-2 text-sm transition-colors ${STATUS_STYLES[step.status]}`}
        >
          <StepIcon status={step.status} />
          <div className="min-w-0 flex-1">
            <span className="font-semibold">
              {friendly ? friendlyLabel(step) : step.label}
            </span>
            {step.message ? (
              <p className="mt-0.5 text-xs opacity-90">{step.message}</p>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}

function StepIcon({ status }: { status: PipelineStepStatus }) {
  if (status === "active") {
    return (
      <span
        className="mt-0.5 inline-block h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent"
        aria-hidden
      />
    );
  }
  if (status === "done") {
    return (
      <span className="mt-0.5 text-green-400" aria-hidden>
        ✓
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="mt-0.5 text-red-400" aria-hidden>
        !
      </span>
    );
  }
  return (
    <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-cyber-muted/40" aria-hidden />
  );
}

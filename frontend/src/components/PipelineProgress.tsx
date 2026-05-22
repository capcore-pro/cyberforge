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
  { id: "coremind", label: "CoreMindAI", status: "pending" },
  { id: "bughunter", label: "BugHunterAI", status: "pending" },
];

const STATUS_STYLES: Record<PipelineStepStatus, string> = {
  pending: "border-cyber-border text-cyber-muted",
  active: "border-cyber-accent text-cyber-neon shadow-[0_0_12px_rgba(0,255,200,0.15)]",
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
  if (idx < 0 && agent === "autofix") {
    next = [
      ...next,
      { id: "autofix", label: "AutoFixAI", status: "pending" as const },
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
}

export function PipelineProgress({ steps }: PipelineProgressProps) {
  return (
    <ul className="space-y-2" aria-live="polite" aria-label="Progression du pipeline IA">
      {steps.map((step) => (
        <li
          key={step.id}
          className={`flex items-start gap-3 rounded-md border px-3 py-2 text-sm transition-colors ${STATUS_STYLES[step.status]}`}
        >
          <StepIcon status={step.status} />
          <div className="min-w-0 flex-1">
            <span className="font-semibold">{step.label}</span>
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

import { useEffect, useMemo, useState } from "react";
import type { PipelineAgentId } from "@shared/types";
import type { AgentRetryEvent } from "@/lib/pipeline-stream";
import type { PipelineStepState, PipelineStepStatus } from "@/components/PipelineProgress";

const V2_STEPS: {
  agentId: PipelineAgentId;
  icon: string;
  title: string;
  agentName: string;
  description: string;
  trackedAgent: string;
}[] = [
  {
    agentId: "architect",
    icon: "📋",
    title: "Plan du projet",
    agentName: "BriefAI",
    description: "Analyse et enrichissement du brief",
    trackedAgent: "BriefAI",
  },
  {
    agentId: "builder",
    icon: "⚡",
    title: "Structure HTML",
    agentName: "GeneratorAI",
    description: "Génération HTML premium (Sonnet)",
    trackedAgent: "GeneratorAI",
  },
  {
    agentId: "bughunter",
    icon: "🔍",
    title: "Contrôle qualité",
    agentName: "SupervisorAI",
    description: "Validation et corrections",
    trackedAgent: "SupervisorAI",
  },
  {
    agentId: "export",
    icon: "🚀",
    title: "Photos & Deploy",
    agentName: "DeployAI",
    description: "Images Pexels + Cloudflare",
    trackedAgent: "DeployAI",
  },
];

function formatElapsed(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  if (min > 0) return `${min}m ${sec.toString().padStart(2, "0")}s`;
  return `${sec}s`;
}

function formatDurationMs(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  return formatElapsed(ms);
}

function resolveStatus(
  agentId: PipelineAgentId,
  steps: PipelineStepState[],
): PipelineStepStatus {
  const step = steps.find((s) => s.id === agentId);
  return step?.status ?? "pending";
}

function progressPercent(steps: PipelineStepState[]): number {
  const statuses = V2_STEPS.map((s) => resolveStatus(s.agentId, steps));
  const done = statuses.filter((s) => s === "done").length;
  const active = statuses.some((s) => s === "active");
  if (done === V2_STEPS.length) return 100;
  const base = (done / V2_STEPS.length) * 100;
  return active ? Math.min(base + 12, 95) : base;
}

function StatusIcon({ status }: { status: PipelineStepStatus }) {
  if (status === "done") {
    return (
      <span className="text-base text-green-400" aria-hidden>
        ✅
      </span>
    );
  }
  if (status === "active") {
    return (
      <span
        className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-[#d4a843] border-t-transparent"
        aria-hidden
      />
    );
  }
  if (status === "error") {
    return (
      <span className="text-base text-red-400" aria-hidden>
        ✕
      </span>
    );
  }
  return (
    <span className="text-base text-white/25" aria-hidden>
      ○
    </span>
  );
}

interface GeneratorPipelineProgressProps {
  steps: PipelineStepState[];
  startedAt: number | null;
  agentDurations?: Partial<Record<string, number>>;
  retries?: AgentRetryEvent[];
  serverDurationMs?: number | null;
}

export function GeneratorPipelineProgress({
  steps,
  startedAt,
  agentDurations = {},
  retries = [],
  serverDurationMs = null,
}: GeneratorPipelineProgressProps) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!startedAt) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [startedAt]);

  const percent = useMemo(() => progressPercent(steps), [steps]);
  const elapsedMs = startedAt ? now - startedAt : 0;
  const displayElapsed =
    serverDurationMs != null && serverDurationMs > 0 ? serverDurationMs : elapsedMs;
  const allDone = percent >= 100;

  const supervisorRetries = retries.filter((r) => r.agent === "SupervisorAI");

  return (
    <div className="space-y-4">
      <div>
        <div className="mb-2 flex items-center justify-between text-xs text-white/50">
          <span>Progression globale</span>
          <span className="tabular-nums">
            {percent.toFixed(0)}% · {formatElapsed(displayElapsed)}
            {allDone && serverDurationMs != null && serverDurationMs > 0 ? (
              <span className="ml-1 text-[#d4a843]/80">(serveur)</span>
            ) : null}
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#d4a843]/80 to-[#d4a843] transition-all duration-200"
            style={{ width: `${percent}%` }}
            role="progressbar"
            aria-valuenow={percent}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      </div>

      <ul className="space-y-2">
        {V2_STEPS.map((def) => {
          const status = resolveStatus(def.agentId, steps);
          const isActive = status === "active";
          const duration = agentDurations[def.trackedAgent];
          return (
            <li
              key={def.agentId}
              className={`flex items-start gap-3 rounded-card border px-4 py-3 backdrop-blur-xl transition-all duration-200 ${
                isActive
                  ? "border-[#d4a843]/60 bg-[#d4a843]/10 shadow-[0_0_20px_rgba(212,168,67,0.12)]"
                  : status === "done"
                    ? "border-green-400/25 bg-white/5"
                    : "border-white/10 bg-white/5"
              }`}
            >
              <span className="mt-0.5 text-xl" aria-hidden>
                {def.icon}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-medium text-white">{def.title}</p>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                      isActive
                        ? "bg-[#d4a843]/20 text-[#d4a843]"
                        : "bg-white/10 text-white/50"
                    }`}
                  >
                    {def.agentName}
                  </span>
                  {typeof duration === "number" && status === "done" ? (
                    <span className="text-[10px] tabular-nums text-white/40">
                      {formatDurationMs(duration)}
                    </span>
                  ) : null}
                </div>
                <p className="mt-0.5 text-xs text-white/45">{def.description}</p>
                {def.agentId === "bughunter" && supervisorRetries.length > 0 ? (
                  <ul className="mt-2 space-y-1">
                    {supervisorRetries.map((retry) => (
                      <li
                        key={`${retry.attempt}-${retry.reason}`}
                        className="rounded-control border border-amber-400/30 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-200"
                      >
                        SupervisorAI — tentative {retry.attempt} — {retry.reason}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
              <div className="mt-1 shrink-0">
                <StatusIcon status={status} />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

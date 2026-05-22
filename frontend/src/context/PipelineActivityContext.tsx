import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { PipelineAgentId, PipelineStepEvent } from "@shared/types";

export type AgentRuntimeStatus = "standby" | "active";

const PIPELINE_AGENT_IDS: PipelineAgentId[] = [
  "architect",
  "coremind",
  "bughunter",
  "autofix",
];

type PipelineStatusMap = Record<string, AgentRuntimeStatus>;

function initialStatuses(): PipelineStatusMap {
  const map: PipelineStatusMap = {};
  for (const id of PIPELINE_AGENT_IDS) {
    map[id] = "standby";
  }
  return map;
}

function applyEvent(
  prev: PipelineStatusMap,
  event: PipelineStepEvent,
): PipelineStatusMap {
  if (event.type === "pipeline_start") {
    return initialStatuses();
  }
  if (event.type === "pipeline_end") {
    return initialStatuses();
  }
  const agent = event.agent;
  if (!agent || !PIPELINE_AGENT_IDS.includes(agent)) {
    return prev;
  }
  const next = { ...prev };
  if (event.type === "step_start") {
    next[agent] = "active";
  } else if (event.type === "step_done" || event.type === "step_error") {
    next[agent] = "standby";
  }
  return next;
}

interface PipelineActivityContextValue {
  statuses: PipelineStatusMap;
  pipelineRunning: boolean;
  dispatchPipelineEvent: (event: PipelineStepEvent) => void;
  setPipelineRunning: (running: boolean) => void;
  getAgentStatus: (agentId: string) => AgentRuntimeStatus;
}

const PipelineActivityContext =
  createContext<PipelineActivityContextValue | null>(null);

export function PipelineActivityProvider({ children }: { children: ReactNode }) {
  const [statuses, setStatuses] = useState<PipelineStatusMap>(initialStatuses);
  const [pipelineRunning, setPipelineRunning] = useState(false);

  const dispatchPipelineEvent = useCallback((event: PipelineStepEvent) => {
    setStatuses((prev) => applyEvent(prev, event));
    if (event.type === "pipeline_start") {
      setPipelineRunning(true);
    }
    if (event.type === "pipeline_end") {
      setPipelineRunning(false);
    }
  }, []);

  const getAgentStatus = useCallback(
    (agentId: string): AgentRuntimeStatus => {
      if (PIPELINE_AGENT_IDS.includes(agentId as PipelineAgentId)) {
        return statuses[agentId] ?? "standby";
      }
      return "standby";
    },
    [statuses],
  );

  const value = useMemo(
    () => ({
      statuses,
      pipelineRunning,
      dispatchPipelineEvent,
      setPipelineRunning,
      getAgentStatus,
    }),
    [
      statuses,
      pipelineRunning,
      dispatchPipelineEvent,
      getAgentStatus,
    ],
  );

  return (
    <PipelineActivityContext.Provider value={value}>
      {children}
    </PipelineActivityContext.Provider>
  );
}

export function usePipelineActivity(): PipelineActivityContextValue {
  const ctx = useContext(PipelineActivityContext);
  if (!ctx) {
    throw new Error(
      "usePipelineActivity doit être utilisé dans PipelineActivityProvider",
    );
  }
  return ctx;
}

export function usePipelineActivityOptional(): PipelineActivityContextValue | null {
  return useContext(PipelineActivityContext);
}

export { PIPELINE_AGENT_IDS };

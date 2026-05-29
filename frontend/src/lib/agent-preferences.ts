const STORAGE_KEY = "cyberforge.agentEnabled";

const DEFAULT_AGENT_IDS = [
  "coremind",
  "architect",
  "builder",
  "bughunter",
  "autofix",
  "visionui",
  "testpilot",
  "export",
] as const;

export type AgentPreferenceId = (typeof DEFAULT_AGENT_IDS)[number];

function readRaw(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    return parsed as Record<string, boolean>;
  } catch {
    return {};
  }
}

export function isAgentEnabled(agentId: string): boolean {
  const prefs = readRaw();
  if (agentId in prefs) return Boolean(prefs[agentId]);
  return true;
}

export function setAgentEnabled(agentId: string, enabled: boolean): void {
  const prefs = readRaw();
  prefs[agentId] = enabled;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
}

export function listAgentPreferences(): { id: AgentPreferenceId; enabled: boolean }[] {
  return DEFAULT_AGENT_IDS.map((id) => ({
    id,
    enabled: isAgentEnabled(id),
  }));
}

export function enabledAgentCount(): number {
  return DEFAULT_AGENT_IDS.filter((id) => isAgentEnabled(id)).length;
}

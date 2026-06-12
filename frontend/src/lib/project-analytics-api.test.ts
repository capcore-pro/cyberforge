import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  auditEventLabel,
  fetchProjectWorkflowHistory,
  formatCostEur,
  formatDuration,
  qualityBadgeVariant,
} from "./project-analytics-api";

vi.mock("@/lib/api-client", () => ({
  apiRequest: vi.fn(),
}));

import { apiRequest } from "@/lib/api-client";

function aggregateLLMUsageFromTest(items: unknown[]) {
  const byAgent = new Map<string, number>();
  let totalCost = 0;
  let totalTokens = 0;
  for (const raw of items) {
    const row = raw as Record<string, unknown>;
    const agent = String(row.agent_name ?? "unknown");
    const cost = Number(row.cost_usd ?? 0);
    const tokens = Number(row.total_tokens ?? row.tokens ?? 0);
    totalCost += cost;
    totalTokens += tokens;
    byAgent.set(agent, (byAgent.get(agent) ?? 0) + cost);
  }
  return {
    total_cost_usd: totalCost,
    total_tokens: totalTokens,
    by_agent: [...byAgent.entries()].map(([agent_name, cost_usd]) => ({
      agent_name,
      cost_usd,
    })),
  };
}

describe("project-analytics-api", () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it("fetchProjectWorkflowHistory returns [] without throwing on API error", async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      ok: false,
      status: 503,
      error: "unavailable",
      data: null,
    });

    await expect(fetchProjectWorkflowHistory("proj-invalid")).resolves.toEqual([]);
  });

  it("fetchProjectWorkflowHistory maps orchestration sessions", async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      ok: true,
      status: 200,
      data: {
        items: [
          {
            generation_id: "gen-1",
            workflow_id: "wf-site",
            status: "completed",
            agents_completed: ["brief", "generator"],
            total_agents: 8,
            started_at: "2026-06-10T10:00:00.000Z",
            completed_at: "2026-06-10T10:01:23.000Z",
            created_at: "2026-06-10T10:00:00.000Z",
          },
        ],
      },
    });

    const rows = await fetchProjectWorkflowHistory("proj-1");
    expect(rows).toHaveLength(1);
    expect(rows[0].generation_id).toBe("gen-1");
    expect(rows[0].agents_completed).toBe(2);
    expect(rows[0].duration_ms).toBe(83_000);
  });

  it("formats helpers for analytics panel", () => {
    expect(formatCostEur(0.1)).toBe("0.09€");
    expect(formatDuration(83_000)).toBe("1m 23s");
    expect(qualityBadgeVariant(82)).toBe("teal");
    expect(qualityBadgeVariant(70)).toBe("amber");
    expect(qualityBadgeVariant(40)).toBe("red");
    expect(auditEventLabel("project_generated")).toBe("Site déployé");
  });

  it("aggregates llm usage rows by agent", () => {
    const aggregated = aggregateLLMUsageFromTest([
      { agent_name: "GeneratorAI", cost_usd: 0.07, tokens: 1000 },
      { agent_name: "BriefAI", cost_usd: 0.01, tokens: 200 },
      { agent_name: "GeneratorAI", cost_usd: 0.02, tokens: 300 },
    ]);
    expect(aggregated.total_cost_usd).toBeCloseTo(0.1);
    expect(aggregated.by_agent).toHaveLength(2);
    expect(aggregated.by_agent[0].agent_name).toBe("GeneratorAI");
    expect(aggregated.by_agent[0].cost_usd).toBeCloseTo(0.09);
  });
});

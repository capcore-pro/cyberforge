import { describe, expect, it } from "vitest";
import {
  normalizeAgentRegistryEntry,
  sortAgents,
  type AgentRegistryEntry,
} from "./agents-api";

describe("agents-api", () => {
  it("normalizes registry row with JSON capabilities string", () => {
    const row = normalizeAgentRegistryEntry({
      agent_id: "brief",
      name: "BriefAI",
      slug: "brief-ai",
      category: "ingestion",
      description: "Test",
      version: "2.0.0",
      provider: "anthropic",
      model: "claude-haiku-4-5-20251001",
      capabilities: '["brief_analysis"]',
      system_prompt_slug: "brief-ai-system",
      enabled: true,
      in_pipeline: true,
      requires_key: "anthropic",
    });
    expect(row.capabilities).toEqual(["brief_analysis"]);
    expect(row.in_pipeline).toBe(true);
  });

  it("sorts pipeline agents first then category", () => {
    const agents: AgentRegistryEntry[] = [
      {
        agent_id: "email",
        name: "EmailAI",
        slug: "email",
        category: "communication",
        description: "",
        version: "1",
        provider: null,
        model: null,
        capabilities: [],
        system_prompt_slug: null,
        enabled: true,
        in_pipeline: false,
        requires_key: null,
      },
      {
        agent_id: "brief",
        name: "BriefAI",
        slug: "brief",
        category: "ingestion",
        description: "",
        version: "1",
        provider: null,
        model: null,
        capabilities: [],
        system_prompt_slug: null,
        enabled: true,
        in_pipeline: true,
        requires_key: null,
      },
    ];
    const sorted = sortAgents(agents);
    expect(sorted[0].agent_id).toBe("brief");
  });
});

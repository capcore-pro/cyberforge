import { describe, expect, it } from "vitest";
import { mergeGenerationEntries } from "./dashboard-api";

describe("dashboard-api", () => {
  it("merges sessions with audit events by generation_id", () => {
    const sessions = [
      {
        generation_id: "gen-1",
        workflow_id: "wf-1",
        project_id: "proj-1",
        status: "completed",
        agents_completed: 8,
        total_agents: 8,
        created_at: "2026-06-10T10:00:00Z",
      },
    ];
    const generations = [
      {
        project_id: "proj-1",
        created_at: "2026-06-10T10:05:00Z",
        event_data: {
          generation_id: "gen-1",
          client_name: "Boulangerie Dupont",
          project_type: "site_vitrine",
          cost_usd: 0.12,
          quality_score: 82,
        },
      },
    ];

    const merged = mergeGenerationEntries(sessions, generations);
    expect(merged).toHaveLength(1);
    expect(merged[0].clientName).toBe("Boulangerie Dupont");
    expect(merged[0].status).toBe("completed");
    expect(merged[0].qualityScore).toBe(82);
    expect(merged[0].costUsd).toBe(0.12);
  });

  it("falls back to audit events when sessions are empty", () => {
    const merged = mergeGenerationEntries(
      [],
      [
        {
          created_at: "2026-06-09T08:00:00Z",
          event_data: {
            client_name: "Client Test",
            project_type: "ecommerce",
            cost_usd: 0.09,
          },
        },
      ],
    );
    expect(merged).toHaveLength(1);
    expect(merged[0].clientName).toBe("Client Test");
    expect(merged[0].status).toBe("completed");
  });
});

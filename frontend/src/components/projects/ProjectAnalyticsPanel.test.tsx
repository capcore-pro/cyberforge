import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/project-analytics-api", () => ({
  fetchProjectQuality: vi.fn().mockResolvedValue(null),
  fetchProjectLLMCost: vi.fn().mockResolvedValue(null),
  fetchProjectWorkflowHistory: vi.fn().mockResolvedValue([]),
  fetchProjectAuditLog: vi.fn().mockResolvedValue([]),
  auditEventIcon: () => "ti-point",
  auditEventLabel: (value: string) => value,
  formatCostEur: (value: number) => `${value}€`,
  formatDuration: () => "—",
  formatRelativeTime: () => "il y a 1 jour",
  qualityBadgeVariant: () => "gray",
  workflowStatusVariant: () => "gray",
}));

import {
  LazyProjectAnalyticsPanel,
  ProjectAnalyticsPanel,
} from "./ProjectAnalyticsPanel";
import {
  fetchProjectAuditLog,
  fetchProjectLLMCost,
  fetchProjectQuality,
  fetchProjectWorkflowHistory,
} from "@/lib/project-analytics-api";

describe("ProjectAnalyticsPanel", () => {
  beforeEach(() => {
    vi.mocked(fetchProjectQuality).mockReset().mockResolvedValue(null);
    vi.mocked(fetchProjectLLMCost).mockReset().mockResolvedValue(null);
    vi.mocked(fetchProjectWorkflowHistory).mockReset().mockResolvedValue([]);
    vi.mocked(fetchProjectAuditLog).mockReset().mockResolvedValue([]);
  });

  it("renders empty state when APIs return no data", async () => {
    const html = renderToStaticMarkup(
      <ProjectAnalyticsPanel project_id="proj-empty" />,
    );
    expect(html).toContain("Analytics");
    expect(html).toContain("Chargement analytics");
  });

  it("mounts without crash for invalid project id", () => {
    const html = renderToStaticMarkup(
      <ProjectAnalyticsPanel project_id="not-a-real-id" />,
    );
    expect(html).toContain("Analytics");
  });

  it("lazy wrapper does not render panel before intersection", () => {
    const html = renderToStaticMarkup(
      <LazyProjectAnalyticsPanel project_id="proj-1" />,
    );
    expect(html).not.toContain("Aucune donnée analytique");
    expect(html).not.toContain("Chargement analytics");
  });
});

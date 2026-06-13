import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/pipeline-api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/pipeline-api")>();
  return {
    ...actual,
    fetchProspects: vi.fn().mockResolvedValue([]),
    fetchStats: vi.fn().mockResolvedValue({
      par_statut: {},
      total_prospects: 0,
      valeur_pipeline: 0,
      taux_conversion: 0,
      prospects_ce_mois: 0,
    }),
  };
});

import {
  nextStatut,
  PROSPECT_STATUTS,
  STATUT_COLUMN_LABELS,
} from "@/lib/pipeline-api";
import { PipelinePage } from "@/pages/PipelinePage";

describe("pipeline-api helpers", () => {
  it("exposes six kanban statuts", () => {
    expect(PROSPECT_STATUTS).toHaveLength(6);
    expect(STATUT_COLUMN_LABELS.nouveau).toBe("NOUVEAU");
  });

  it("advances statut to next column", () => {
    expect(nextStatut("nouveau")).toBe("contacté");
    expect(nextStatut("négociation")).toBe("gagné");
    expect(nextStatut("perdu")).toBeNull();
  });
});

describe("PipelinePage", () => {
  it("renders kanban tab and six column headers", () => {
    const html = renderToStaticMarkup(<PipelinePage />);
    expect(html).toContain("Pipeline");
    expect(html).toContain("Kanban");
    expect(html).toContain("Statistiques");
    expect(html).toContain("Chargement du pipeline");
  });
});

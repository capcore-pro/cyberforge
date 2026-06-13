import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/knowledge-api", () => ({
  fetchDocuments: vi.fn().mockResolvedValue([]),
  ingestText: vi.fn(),
  ingestFile: vi.fn(),
  deleteDocument: vi.fn(),
  searchKnowledgeSafe: vi.fn().mockResolvedValue({ ok: true, data: [] }),
  chunkScoreValue: () => 0.8,
  scoreBadgeVariant: () => "teal",
  sourceTypeBadgeVariant: () => "teal",
  truncateChunkContent: (value: string) => value,
  isKnowledgeFileAllowed: () => true,
  titleFromFilename: (name: string) => name.replace(/\.[^.]+$/, ""),
  KNOWLEDGE_ALLOWED_EXTENSIONS: [".txt", ".md", ".pdf"],
}));

import { KnowledgePage } from "@/pages/KnowledgePage";
import { fetchDocuments } from "@/lib/knowledge-api";

describe("KnowledgePage", () => {
  beforeEach(() => {
    vi.mocked(fetchDocuments).mockReset().mockResolvedValue([]);
  });

  it("renders main tabs and loading state", () => {
    const html = renderToStaticMarkup(<KnowledgePage />);
    expect(html).toContain("Base de connaissance");
    expect(html).toContain("Documents");
    expect(html).toContain("Ajouter");
    expect(html).toContain("Rechercher");
    expect(html).toContain("Graphe");
    expect(html).toContain("Chargement des documents");
  });
});

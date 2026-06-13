import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  chunkScoreValue,
  deleteDocument,
  fetchDocuments,
  ingestText,
  isKnowledgeFileAllowed,
  scoreBadgeVariant,
  searchKnowledge,
  sourceTypeBadgeVariant,
  titleFromFilename,
  truncateChunkContent,
} from "./knowledge-api";

vi.mock("@/lib/api-client", () => ({
  apiRequest: vi.fn(),
}));

import { apiRequest } from "@/lib/api-client";

describe("knowledge-api helpers", () => {
  it("maps source type to badge variants", () => {
    expect(sourceTypeBadgeVariant("pdf")).toBe("blue");
    expect(sourceTypeBadgeVariant("uploaded")).toBe("teal");
    expect(sourceTypeBadgeVariant("manual")).toBe("gray");
  });

  it("maps score to badge variants", () => {
    expect(scoreBadgeVariant(0.82)).toBe("teal");
    expect(scoreBadgeVariant(0.55)).toBe("amber");
    expect(scoreBadgeVariant(0.2)).toBe("gray");
  });

  it("prefers combined_score over similarity", () => {
    expect(
      chunkScoreValue({
        chunk_id: "c1",
        document_id: "d1",
        document_title: "Doc",
        content: "test",
        similarity: 0.4,
        combined_score: 0.81,
      }),
    ).toBe(0.81);
  });

  it("truncates chunk content to 150 chars", () => {
    const long = "a".repeat(200);
    expect(truncateChunkContent(long)).toHaveLength(151);
    expect(truncateChunkContent(long).endsWith("…")).toBe(true);
  });

  it("validates allowed file extensions", () => {
    expect(isKnowledgeFileAllowed(new File(["x"], "note.txt"))).toBe(true);
    expect(isKnowledgeFileAllowed(new File(["x"], "doc.pdf"))).toBe(true);
    expect(isKnowledgeFileAllowed(new File(["x"], "image.png"))).toBe(false);
  });

  it("derives title from filename", () => {
    expect(titleFromFilename("guide-onboarding.md")).toBe("guide-onboarding");
  });
});

describe("knowledge-api requests", () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
  });

  it("fetchDocuments returns normalized rows", async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      data: [
        {
          id: "doc-1",
          title: "Guide TXT",
          source_type: "uploaded",
          language: "fr",
          status: "indexed",
          created_at: "2026-06-10T10:00:00.000Z",
        },
      ],
    });

    const docs = await fetchDocuments();
    expect(docs).toHaveLength(1);
    expect(docs[0].title).toBe("Guide TXT");
    expect(docs[0].source_type).toBe("uploaded");
  });

  it("ingestText returns ingest result for txt upload flow", async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      data: {
        document_id: "doc-txt",
        chunks_count: 4,
        status: "indexed",
      },
    });

    const result = await ingestText("Guide", "x".repeat(120));
    expect(result.document_id).toBe("doc-txt");
    expect(result.chunks_count).toBe(4);
  });

  it("ingestText path can represent pdf indexing result", async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      data: {
        document_id: "doc-pdf",
        chunks_count: 12,
        status: "indexed",
      },
    });

    const result = await ingestText("Rapport PDF", "contenu extrait");
    expect(result.chunks_count).toBe(12);
  });

  it("searchKnowledge returns chunks with scores", async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      data: [
        {
          chunk_id: "chunk-1",
          document_id: "doc-1",
          document_title: "Guide",
          content: "Procédure onboarding",
          similarity: 0.62,
          combined_score: 0.78,
        },
      ],
    });

    const hits = await searchKnowledge("onboarding");
    expect(hits).toHaveLength(1);
    expect(hits[0].combined_score).toBe(0.78);
    expect(chunkScoreValue(hits[0])).toBe(0.78);
  });

  it("deleteDocument calls DELETE route", async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      ok: true,
      status: 200,
      statusText: "OK",
      data: { ok: true },
    });

    await expect(deleteDocument("doc-1")).resolves.toBeUndefined();
    expect(apiRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: "DELETE",
        path: "/api/knowledge/documents/doc-1",
      }),
    );
  });
});

import { describe, expect, it } from "vitest";
import {
  ENTITY_TYPE_COLORS,
  graphNodeKey,
} from "@/lib/knowledge-graph-api";
import {
  knowledgeGraphEdgesToFlow,
  layoutKnowledgeGraphNodes,
} from "@/lib/knowledge-graph-layout";

describe("knowledge-graph-layout", () => {
  it("maps entity types to colors", () => {
    expect(ENTITY_TYPE_COLORS.agent).toBe("#d4a843");
    expect(ENTITY_TYPE_COLORS.workflow).toBe("#6366f1");
  });

  it("builds reactflow nodes with stable ids", () => {
    const nodes = layoutKnowledgeGraphNodes([
      {
        id: "uuid-1",
        entity_type: "agent",
        entity_id: "brief",
        label: "BriefAI",
        properties: {},
      },
    ]);
    expect(nodes[0].id).toBe(graphNodeKey("agent", "brief"));
    expect(nodes[0].data.label).toBe("BriefAI");
    expect(nodes[0].data.color).toBe("#d4a843");
  });

  it("filters edges to visible node ids", () => {
    const visible = new Set([graphNodeKey("workflow", "wf1"), graphNodeKey("agent", "brief")]);
    const edges = knowledgeGraphEdgesToFlow(
      [
        {
          id: "e1",
          source_type: "workflow",
          source_id: "wf1",
          target_type: "agent",
          target_id: "brief",
          relation_type: "uses",
          weight: 1,
        },
        {
          id: "e2",
          source_type: "agent",
          source_id: "brief",
          target_type: "tool",
          target_id: "deploy",
          relation_type: "triggers",
          weight: 1,
        },
      ],
      visible,
    );
    expect(edges).toHaveLength(1);
    expect(edges[0].label).toBe("uses");
  });
});

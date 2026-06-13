import { describe, expect, it } from "vitest";
import {
  MAIN_NAV_GROUP,
  NAV_ITEMS,
  ROUTED_PAGES,
  SECONDARY_NAV_GROUP,
  type AppPage,
} from "./navigation";

describe("navigation — knowledge page", () => {
  it("exposes Base de connaissance after Médiathèque in secondary group", () => {
    const labels = SECONDARY_NAV_GROUP.items.map((item) => item.label);
    expect(labels).toEqual(["Médiathèque", "Base de connaissance"]);
    expect(SECONDARY_NAV_GROUP.items[1]).toMatchObject({
      id: "knowledge",
      iconClass: "ti ti-brain",
      enabled: true,
    });
  });

  it("includes knowledge in routed pages and full nav list", () => {
    expect(ROUTED_PAGES).toContain("knowledge");
    expect(NAV_ITEMS.some((item) => item.id === "knowledge")).toBe(true);
  });

  it("includes pipeline after clients in main nav", () => {
    const idxClients = MAIN_NAV_GROUP.items.findIndex((i) => i.id === "clients");
    const idxPipeline = MAIN_NAV_GROUP.items.findIndex((i) => i.id === "pipeline");
    expect(idxPipeline).toBe(idxClients + 1);
    expect(MAIN_NAV_GROUP.items[idxPipeline]).toMatchObject({
      label: "Pipeline",
      iconClass: "ti ti-chart-arrows-vertical",
    });
    expect(ROUTED_PAGES).toContain("pipeline");
  });

  it("keeps existing primary pages without regression", () => {
    const expected: AppPage[] = [
      "dashboard",
      "generator",
      "projects",
      "agents",
      "monitoring",
      "workflows",
      "perso",
      "clients",
      "pipeline",
      "accounting",
      "newsletter",
    ];
    for (const page of expected) {
      expect(MAIN_NAV_GROUP.items.some((item) => item.id === page)).toBe(true);
      expect(ROUTED_PAGES).toContain(page);
    }
    expect(ROUTED_PAGES).toContain("media_library");
    expect(ROUTED_PAGES).toContain("settings");
  });
});

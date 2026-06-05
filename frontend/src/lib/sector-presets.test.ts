import { describe, expect, it } from "vitest";
import {
  listSectorsForKind,
  REQUIRED_ECOMMERCE_SECTOR_LABELS,
  REQUIRED_RESERVATION_SECTOR_LABELS,
  REQUIRED_VITRINE_SECTOR_LABELS,
} from "./sector-presets";

describe("listSectorsForKind", () => {
  it("returns 8 vitrine sectors in order", () => {
    const sectors = listSectorsForKind("vitrine");
    expect(sectors).toHaveLength(8);
    expect(sectors.map((s) => s.label)).toEqual([...REQUIRED_VITRINE_SECTOR_LABELS]);
    expect(sectors.every((s) => s.kinds.includes("vitrine"))).toBe(true);
  });

  it("returns 7 reservation sectors in order", () => {
    const sectors = listSectorsForKind("reservation");
    expect(sectors).toHaveLength(7);
    expect(sectors.map((s) => s.label)).toEqual([...REQUIRED_RESERVATION_SECTOR_LABELS]);
    expect(sectors.every((s) => s.kinds.includes("reservation"))).toBe(true);
  });

  it("returns 6 ecommerce sectors in order", () => {
    const sectors = listSectorsForKind("ecommerce");
    expect(sectors).toHaveLength(6);
    expect(sectors.map((s) => s.label)).toEqual([...REQUIRED_ECOMMERCE_SECTOR_LABELS]);
    expect(sectors.every((s) => s.kinds.includes("ecommerce"))).toBe(true);
  });

  it("does not mix vitrine and reservation sectors", () => {
    const vitrineLabels = new Set(listSectorsForKind("vitrine").map((s) => s.label));
    const reservationLabels = new Set(
      listSectorsForKind("reservation").map((s) => s.label),
    );
    for (const label of reservationLabels) {
      expect(vitrineLabels.has(label)).toBe(false);
    }
  });
});

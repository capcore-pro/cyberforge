import { describe, expect, it } from "vitest";
import { computeProjectEstimation, resolveEstimationProfile } from "./generator-estimation";

describe("computeProjectEstimation", () => {
  it("maps reservation kind to site_reservation profile", () => {
    const est = computeProjectEstimation("reservation", "Camping familial");
    expect(est.profileId).toBe("site_reservation");
    expect(est.complexityLabel).toBe("Complexe (réservation)");
    expect(est.apiCostEur).toBe(0.5);
  });

  it("respects TYPE prefix in prompt", () => {
    expect(
      resolveEstimationProfile("vitrine", "TYPE: site_reservation\nCamping"),
    ).toBe("site_reservation");
  });

  it("maps vitrine kind to vitrine_next", () => {
    const est = computeProjectEstimation("vitrine", "Boulangerie");
    expect(est.complexityLabel).toBe("Simple (vitrine)");
    expect(est.apiCostEur).toBe(0.1);
  });

  it("maps app_web to advanced tier", () => {
    const est = computeProjectEstimation("app_web", "CRM");
    expect(est.complexityLabel).toBe("Avancé (app web)");
    expect(est.apiCostEur).toBe(0.8);
  });
});

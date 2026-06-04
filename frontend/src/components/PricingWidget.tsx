import type { ArchitectPlanCosts } from "@shared/types";

export interface PricingLiveData {
  architectPlan: ArchitectPlanCosts | null;
  totalEur: number;
  byService: Record<string, number>;
  marginMultiplier: number | null;
  updatedAt?: string | null;
}

export interface PricingWidgetProps {
  mode: "live" | "static";
  projectId: string;
  liveData?: PricingLiveData | null;
  className?: string;
}

/**
 * Tarification live/static — coûts API projet retirés (GET /projects/{id}/costs).
 */
export function PricingWidget(_props: PricingWidgetProps) {
  return null;
}

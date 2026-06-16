import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export interface DemoDeviceStats {
  mobile: number;
  tablet: number;
  desktop: number;
}

export interface DemoTrackingStats {
  total_views: number;
  unique_ips: number;
  by_device: DemoDeviceStats;
  last_viewed_at: string | null;
  views_this_week: number;
  views_this_month: number;
}

export async function fetchDemoStats(projectId: string): Promise<DemoTrackingStats> {
  return apiRequest<DemoTrackingStats>({
    method: "GET",
    path: `${API_PREFIX}/demo-tracking/${encodeURIComponent(projectId)}/stats`,
  });
}

export async function recordDemoView(
  projectId: string,
  demoUrl: string,
): Promise<void> {
  await apiRequest({
    method: "POST",
    path: `${API_PREFIX}/demo-tracking/view`,
    body: { project_id: projectId, demo_url: demoUrl },
  });
}

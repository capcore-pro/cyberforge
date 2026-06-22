import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";
import type { UnifiedProject } from "@/lib/unified-projects";

export interface OpenHandsDebugReport {
  success: boolean;
  project_id: string;
  iterations: number;
  issues_found: string[];
  corrections_applied: string[];
  quality_score: number;
  redeployed: boolean;
  deploy_url: string | null;
  report: Record<string, unknown>;
}

export function openhandsProjectType(project: UnifiedProject): string {
  if (project.projectType) {
    return project.projectType;
  }
  switch (project.type) {
    case "ecommerce":
      return "ecommerce";
    case "reservation":
      return "booking";
    case "app_web":
      return "web_app";
    case "extension":
      return "extension";
    default:
      return "website";
  }
}

export function debugOpenHandsProject(
  projectId: string,
  projectType: string,
  options?: { projectName?: string; redeployAfter?: boolean },
) {
  return apiRequest<OpenHandsDebugReport>({
    method: "POST",
    path: `${API_PREFIX}/openhands/debug`,
    body: {
      project_id: projectId,
      project_type: projectType,
      project_name: options?.projectName ?? "",
      redeploy_after: options?.redeployAfter ?? true,
    },
    timeoutMs: 180_000,
  });
}

export function fetchOpenHandsReport(projectId: string) {
  return apiRequest<{ project_id: string; report: Record<string, unknown> | null }>({
    method: "GET",
    path: `${API_PREFIX}/openhands/report/${encodeURIComponent(projectId)}`,
  });
}

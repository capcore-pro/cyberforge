import type { LighthouseReportSummary } from "@shared/types";

const REPORTS_KEY = "cyberforge.lighthouseReports";

function readAll(): Record<string, LighthouseReportSummary> {
  try {
    const raw = localStorage.getItem(REPORTS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    return parsed as Record<string, LighthouseReportSummary>;
  } catch {
    return {};
  }
}

export function saveLighthouseReport(
  projectKey: string,
  report: LighthouseReportSummary,
): void {
  if (!projectKey.trim()) return;
  const all = readAll();
  all[projectKey] = report;
  localStorage.setItem(REPORTS_KEY, JSON.stringify(all));
}

export function getLighthouseReport(
  projectKey: string | null | undefined,
): LighthouseReportSummary | null {
  if (!projectKey?.trim()) return null;
  return readAll()[projectKey] ?? null;
}

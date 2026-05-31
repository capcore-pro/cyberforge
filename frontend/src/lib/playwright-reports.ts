import type { PlaywrightReportSummary } from "@shared/types";

const REPORTS_KEY = "cyberforge.playwrightReports";

function readAll(): Record<string, PlaywrightReportSummary> {
  try {
    const raw = localStorage.getItem(REPORTS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    return parsed as Record<string, PlaywrightReportSummary>;
  } catch {
    return {};
  }
}

export function savePlaywrightReport(
  projectKey: string,
  report: PlaywrightReportSummary,
): void {
  if (!projectKey.trim()) return;
  const all = readAll();
  all[projectKey] = report;
  localStorage.setItem(REPORTS_KEY, JSON.stringify(all));
}

export function getPlaywrightReport(
  projectKey: string | null | undefined,
): PlaywrightReportSummary | null {
  if (!projectKey?.trim()) return null;
  return readAll()[projectKey] ?? null;
}

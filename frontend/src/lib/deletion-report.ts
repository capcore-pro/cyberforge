export type DeletionReportStatus = "ok" | "skipped" | "error";

export interface DeletionReportItem {
  label: string;
  status: DeletionReportStatus;
  detail?: string | null;
}

export interface DeletionReport {
  deleted: boolean;
  ok: boolean;
  items: DeletionReportItem[];
}

export function formatDeletionReport(items: DeletionReportItem[]): string {
  return items
    .map((item) => {
      if (item.status === "ok") {
        const detail = item.detail ? ` (${item.detail})` : "";
        return `✅ ${item.label} supprimé${detail}`;
      }
      if (item.status === "skipped") {
        const detail = item.detail ? ` — ${item.detail}` : "";
        return `— ${item.label}${detail}`;
      }
      const detail = item.detail ? ` — ${item.detail}` : "";
      return `⚠️ ${item.label} : erreur${detail} — supprimez manuellement si besoin`;
    })
    .join("\n");
}

import type { DocumentStatus } from "@/lib/legal-api";

const STATUS_LABELS: Record<DocumentStatus, string> = {
  draft: "Brouillon",
  sent: "Envoyé",
  signed: "Signé",
  paid: "Payé",
  cancelled: "Annulé",
};

const STATUS_CLASSES: Record<DocumentStatus, string> = {
  draft: "bg-slate-500/25 text-slate-200 border-slate-500/40",
  sent: "bg-blue-500/20 text-blue-200 border-blue-500/45",
  signed: "bg-violet-500/20 text-violet-200 border-violet-500/45",
  paid: "bg-emerald-500/20 text-emerald-200 border-emerald-500/45",
  cancelled: "bg-red-500/20 text-red-200 border-red-500/45",
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`inline-flex rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${STATUS_CLASSES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}

export const DOCUMENT_STATUS_OPTIONS: DocumentStatus[] = [
  "draft",
  "sent",
  "signed",
  "paid",
  "cancelled",
];

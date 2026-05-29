import type { StripeTransaction } from "@/lib/stripe-api";

const eurFmt = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
});

export function formatEur(value: number): string {
  return eurFmt.format(value);
}

export function formatDateFr(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function currentMonthKey(date = new Date()): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

export function currentMonthLabel(date = new Date()): string {
  return date.toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
}

export function filterTransactionsForMonth(
  transactions: StripeTransaction[],
  date = new Date(),
): StripeTransaction[] {
  const key = currentMonthKey(date);
  return transactions.filter((tx) => {
    const created = new Date(tx.created_at);
    return currentMonthKey(created) === key;
  });
}

function csvEscape(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

export function buildTransactionsCsv(transactions: StripeTransaction[]): string {
  const header = "Date,Description,Email,Montant EUR,Statut,Type";
  const rows = transactions.map((tx) =>
    [
      formatDateFr(tx.created_at),
      csvEscape(tx.description ?? ""),
      csvEscape(tx.customer_email ?? ""),
      String(tx.amount_eur),
      tx.status,
      tx.type,
    ].join(","),
  );
  return [header, ...rows].join("\n");
}

export function downloadTextFile(
  content: string,
  filename: string,
  mime = "text/csv;charset=utf-8",
): void {
  const blob = new Blob(["\uFEFF", content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export interface MonthlySummaryData {
  monthLabel: string;
  revenueMonthEur: number;
  apiExpensesMonthEur: number;
  estimatedProfitEur: number;
  totalCollectedEur: number;
  mrrEur: number;
  transactions: StripeTransaction[];
}

export function openMonthlySummaryPdf(data: MonthlySummaryData): void {
  const txRows = data.transactions
    .map(
      (tx) => `
      <tr>
        <td>${formatDateFr(tx.created_at)}</td>
        <td>${escapeHtml(tx.description ?? "—")}</td>
        <td>${escapeHtml(tx.customer_email ?? "—")}</td>
        <td style="text-align:right">${formatEur(tx.amount_eur)}</td>
        <td>${tx.status}</td>
      </tr>`,
    )
    .join("");

  const html = `<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <title>Récapitulatif ${escapeHtml(data.monthLabel)} — CapCore</title>
  <style>
    body { font-family: system-ui, sans-serif; color: #111; padding: 2rem; max-width: 900px; margin: 0 auto; }
    h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
    .subtitle { color: #555; margin-bottom: 2rem; }
    .metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; margin-bottom: 2rem; }
    .metric { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; }
    .metric label { display: block; font-size: 0.75rem; text-transform: uppercase; color: #666; }
    .metric strong { font-size: 1.25rem; }
    table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
    th, td { border-bottom: 1px solid #eee; padding: 0.5rem; text-align: left; }
    th { font-size: 0.7rem; text-transform: uppercase; color: #666; }
    @media print { body { padding: 0; } }
  </style>
</head>
<body>
  <h1>Récapitulatif comptable — ${escapeHtml(data.monthLabel)}</h1>
  <p class="subtitle">CyberForge CapCore — document généré le ${formatDateFr(new Date().toISOString())}</p>
  <div class="metrics">
    <div class="metric"><label>CA du mois</label><strong>${formatEur(data.revenueMonthEur)}</strong></div>
    <div class="metric"><label>CA total encaissé</label><strong>${formatEur(data.totalCollectedEur)}</strong></div>
    <div class="metric"><label>MRR (abonnements actifs)</label><strong>${formatEur(data.mrrEur)}</strong></div>
    <div class="metric"><label>Dépenses API du mois</label><strong>${formatEur(data.apiExpensesMonthEur)}</strong></div>
    <div class="metric"><label>Bénéfice estimé</label><strong>${formatEur(data.estimatedProfitEur)}</strong></div>
    <div class="metric"><label>Transactions du mois</label><strong>${data.transactions.length}</strong></div>
  </div>
  <h2>Transactions Stripe (${data.transactions.length})</h2>
  <table>
    <thead><tr><th>Date</th><th>Description</th><th>Client</th><th>Montant</th><th>Statut</th></tr></thead>
    <tbody>${txRows || "<tr><td colspan=\"5\">Aucune transaction ce mois.</td></tr>"}</tbody>
  </table>
  <script>window.onload = () => { window.print(); };</script>
</body>
</html>`;

  const win = window.open("", "_blank");
  if (!win) return;
  win.document.write(html);
  win.document.close();
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

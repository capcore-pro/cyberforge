import { useCallback, useEffect, useRef, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  buildTransactionsCsv,
  currentMonthLabel,
  downloadTextFile,
  filterTransactionsForMonth,
  formatEur,
  openMonthlySummaryPdf,
} from "@/lib/accounting-export";
import { fetchCockpitDashboard } from "@/lib/cockpit-api";
import { uploadMediaAsset, fetchMediaAsset } from "@/lib/media-api";
import { fetchProfileSettings, saveProfileSettings } from "@/lib/settings-api";
import {
  fetchStripeDashboard,
  fetchStripeTransactions,
} from "@/lib/stripe-api";

export function AccountingExportPanel() {
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<"csv" | "pdf" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [revenueMonth, setRevenueMonth] = useState(0);
  const [apiExpenses, setApiExpenses] = useState(0);
  const [monthTxCount, setMonthTxCount] = useState(0);

  const [kbisMediaId, setKbisMediaId] = useState<string | null>(null);
  const [kbisName, setKbisName] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [savingKbis, setSavingKbis] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    const [stripeRes, cockpitRes, txRes, profileRes] = await Promise.all([
      fetchStripeDashboard(),
      fetchCockpitDashboard(),
      fetchStripeTransactions({ status: "paid", limit: 500 }),
      fetchProfileSettings(),
    ]);

    setLoading(false);

    if (stripeRes.ok && stripeRes.data) {
      setRevenueMonth(stripeRes.data.revenue_this_month_eur ?? 0);
    }

    if (cockpitRes.ok && cockpitRes.data) {
      setApiExpenses(
        cockpitRes.data.spent_month_eur ?? cockpitRes.data.expenses?.month_eur ?? 0,
      );
    }

    if (txRes.ok && Array.isArray(txRes.data)) {
      setMonthTxCount(filterTransactionsForMonth(txRes.data).length);
    }

    if (profileRes.ok && profileRes.data) {
      setKbisMediaId(profileRes.data.kbis_media_id);
      if (profileRes.data.kbis_media_id) {
        const asset = await fetchMediaAsset(profileRes.data.kbis_media_id);
        if (asset.ok && asset.data) {
          setKbisName(asset.data.filename);
        }
      }
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCsvExport() {
    setExporting("csv");
    setError(null);
    setSuccess(null);

    const res = await fetchStripeTransactions({ limit: 500 });
    setExporting(null);

    if (!res.ok || !Array.isArray(res.data)) {
      setError(apiErrorMessage(res, "Impossible de charger les transactions."));
      return;
    }

    const monthTx = filterTransactionsForMonth(res.data);
    const csv = buildTransactionsCsv(monthTx);
    const label = currentMonthLabel().replace(/\s+/g, "_");
    downloadTextFile(csv, `transactions_${label}.csv`);
    setSuccess(`${monthTx.length} transaction(s) exportée(s) en CSV.`);
  }

  async function handlePdfExport() {
    setExporting("pdf");
    setError(null);
    setSuccess(null);

    const [stripeRes, cockpitRes, txRes] = await Promise.all([
      fetchStripeDashboard(),
      fetchCockpitDashboard(),
      fetchStripeTransactions({ limit: 500 }),
    ]);

    setExporting(null);

    if (!stripeRes.ok) {
      setError(apiErrorMessage(stripeRes, "Données Stripe indisponibles."));
      return;
    }

    const revenue = stripeRes.data?.revenue_this_month_eur ?? 0;
    const expenses =
      cockpitRes.ok && cockpitRes.data
        ? cockpitRes.data.spent_month_eur ?? cockpitRes.data.expenses?.month_eur ?? 0
        : 0;
    const transactions =
      txRes.ok && Array.isArray(txRes.data)
        ? filterTransactionsForMonth(txRes.data)
        : [];

    openMonthlySummaryPdf({
      monthLabel: currentMonthLabel(),
      revenueMonthEur: revenue,
      apiExpensesMonthEur: expenses,
      estimatedProfitEur: revenue - expenses,
      totalCollectedEur: stripeRes.data?.total_collected_eur ?? 0,
      mrrEur: stripeRes.data?.active_subscriptions_mrr_eur ?? 0,
      transactions,
    });
    setSuccess("Récapitulatif ouvert — enregistrez en PDF via Imprimer.");
  }

  async function handleKbisUpload(file: File) {
    setUploading(true);
    setError(null);
    setSuccess(null);

    const res = await uploadMediaAsset(file, { tags: "kbis,legal,capcore" });
    setUploading(false);

    if (!res.ok || !res.data) {
      setError(apiErrorMessage(res, "Échec de l'upload KBIS."));
      return;
    }

    setKbisMediaId(res.data.id);
    setKbisName(res.data.filename);

    setSavingKbis(true);
    const profileRes = await fetchProfileSettings();
    const saveRes = await saveProfileSettings({
      email: profileRes.data?.email ?? "",
      siret: profileRes.data?.siret ?? "",
      kbis_media_id: res.data.id,
    });
    setSavingKbis(false);

    if (!saveRes.ok) {
      setError(apiErrorMessage(saveRes, "KBIS uploadé mais liaison profil échouée."));
      return;
    }
    setSuccess("KBIS enregistré et lié à votre profil CapCore.");
  }

  const profit = revenueMonth - apiExpenses;

  if (loading) {
    return <p className="animate-pulse text-sm text-cf-muted">Préparation des exports…</p>;
  }

  return (
    <div className="space-y-8">
      <div className="rounded-card border border-cf-border-input bg-cf-secondary/40 p-5">
        <p className="cf-section-label mb-2">Aperçu du mois en cours</p>
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-cf-muted">
          <span>
            CA : <strong className="text-cf-gold">{formatEur(revenueMonth)}</strong>
          </span>
          <span>
            Dépenses API : <strong className="text-cf-text">{formatEur(apiExpenses)}</strong>
          </span>
          <span>
            Bénéfice estimé :{" "}
            <strong className={profit >= 0 ? "text-emerald-400" : "text-red-300"}>
              {formatEur(profit)}
            </strong>
          </span>
          <span>
            Transactions : <strong className="text-cf-text">{monthTxCount}</strong>
          </span>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-card border border-cf-border-input bg-cf-card p-6 shadow-card">
          <h3 className="mb-2 text-sm font-semibold text-cf-text">Export CSV</h3>
          <p className="mb-4 text-sm text-cf-muted">
            Toutes les transactions Stripe payées du mois ({currentMonthLabel()}).
          </p>
          <button
            type="button"
            disabled={exporting === "csv"}
            onClick={() => void handleCsvExport()}
            className="rounded-control border border-cf-gold/40 bg-cf-active px-4 py-2 text-sm text-cf-gold hover:border-cf-gold disabled:opacity-50"
          >
            {exporting === "csv" ? "Export…" : "Télécharger le CSV du mois"}
          </button>
        </div>

        <div className="rounded-card border border-cf-border-input bg-cf-card p-6 shadow-card">
          <h3 className="mb-2 text-sm font-semibold text-cf-text">Récapitulatif PDF</h3>
          <p className="mb-4 text-sm text-cf-muted">
            Synthèse mensuelle pour votre comptable (CA, dépenses, transactions). Imprimez ou
            enregistrez en PDF depuis le navigateur.
          </p>
          <button
            type="button"
            disabled={exporting === "pdf"}
            onClick={() => void handlePdfExport()}
            className="rounded-control border border-cf-gold bg-cf-gold px-4 py-2 text-sm font-medium text-cf-main hover:bg-cf-gold-hover disabled:opacity-50"
          >
            {exporting === "pdf" ? "Génération…" : "Générer le récapitulatif mensuel"}
          </button>
        </div>
      </div>

      {!kbisMediaId ? (
        <div className="rounded-card border border-cf-border-input bg-cf-card p-6 shadow-card">
          <h3 className="mb-2 text-sm font-semibold text-cf-text">KBIS entreprise</h3>
          <p className="mb-4 text-sm text-cf-muted">
            Aucun KBIS enregistré sur votre profil. Ajoutez-le ici pour vos dossiers comptables.
          </p>
          <input
            ref={fileRef}
            type="file"
            accept="application/pdf,image/*"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleKbisUpload(file);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            disabled={uploading || savingKbis}
            onClick={() => fileRef.current?.click()}
            className="rounded-control border border-cf-border-input px-4 py-2 text-sm text-cf-text hover:border-cf-gold/50 hover:text-cf-gold disabled:opacity-50"
          >
            {uploading || savingKbis ? "Enregistrement…" : "Uploader mon KBIS"}
          </button>
        </div>
      ) : (
        <p className="text-sm text-cf-muted">
          KBIS déjà enregistré sur votre profil
          {kbisName ? ` (${kbisName})` : ""}. Modifiable dans Paramètres → Mon profil.
        </p>
      )}

      {error ? (
        <p className="rounded-control border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}
      {success ? (
        <p className="rounded-control border border-cf-gold/30 bg-cf-active px-4 py-3 text-sm text-cf-gold">
          {success}
        </p>
      ) : null}
    </div>
  );
}

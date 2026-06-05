import { useCallback, useEffect, useRef, useState } from "react";
import { Download, FileText } from "lucide-react";
import {
  GLASS_BTN,
  GLASS_KPI,
  GLASS_SECTION,
  GOLD_BTN,
  logAccountingApiError,
  shouldSilenceApiError,
} from "@/components/accounting/accounting-theme";
import { AccountingToast } from "@/components/accounting/AccountingToast";
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
  const [toast, setToast] = useState<string | null>(null);

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

    const [stripeRes, cockpitRes, txRes, profileRes] = await Promise.all([
      fetchStripeDashboard(),
      fetchCockpitDashboard(),
      fetchStripeTransactions({ status: "paid", limit: 500 }),
      fetchProfileSettings(),
    ]);

    if (stripeRes.ok && stripeRes.data) {
      setRevenueMonth(stripeRes.data.revenue_this_month_eur ?? 0);
    } else if (!stripeRes.ok) {
      logAccountingApiError(
        "Export / Stripe",
        apiErrorMessage(stripeRes, "Stripe indisponible."),
      );
    }

    if (cockpitRes.ok && cockpitRes.data) {
      setApiExpenses(
        cockpitRes.data.spent_month_eur ??
          cockpitRes.data.expenses?.month_eur ??
          0,
      );
    } else if (!cockpitRes.ok) {
      logAccountingApiError(
        "Export / Cockpit",
        apiErrorMessage(cockpitRes, "Cockpit indisponible."),
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
    } else if (!profileRes.ok) {
      logAccountingApiError(
        "Export / profil",
        apiErrorMessage(profileRes, "Profil indisponible."),
      );
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCsvExport() {
    setExporting("csv");
    const res = await fetchStripeTransactions({ limit: 500 });
    setExporting(null);

    if (!res.ok || !Array.isArray(res.data)) {
      const msg = apiErrorMessage(res, "Impossible de charger les transactions.");
      if (shouldSilenceApiError(msg)) {
        logAccountingApiError("Export CSV", msg);
      } else {
        setToast(msg);
      }
      return;
    }

    const monthTx = filterTransactionsForMonth(res.data);
    const csv = buildTransactionsCsv(monthTx);
    const label = currentMonthLabel().replace(/\s+/g, "_");
    downloadTextFile(csv, `transactions_${label}.csv`);
    setToast(`${monthTx.length} transaction(s) exportée(s) en CSV.`);
  }

  async function handlePdfExport() {
    setExporting("pdf");

    const [stripeRes, cockpitRes, txRes] = await Promise.all([
      fetchStripeDashboard(),
      fetchCockpitDashboard(),
      fetchStripeTransactions({ limit: 500 }),
    ]);

    setExporting(null);

    if (!stripeRes.ok) {
      const msg = apiErrorMessage(stripeRes, "Données Stripe indisponibles.");
      logAccountingApiError("Export PDF", msg);
      setToast("Données Stripe indisponibles pour le récapitulatif.");
      return;
    }

    const revenue = stripeRes.data?.revenue_this_month_eur ?? 0;
    const expenses =
      cockpitRes.ok && cockpitRes.data
        ? cockpitRes.data.spent_month_eur ??
          cockpitRes.data.expenses?.month_eur ??
          0
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
    setToast("Récapitulatif ouvert — enregistrez en PDF via Imprimer.");
  }

  async function handleKbisUpload(file: File) {
    setUploading(true);
    const res = await uploadMediaAsset(file, { tags: "kbis,legal,capcore" });
    setUploading(false);

    if (!res.ok || !res.data) {
      const msg = apiErrorMessage(res, "Échec de l'upload KBIS.");
      if (!shouldSilenceApiError(msg)) setToast(msg);
      else logAccountingApiError("KBIS upload", msg);
      return;
    }

    setKbisMediaId(res.data.id);
    setKbisName(res.data.filename);

    setSavingKbis(true);
    const profileRes = await fetchProfileSettings();
    const saveRes = await saveProfileSettings({
      ...(profileRes.data ?? {}),
      kbis_media_id: res.data.id,
    });
    setSavingKbis(false);

    if (!saveRes.ok) {
      const msg = apiErrorMessage(saveRes, "KBIS uploadé mais liaison profil échouée.");
      logAccountingApiError("KBIS profil", msg);
      setToast("KBIS uploadé — liaison profil à refaire dans Paramètres.");
      return;
    }
    setToast("KBIS enregistré et lié à votre profil CapCore.");
  }

  const profit = revenueMonth - apiExpenses;

  if (loading) {
    return (
      <p className="animate-pulse text-sm text-white/50">
        Préparation des exports…
      </p>
    );
  }

  return (
    <div className="space-y-8">
      <div className={GLASS_SECTION}>
        <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/40">
          Aperçu du mois en cours
        </p>
        <div className="flex flex-wrap gap-x-8 gap-y-2 text-sm text-white/50">
          <span>
            CA :{" "}
            <strong className="text-[#d4a843]">{formatEur(revenueMonth)}</strong>
          </span>
          <span>
            Dépenses API :{" "}
            <strong className="text-white/80">{formatEur(apiExpenses)}</strong>
          </span>
          <span>
            Bénéfice estimé :{" "}
            <strong
              className={profit >= 0 ? "text-emerald-300" : "text-red-300"}
            >
              {formatEur(profit)}
            </strong>
          </span>
          <span>
            Transactions :{" "}
            <strong className="text-white/80">{monthTxCount}</strong>
          </span>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className={GLASS_KPI}>
          <Download className="mb-3 h-8 w-8 text-[#d4a843]/80" aria-hidden />
          <h3 className="text-sm font-semibold text-white">Export CSV</h3>
          <p className="mb-4 mt-2 text-sm text-white/50">
            Toutes les transactions Stripe payées du mois ({currentMonthLabel()}
            ).
          </p>
          <button
            type="button"
            disabled={exporting === "csv"}
            onClick={() => void handleCsvExport()}
            className={GLASS_BTN}
          >
            {exporting === "csv" ? "Export…" : "Télécharger le CSV du mois"}
          </button>
        </div>

        <div className={GLASS_KPI}>
          <FileText className="mb-3 h-8 w-8 text-[#d4a843]/80" aria-hidden />
          <h3 className="text-sm font-semibold text-white">Récapitulatif PDF</h3>
          <p className="mb-4 mt-2 text-sm text-white/50">
            Synthèse mensuelle pour votre comptable. Imprimez ou enregistrez en
            PDF depuis le navigateur.
          </p>
          <button
            type="button"
            disabled={exporting === "pdf"}
            onClick={() => void handlePdfExport()}
            className={GOLD_BTN}
          >
            {exporting === "pdf"
              ? "Génération…"
              : "Générer le récapitulatif mensuel"}
          </button>
        </div>
      </div>

      <div className={GLASS_SECTION}>
        <h3 className="mb-2 text-sm font-semibold text-white">KBIS entreprise</h3>
        {!kbisMediaId ? (
          <>
            <p className="mb-4 text-sm text-white/50">
              Aucun KBIS enregistré sur votre profil. Ajoutez-le ici pour vos
              dossiers comptables.
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
              className={GOLD_BTN}
            >
              {uploading || savingKbis
                ? "Enregistrement…"
                : "Uploader mon KBIS"}
            </button>
          </>
        ) : (
          <p className="text-sm text-white/50">
            KBIS déjà enregistré sur votre profil
            {kbisName ? ` (${kbisName})` : ""}. Modifiable dans Paramètres → Mon
            profil.
          </p>
        )}
      </div>

      <AccountingToast message={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}

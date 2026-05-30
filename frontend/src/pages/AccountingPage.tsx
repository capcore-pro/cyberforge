import { lazy, Suspense, useState } from "react";
import { PageLoader } from "@/components/PageLoader";

const AccountingOverviewPanel = lazy(() =>
  import("@/components/accounting/AccountingOverviewPanel").then((m) => ({
    default: m.AccountingOverviewPanel,
  })),
);
const AccountingExportPanel = lazy(() =>
  import("@/components/accounting/AccountingExportPanel").then((m) => ({
    default: m.AccountingExportPanel,
  })),
);
const StripeCapcorePanel = lazy(() =>
  import("@/components/accounting/StripeCapcorePanel").then((m) => ({
    default: m.StripeCapcorePanel,
  })),
);
const LegalPage = lazy(() =>
  import("@/pages/LegalPage").then((m) => ({ default: m.LegalPage })),
);

type AccountingTab = "overview" | "legal" | "stripe" | "export";

const TABS: { id: AccountingTab; label: string }[] = [
  { id: "overview", label: "Vue d'ensemble" },
  { id: "legal", label: "Devis & Factures" },
  { id: "stripe", label: "Mes revenus" },
  { id: "export", label: "Export" },
];

/**
 * Comptabilité — CA, dépenses, devis/factures, Stripe et exports.
 */
export function AccountingPage() {
  const [tab, setTab] = useState<AccountingTab>("overview");

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <header>
        <p className="cf-section-label mb-2">Finances CapCore</p>
        <h1 className="cf-page-title">Comptabilité</h1>
        <p className="mt-2 text-sm text-cf-muted">
          Chiffre d'affaires, dépenses API, documents commerciaux, Stripe et exports comptables.
        </p>
      </header>

      <nav className="flex flex-wrap gap-2 border-b border-cf-border-input pb-1">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`cf-subtab mb-1 ${tab === item.id ? "cf-subtab-active" : ""}`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <section
        className={
          tab === "legal" || tab === "stripe"
            ? ""
            : "rounded-card border border-cf-border-input bg-cf-card p-6 shadow-card"
        }
      >
        <Suspense fallback={<PageLoader />}>
          {tab === "overview" ? <AccountingOverviewPanel /> : null}
          {tab === "legal" ? <LegalPage embedded /> : null}
          {tab === "stripe" ? <StripeCapcorePanel /> : null}
          {tab === "export" ? <AccountingExportPanel /> : null}
        </Suspense>
      </section>
    </div>
  );
}

import { lazy, Suspense, useState } from "react";
import {
  ACC_TAB_ACTIVE,
  ACC_TAB_BASE,
} from "@/components/accounting/accounting-theme";
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
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-[#d4a843]/80">
          Finances CapCore
        </p>
        <h1 className="text-2xl font-semibold text-white">Comptabilité</h1>
        <p className="mt-2 text-sm text-white/50">
          Chiffre d'affaires, dépenses API, documents commerciaux, Stripe et
          exports comptables.
        </p>
      </header>

      <nav className="flex flex-wrap gap-1 border-b border-white/10">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`${ACC_TAB_BASE} ${tab === item.id ? ACC_TAB_ACTIVE : ""}`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <section>
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

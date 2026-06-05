import { useState } from "react";
import { DocumentsTab } from "@/components/legal/DocumentsTab";
import { LegalClientsPanel } from "@/components/legal/LegalClientsPanel";
import { MentionsCgvPanel } from "@/components/legal/MentionsCgvPanel";
import {
  PILL_ACTIVE,
  PILL_BASE,
} from "@/components/accounting/accounting-theme";

type LegalSection = "devis" | "factures" | "mentions" | "clients";

const SECTIONS: { id: LegalSection; label: string }[] = [
  { id: "devis", label: "Devis" },
  { id: "factures", label: "Factures" },
  { id: "mentions", label: "Mentions & CGV" },
  { id: "clients", label: "Clients" },
];

function SubTabs({
  current,
  onChange,
}: {
  current: LegalSection;
  onChange: (s: LegalSection) => void;
}) {
  return (
    <div className="mb-6 flex flex-wrap gap-2">
      {SECTIONS.map((s) => (
        <button
          key={s.id}
          type="button"
          onClick={() => onChange(s.id)}
          className={`${PILL_BASE} ${current === s.id ? PILL_ACTIVE : ""}`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}

/**
 * Module Légal — devis, factures, mentions légales, CGV et carnet clients.
 */
export function LegalPage({ embedded = false }: { embedded?: boolean }) {
  const [section, setSection] = useState<LegalSection>("devis");

  return (
    <div className={embedded ? "" : "mx-auto max-w-6xl px-4 py-6 md:px-6"}>
      {!embedded ? (
        <header className="mb-6">
          <h1 className="text-2xl font-semibold text-white">
            Légal &amp; commercial
          </h1>
          <p className="mt-1 text-sm text-white/50">
            Devis, factures, documents juridiques et carnet clients CapCore.
          </p>
        </header>
      ) : null}

      <SubTabs current={section} onChange={setSection} />

      {section === "devis" ? (
        <DocumentsTab docType="devis" docTypeLabel="Devis" />
      ) : null}
      {section === "factures" ? (
        <DocumentsTab
          docType="facture"
          docTypeLabel="Facture"
          enableConvertFromSignedDevis
        />
      ) : null}
      {section === "mentions" ? <MentionsCgvPanel /> : null}
      {section === "clients" ? <LegalClientsPanel /> : null}
    </div>
  );
}

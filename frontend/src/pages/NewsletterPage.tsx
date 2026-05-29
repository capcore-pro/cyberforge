import { useState } from "react";
import { NewsletterBroadcastPanel } from "@/components/newsletter/NewsletterBroadcastPanel";
import { NewsletterContactsPanel } from "@/components/newsletter/NewsletterContactsPanel";
import { SequencesPanel } from "@/components/newsletter/SequencesPanel";

type NewsletterSection = "sequences" | "broadcast" | "contacts";

const SECTIONS: { id: NewsletterSection; label: string }[] = [
  { id: "sequences", label: "Séquences" },
  { id: "broadcast", label: "Newsletter" },
  { id: "contacts", label: "Contacts" },
];

function SubTabs({
  current,
  onChange,
}: {
  current: NewsletterSection;
  onChange: (s: NewsletterSection) => void;
}) {
  return (
    <div className="cf-subtabs">
      {SECTIONS.map((s) => (
        <button
          key={s.id}
          type="button"
          onClick={() => onChange(s.id)}
          className={`cf-subtab ${current === s.id ? "cf-subtab-active" : ""}`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}

/**
 * Module Newsletter — séquences bienvenue, envois Brevo et contacts.
 */
export function NewsletterPage() {
  const [section, setSection] = useState<NewsletterSection>("sequences");

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 md:px-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-cyber-text">
          Newsletter CapCore
        </h1>
        <p className="mt-1 text-sm text-cyber-muted">
          Séquences de bienvenue, newsletters ponctuelles et carnet abonnés.
        </p>
      </header>

      <SubTabs current={section} onChange={setSection} />

      {section === "sequences" ? <SequencesPanel /> : null}
      {section === "broadcast" ? <NewsletterBroadcastPanel /> : null}
      {section === "contacts" ? <NewsletterContactsPanel /> : null}
    </div>
  );
}

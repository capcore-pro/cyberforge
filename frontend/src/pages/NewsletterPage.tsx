import { lazy, Suspense, useState } from "react";
import { PageLoader } from "@/components/PageLoader";

const TAB_INACTIVE =
  "border-b-2 border-transparent px-4 pb-3 pt-2 text-sm text-white/50 transition-colors hover:text-white/80";
const TAB_ACTIVE =
  "border-b-2 border-[#d4a843] px-4 pb-3 pt-2 text-sm font-medium text-[#d4a843]";

const SequencesPanel = lazy(() =>
  import("@/components/newsletter/SequencesPanel").then((m) => ({
    default: m.SequencesPanel,
  })),
);
const NewsletterBroadcastPanel = lazy(() =>
  import("@/components/newsletter/NewsletterBroadcastPanel").then((m) => ({
    default: m.NewsletterBroadcastPanel,
  })),
);
const NewsletterContactsPanel = lazy(() =>
  import("@/components/newsletter/NewsletterContactsPanel").then((m) => ({
    default: m.NewsletterContactsPanel,
  })),
);

type NewsletterSection = "sequences" | "broadcast" | "contacts";

const SECTIONS: { id: NewsletterSection; label: string }[] = [
  { id: "sequences", label: "Séquences" },
  { id: "broadcast", label: "Newsletter" },
  { id: "contacts", label: "Contacts" },
];

/**
 * Module Newsletter — séquences bienvenue, envois Brevo et contacts.
 */
export function NewsletterPage() {
  const [section, setSection] = useState<NewsletterSection>("sequences");

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <header>
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-[#d4a843]/80">
          Communications CapCore
        </p>
        <h1 className="text-2xl font-semibold text-white">Newsletter CapCore</h1>
        <p className="mt-2 text-sm text-white/50">
          Séquences de bienvenue, newsletters ponctuelles et carnet abonnés.
        </p>
      </header>

      <nav className="flex flex-wrap gap-1 border-b border-white/10">
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setSection(s.id)}
            className={section === s.id ? TAB_ACTIVE : TAB_INACTIVE}
          >
            {s.label}
          </button>
        ))}
      </nav>

      <Suspense fallback={<PageLoader />}>
        {section === "sequences" ? <SequencesPanel /> : null}
        {section === "broadcast" ? <NewsletterBroadcastPanel /> : null}
        {section === "contacts" ? <NewsletterContactsPanel /> : null}
      </Suspense>
    </div>
  );
}

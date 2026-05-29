import type { NewsletterEmail, WelcomeEmailType } from "@/lib/newsletter-api";

const STEPS: { type: WelcomeEmailType; label: string }[] = [
  { type: "welcome_j0", label: "J0" },
  { type: "welcome_j1", label: "J+1" },
  { type: "welcome_j3", label: "J+3" },
];

function stepIcon(email: NewsletterEmail | undefined): string {
  if (!email) return "○";
  if (email.status === "sent") return "✅";
  if (email.status === "failed") return "❌";
  if (email.status === "scheduled") return "⏳";
  return "○";
}

function stepTitle(email: NewsletterEmail | undefined, fallback: string): string {
  if (!email) return fallback;
  return `${fallback} — ${email.subject}`;
}

export function EmailTimeline({ emails }: { emails: NewsletterEmail[] }) {
  const byType = new Map(emails.map((e) => [e.type, e]));

  return (
    <div className="flex flex-wrap items-stretch gap-2 py-2">
      {STEPS.map((step, idx) => {
        const row = byType.get(step.type);
        const icon = stepIcon(row);
        return (
          <div key={step.type} className="flex items-center gap-2">
            <div
              className="min-w-[88px] rounded-md border border-cyber-border bg-cyber-bg/50 px-2 py-1.5 text-center"
              title={stepTitle(row, step.label)}
            >
              <div className="text-sm">{icon}</div>
              <div className="text-[10px] font-bold uppercase tracking-wide text-cyber-muted">
                {step.label}
              </div>
              {row ? (
                <div className="mt-0.5 truncate text-[9px] text-cyber-neon">
                  {row.status}
                </div>
              ) : null}
            </div>
            {idx < STEPS.length - 1 ? (
              <span className="text-cyber-border" aria-hidden>
                →
              </span>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

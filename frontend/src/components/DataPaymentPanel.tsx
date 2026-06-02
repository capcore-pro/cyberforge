import { useMemo, useState } from "react";
import { CreditCard, Database, ShieldCheck } from "lucide-react";
import { copyTextToClipboard } from "@/lib/generation-export";

type BadgeTone = "muted" | "blue" | "green" | "purple";

function badgeClass(tone: BadgeTone): string {
  if (tone === "blue")
    return "border-sky-500/40 bg-sky-500/10 text-sky-200";
  if (tone === "green")
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
  if (tone === "purple")
    return "border-fuchsia-500/40 bg-fuchsia-500/10 text-fuchsia-200";
  return "border-cf-border-input text-cf-muted";
}

function SmallBadge({ label, tone = "muted" }: { label: string; tone?: BadgeTone }) {
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${badgeClass(tone)}`}
    >
      {label}
    </span>
  );
}

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-3 rounded-card border border-cf-border-input bg-cf-secondary/30 p-4">
      <div className="flex items-center gap-2">
        <span className="text-cf-muted" aria-hidden>
          {icon}
        </span>
        <p className="text-sm font-semibold text-cf-text">{title}</p>
      </div>
      {children}
    </div>
  );
}

export function DataPaymentPanel({
  databaseSchema,
  authSchema,
  paymentConfig,
}: {
  databaseSchema: any | null;
  authSchema: any | null;
  paymentConfig: any | null;
}) {
  const [toast, setToast] = useState<string | null>(null);

  const dbSummary = typeof databaseSchema?.summary === "string" ? databaseSchema.summary : null;
  const dbTables: string[] = useMemo(() => {
    const tables = databaseSchema?.tables;
    if (!Array.isArray(tables)) return [];
    return tables
      .map((t: any) => (t && typeof t.name === "string" ? t.name : null))
      .filter(Boolean) as string[];
  }, [databaseSchema]);
  const dbSql = typeof databaseSchema?.sql === "string" ? databaseSchema.sql : "";

  const authType = typeof authSchema?.auth_type === "string" ? authSchema.auth_type : null;
  const authSummary = typeof authSchema?.summary === "string" ? authSchema.summary : null;
  const authRoles: string[] = useMemo(() => {
    const roles = authSchema?.roles;
    if (!Array.isArray(roles)) return [];
    return roles.map((r: any) => String(r)).filter(Boolean);
  }, [authSchema]);
  const authSql = typeof authSchema?.sql === "string" ? authSchema.sql : "";

  const paymentType =
    typeof paymentConfig?.payment_type === "string" ? paymentConfig.payment_type : null;
  const paymentSummary =
    typeof paymentConfig?.summary === "string" ? paymentConfig.summary : null;
  const stripeConfig = paymentConfig?.stripe_config ?? null;
  const frontendCode =
    typeof paymentConfig?.frontend_code === "string" ? paymentConfig.frontend_code : "";

  async function copy(label: string, text: string) {
    try {
      await copyTextToClipboard(text);
      setToast(label);
      window.setTimeout(() => setToast(null), 1800);
    } catch {
      setToast("Copie impossible");
      window.setTimeout(() => setToast(null), 1800);
    }
  }

  function authTone(): BadgeTone {
    if (authType === "single_user") return "blue";
    if (authType === "multi_user") return "green";
    if (authType === "agency") return "purple";
    return "muted";
  }

  function paymentBadge(): { label: string; tone: BadgeTone } {
    if (paymentType === "one_shot") return { label: "Paiement unique", tone: "blue" };
    if (paymentType === "subscription") return { label: "Abonnement", tone: "purple" };
    if (paymentType === "booking") return { label: "Réservation", tone: "green" };
    return { label: "Non requis", tone: "muted" };
  }

  const hasDb = Boolean(databaseSchema);
  if (!hasDb) return null;

  const pay = paymentBadge();

  return (
    <section className="space-y-4 rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="cf-section-label">Données & Paiement</p>
          <p className="mt-1 text-xs text-cf-muted">
            Schéma Supabase, RLS et configuration Stripe générés par les agents
          </p>
        </div>
        {toast ? (
          <span className="rounded-full border border-cf-border-input bg-cf-secondary px-2 py-0.5 text-[10px] text-cf-muted">
            {toast}
          </span>
        ) : null}
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Section title="Base de données" icon={<Database size={16} />}>
          {dbSummary ? (
            <p className="text-xs text-cf-muted">{dbSummary}</p>
          ) : (
            <p className="text-xs text-cf-muted">Non généré</p>
          )}

          {dbTables.length ? (
            <div className="flex flex-wrap gap-2">
              {dbTables.map((t) => (
                <SmallBadge key={t} label={t} tone="muted" />
              ))}
            </div>
          ) : (
            <p className="text-xs text-cf-muted">Non généré</p>
          )}

          <button
            type="button"
            className="rounded-control border border-cf-gold/40 bg-cf-active px-3 py-1.5 text-xs text-cf-gold hover:border-cf-gold disabled:opacity-50"
            disabled={!dbSql.trim()}
            onClick={() => void copy("SQL copié", dbSql)}
          >
            Copier le SQL
          </button>
        </Section>

        <Section title="Authentification" icon={<ShieldCheck size={16} />}>
          <div className="flex flex-wrap items-center gap-2">
            <SmallBadge label={authType ?? "Non généré"} tone={authTone()} />
          </div>

          {authSummary ? (
            <p className="text-xs text-cf-muted">{authSummary}</p>
          ) : (
            <p className="text-xs text-cf-muted">Non généré</p>
          )}

          {authRoles.length ? (
            <div className="flex flex-wrap gap-2">
              {authRoles.map((r) => (
                <SmallBadge key={r} label={r} tone={authTone()} />
              ))}
            </div>
          ) : (
            <p className="text-xs text-cf-muted">Non généré</p>
          )}

          <button
            type="button"
            className="rounded-control border border-cf-gold/40 bg-cf-active px-3 py-1.5 text-xs text-cf-gold hover:border-cf-gold disabled:opacity-50"
            disabled={!authSql.trim()}
            onClick={() => void copy("SQL Auth copié", authSql)}
          >
            Copier le SQL Auth
          </button>
        </Section>

        <Section title="Paiement Stripe" icon={<CreditCard size={16} />}>
          <div className="flex flex-wrap items-center gap-2">
            <SmallBadge label={pay.label} tone={pay.tone} />
          </div>

          {paymentSummary ? (
            <p className="text-xs text-cf-muted">{paymentSummary}</p>
          ) : (
            <p className="text-xs text-cf-muted">Non généré</p>
          )}

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-control border border-cf-border-input bg-cf-secondary px-3 py-1.5 text-xs text-cf-text hover:border-cf-gold/50 disabled:opacity-50"
              disabled={!stripeConfig}
              onClick={() =>
                void copy(
                  "Config Stripe copiée",
                  JSON.stringify(stripeConfig ?? {}, null, 2),
                )
              }
            >
              Copier config Stripe
            </button>
            <button
              type="button"
              className="rounded-control border border-cf-border-input bg-cf-secondary px-3 py-1.5 text-xs text-cf-text hover:border-cf-gold/50 disabled:opacity-50"
              disabled={!frontendCode.trim()}
              onClick={() => void copy("JS copié", frontendCode)}
            >
              Copier JS Frontend
            </button>
          </div>
        </Section>
      </div>
    </section>
  );
}


import { useState } from "react";
import type { CreateDemoResponse, DemoDuration } from "@/lib/demos-api";
import { copyTextToClipboard } from "@/lib/generation-export";

const DURATION_OPTIONS: { id: DemoDuration; label: string }[] = [
  { id: "24h", label: "24 heures" },
  { id: "48h", label: "48 heures" },
  { id: "7d", label: "7 jours" },
];

interface CreateDemoModalProps {
  open: boolean;
  busy: boolean;
  created: CreateDemoResponse | null;
  error: string | null;
  onClose: () => void;
  onCreate: (duration: DemoDuration) => void;
}

function formatExpiry(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

/**
 * Modal création démo client — durée + affichage lien / mot de passe.
 */
export function CreateDemoModal({
  open,
  busy,
  created,
  error,
  onClose,
  onCreate,
}: CreateDemoModalProps) {
  const [duration, setDuration] = useState<DemoDuration>("48h");
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  if (!open) return null;

  async function handleCopy(label: string, text: string) {
    try {
      await copyTextToClipboard(text);
      setCopyFeedback(label);
      window.setTimeout(() => setCopyFeedback(null), 2000);
    } catch {
      setCopyFeedback("Échec de la copie");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Créer une démo client"
    >
      <div className="w-full max-w-lg space-y-4 rounded-lg border border-cyber-violet/40 bg-cyber-surface p-6 shadow-neonViolet">
        <header>
          <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-cyber-violet">
            // client_demo
          </p>
          <h2 className="mt-1 text-lg font-bold text-cyber-neon">
            Créer une démo client
          </h2>
          <p className="mt-2 text-xs text-cyber-muted">
            Partagez un lien sécurisé avec un mot de passe temporaire. Le client
            pourra tester le livrable en lecture seule jusqu&apos;à expiration.
          </p>
        </header>

        {!created ? (
          <>
            <fieldset className="space-y-2">
              <legend className="text-[10px] uppercase tracking-wider text-cyber-muted">
                Durée de validité
              </legend>
              <div className="flex flex-wrap gap-2">
                {DURATION_OPTIONS.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    disabled={busy}
                    onClick={() => setDuration(opt.id)}
                    className={`rounded-lg border px-3 py-2 text-xs transition ${
                      duration === opt.id
                        ? "border-cyber-neon bg-cyber-violet/20 text-cyber-neon"
                        : "border-cyber-border text-cyber-muted hover:border-cyber-violet/50"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </fieldset>

            {error ? (
              <p className="rounded border border-red-400/30 bg-red-400/10 px-3 py-2 text-xs text-red-300">
                {error}
              </p>
            ) : null}

            <div className="flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className="cyber-action-btn"
                disabled={busy}
                onClick={onClose}
              >
                Annuler
              </button>
              <button
                type="button"
                className="cyber-action-btn cyber-action-btn-primary"
                disabled={busy}
                onClick={() => onCreate(duration)}
              >
                {busy ? "Création…" : "Générer le lien"}
              </button>
            </div>
          </>
        ) : (
          <>
            <section className="space-y-3 rounded border border-cyber-neon/30 bg-cyber-bg/60 p-4">
              <p className="text-xs text-cyber-text">
                Transmettez ces informations au client (mot de passe affiché une
                seule fois).
              </p>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
                  Application (Cloudflare)
                </p>
                <p className="mt-1 break-all font-mono text-[11px] text-cyber-accent">
                  {created.url}
                </p>
                <button
                  type="button"
                  className="cyber-action-btn mt-2"
                  onClick={() => void handleCopy("Lien application copié", created.url)}
                >
                  Copier le lien application
                </button>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
                  Accès mot de passe
                </p>
                <p className="mt-1 break-all font-mono text-[11px] text-cyber-violet">
                  {created.unlock_url}
                </p>
                <button
                  type="button"
                  className="cyber-action-btn mt-2"
                  onClick={() =>
                    void handleCopy("Lien accès copié", created.unlock_url)
                  }
                >
                  Copier le lien accès
                </button>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
                  Mot de passe
                </p>
                <p className="mt-1 font-mono text-lg tracking-wide text-cyber-neon">
                  {created.password}
                </p>
                <button
                  type="button"
                  className="cyber-action-btn mt-2"
                  onClick={() => void handleCopy("Mot de passe copié", created.password)}
                >
                  Copier le mot de passe
                </button>
              </div>
              <p className="text-[10px] text-cyber-muted">
                Expire le {formatExpiry(created.expires_at)} · {created.title}
              </p>
            </section>

            {copyFeedback ? (
              <p className="text-xs text-cyber-neon">{copyFeedback}</p>
            ) : null}

            <button type="button" className="cyber-action-btn w-full" onClick={onClose}>
              Fermer
            </button>
          </>
        )}
      </div>
    </div>
  );
}

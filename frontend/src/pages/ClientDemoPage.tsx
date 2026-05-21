import { useCallback, useEffect, useRef, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  fetchDemoMeta,
  unlockClientDemo,
  type DemoUnlockResponse,
} from "@/lib/demos-api";

interface ClientDemoPageProps {
  token: string;
}

function formatExpiry(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      dateStyle: "full",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

/**
 * Page publique client — /demo/{token}, mot de passe puis aperçu HTML (srcdoc).
 */
export function ClientDemoPage({ token }: ClientDemoPageProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("Démo CyberForge");
  const [expired, setExpired] = useState(false);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);

  const [password, setPassword] = useState("");
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [unlocking, setUnlocking] = useState(false);
  const [unlocked, setUnlocked] = useState<DemoUnlockResponse | null>(null);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const demoIframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const frame = demoIframeRef.current;
    if (!frame || !previewHtml) return;
    frame.srcdoc = previewHtml;
  }, [previewHtml]);

  const loadMeta = useCallback(async () => {
    setLoading(true);
    setError(null);
    const response = await fetchDemoMeta(token);
    setLoading(false);
    if (!response.ok || !response.data) {
      setError(
        apiErrorMessage(response, "Impossible de charger cette démo."),
      );
      return;
    }
    setTitle(response.data.title);
    setExpired(response.data.expired);
    setExpiresAt(response.data.expires_at);
  }, [token]);

  useEffect(() => {
    void loadMeta();
  }, [loadMeta]);

  async function handleUnlock(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = password.trim();
    if (!trimmed) {
      setError("Saisissez le mot de passe fourni par votre contact.");
      return;
    }
    setUnlocking(true);
    setError(null);
    const response = await unlockClientDemo(token, trimmed);
    setUnlocking(false);
    if (!response.ok || !response.data) {
      setError(
        apiErrorMessage(
          response,
          "Accès refusé. Vérifiez le mot de passe ou l'expiration du lien.",
        ),
      );
      return;
    }
    const cloudflareUrl = response.data.payload.cloudflare_url?.trim();
    if (cloudflareUrl) {
      window.location.assign(cloudflareUrl);
      return;
    }

    const html = response.data.payload.preview_html?.trim();
    if (
      !html ||
      !html.includes("<!DOCTYPE") ||
      html.includes('class=\\"') ||
      /id=["']cf-demo-root["']>\s*\\n/i.test(html)
    ) {
      setError(
        "Cette démo ne contient pas d'aperçu HTML valide. Recréez la démo depuis le Générateur.",
      );
      return;
    }
    setUnlocked(response.data);
    setPreviewHtml(html);
    setPassword("");
  }

  if (unlocked && previewHtml) {
    return (
      <div className="flex h-screen min-h-screen flex-col bg-cyber-bg">
        <header className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-cyber-border bg-cyber-surface/90 px-4 py-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-cyber-violet">
              Livrable client · application interactive
            </p>
            <h1 className="text-sm font-semibold text-cyber-neon">{unlocked.title}</h1>
          </div>
          <p className="text-[10px] text-cyber-muted">
            Expire le {formatExpiry(unlocked.expires_at)} — testez le produit comme en
            production (ajout, modification, navigation)
          </p>
        </header>
        <iframe
          ref={demoIframeRef}
          title={`Démo ${unlocked.title}`}
          className="min-h-0 flex-1 w-full bg-[#0a0a0f]"
          sandbox="allow-scripts allow-same-origin allow-forms"
        />
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
      <header className="mb-8 text-center">
        <p className="text-[10px] font-bold uppercase tracking-[0.35em] text-cyber-violet">
          CyberForge
        </p>
        <h1 className="mt-2 text-xl font-bold text-cyber-neon">{title}</h1>
        {expiresAt && !expired ? (
          <p className="mt-2 text-xs text-cyber-muted">
            Valide jusqu&apos;au {formatExpiry(expiresAt)}
          </p>
        ) : null}
      </header>

      {loading ? (
        <p className="text-center text-sm text-cyber-neon animate-pulse">
          Chargement…
        </p>
      ) : null}

      {expired && !loading ? (
        <section className="cyber-panel border-amber-400/30 p-5 text-center">
          <p className="text-sm text-amber-300">
            Cette démo a expiré. Demandez un nouveau lien à votre contact.
          </p>
        </section>
      ) : null}

      {error ? (
        <section className="cyber-panel border-red-400/30 p-4">
          <pre className="whitespace-pre-wrap text-xs text-red-300">{error}</pre>
        </section>
      ) : null}

      {!loading && !expired ? (
        <form onSubmit={(e) => void handleUnlock(e)} className="cyber-panel space-y-4 p-5">
          <p className="text-xs text-cyber-muted">
            Saisissez le mot de passe reçu (ex. trois mots séparés par des tirets).
          </p>
          <label className="block space-y-1">
            <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Mot de passe
            </span>
            <div className="flex gap-2">
              <input
                type={passwordVisible ? "text" : "password"}
                autoComplete="off"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="cyber-prompt-field min-h-0 flex-1 font-mono text-sm"
                placeholder="soleil-bateau-rouge"
                disabled={unlocking}
              />
              <button
                type="button"
                className="cyber-action-btn shrink-0"
                onClick={() => setPasswordVisible((v) => !v)}
                aria-pressed={passwordVisible}
              >
                {passwordVisible ? "Masquer" : "Afficher"}
              </button>
            </div>
          </label>
          <button
            type="submit"
            className="cyber-generate-btn w-full"
            disabled={unlocking}
          >
            {unlocking ? "Vérification…" : "Accéder à la démo"}
          </button>
        </form>
      ) : null}
    </div>
  );
}

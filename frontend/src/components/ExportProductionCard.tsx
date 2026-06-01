import { PasswordRevealField } from "@/components/PasswordRevealField";
import { buildClientDemoGmailComposeUrl } from "@/lib/gmail-compose-url";
import { withCyberforgeInternalPreview } from "@/lib/cyberforge-preview";

interface ExportProductionCardProps {
  productionUrl: string | null | undefined;
  exportProvider?: string | null;
  /** Lien client SPA (/demo/{token}) — envoi Gmail uniquement, pas l’aperçu in-app. */
  unlockUrl?: string | null;
  demoPassword?: string | null;
  githubUrl?: string | null;
  /** Ouvre l’iframe modale avec le HTML déjà en mémoire (pas localhost/demo). */
  onInternalPreview?: () => void;
  internalPreviewReady?: boolean;
}

/**
 * URL de production ExportAI — ouvrir la démo ou préparer l'envoi client.
 */
export function ExportProductionCard({
  productionUrl,
  exportProvider,
  unlockUrl,
  demoPassword,
  githubUrl,
  onInternalPreview,
  internalPreviewReady = false,
}: ExportProductionCardProps) {
  if (!productionUrl?.trim()) {
    return null;
  }

  const openUrl = withCyberforgeInternalPreview(productionUrl.trim());
  const clientUrl = unlockUrl?.trim() || productionUrl.trim();

  const gmailComposeUrl = buildClientDemoGmailComposeUrl({
    url: clientUrl,
    password: demoPassword,
  });

  return (
    <section
      className="cyber-panel space-y-4 border-cyber-neon/30 p-5"
      aria-label="Déploiement ExportAI"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-cyber-violet">
          Production
        </h3>
        {exportProvider ? (
          <span className="rounded border border-cyber-accent/30 bg-cyber-accent/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-cyber-neon">
            {exportProvider}
          </span>
        ) : null}
      </div>
      <p className="break-all font-mono text-sm text-cyber-neon">{openUrl}</p>
      {demoPassword ? (
        <PasswordRevealField password={demoPassword} label="Mot de passe démo" />
      ) : null}
      <div className="flex flex-wrap gap-2">
        {internalPreviewReady && onInternalPreview ? (
          <button
            type="button"
            onClick={onInternalPreview}
            className="cyber-action-btn cyber-action-btn-primary"
          >
            Aperçu CyberForge
          </button>
        ) : null}
        <a
          href={openUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="cyber-action-btn"
        >
          Ouvrir (Cloudflare)
        </a>
        <a
          href={gmailComposeUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="cyber-action-btn"
        >
          Envoyer au client
        </a>
        {githubUrl ? (
          <a
            href={githubUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="cyber-action-btn"
          >
            Code source
          </a>
        ) : null}
      </div>
    </section>
  );
}

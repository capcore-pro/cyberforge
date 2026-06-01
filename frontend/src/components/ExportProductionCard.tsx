import { PasswordRevealField } from "@/components/PasswordRevealField";
import { buildClientDemoGmailComposeUrl } from "@/lib/gmail-compose-url";
import { withCyberforgeInternalPreview } from "@/lib/cyberforge-preview";

interface ExportProductionCardProps {
  productionUrl: string | null | undefined;
  exportProvider?: string | null;
  artifactDownloadUrl?: string | null;
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
 * Extensions : lien ZIP uniquement (pas Cloudflare).
 */
export function ExportProductionCard({
  productionUrl,
  exportProvider,
  artifactDownloadUrl,
  unlockUrl,
  demoPassword,
  githubUrl,
  onInternalPreview,
  internalPreviewReady = false,
}: ExportProductionCardProps) {
  const zipUrl = artifactDownloadUrl?.trim();
  const prodUrl = productionUrl?.trim();
  if (!prodUrl && !zipUrl) {
    return null;
  }

  const isZipExport = exportProvider === "zip" || Boolean(zipUrl);
  const openUrl = prodUrl ? withCyberforgeInternalPreview(prodUrl) : "";
  const clientUrl = unlockUrl?.trim() || prodUrl || "";

  const gmailComposeUrl = buildClientDemoGmailComposeUrl({
    url: clientUrl,
    password: demoPassword,
  });

  return (
    <section
      className="cyber-panel space-y-4 border-cyber-neon/30 p-5"
      aria-label={isZipExport ? "Export extension Chrome" : "Déploiement ExportAI"}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-cyber-violet">
          {isZipExport ? "Extension Chrome" : "Production"}
        </h3>
        {exportProvider ? (
          <span className="rounded border border-cyber-accent/30 bg-cyber-accent/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-cyber-neon">
            {exportProvider}
          </span>
        ) : null}
      </div>
      {isZipExport ? (
        <p className="text-sm text-cyber-muted">
          Archive ZIP prête (manifest.json, popup.html, background.js, content.js).
          Chargez le dossier dézippé dans{" "}
          <span className="font-mono text-cyber-neon">chrome://extensions</span>.
        </p>
      ) : (
        <p className="break-all font-mono text-sm text-cyber-neon">{openUrl}</p>
      )}
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
        {zipUrl ? (
          <a
            href={zipUrl}
            download
            className="cyber-action-btn cyber-action-btn-primary"
          >
            Télécharger le ZIP
          </a>
        ) : null}
        {prodUrl ? (
          <a
            href={openUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="cyber-action-btn"
          >
            Ouvrir (Cloudflare)
          </a>
        ) : null}
        {clientUrl ? (
          <a
            href={gmailComposeUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="cyber-action-btn"
          >
            Envoyer au client
          </a>
        ) : null}
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

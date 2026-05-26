/**
 * Lien de composition Gmail (navigateur) — évite l'ouverture du client mail système (Outlook).
 */

export interface GmailComposeOptions {
  subject: string;
  body: string;
  to?: string;
}

/** URL Gmail « Nouveau message » avec sujet et corps pré-remplis. */
export function buildGmailComposeUrl({
  subject,
  body,
  to = "",
}: GmailComposeOptions): string {
  const params = new URLSearchParams({
    view: "cm",
    to,
    su: subject,
    body,
  });
  return `https://mail.google.com/mail/?${params.toString()}`;
}

export interface ClientDemoGmailOptions {
  /** Lien démo (URL de production ou unlock). */
  url: string;
  password?: string | null;
  title?: string;
  /** ISO 8601 — affiché dans le corps si fourni. */
  expiresAt?: string;
}

function formatExpiryFr(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

/** Corps type « envoi démo client » pour ExportAI ou modal création démo. */
export function buildClientDemoGmailComposeUrl({
  url,
  password,
  title,
  expiresAt,
}: ClientDemoGmailOptions): string {
  const subject = title?.trim()
    ? `Votre démo CyberForge — ${title.trim()}`
    : "Votre démo CyberForge";

  const lines = [
    "Bonjour,",
    "",
    "Voici votre démo en ligne :",
    url.trim(),
  ];
  if (password?.trim()) {
    lines.push("", `Mot de passe : ${password.trim()}`);
  }
  if (expiresAt?.trim()) {
    lines.push("", `Validité : jusqu'au ${formatExpiryFr(expiresAt.trim())}.`);
  }
  lines.push("", "Cordialement,");

  return buildGmailComposeUrl({ subject, body: lines.join("\n") });
}

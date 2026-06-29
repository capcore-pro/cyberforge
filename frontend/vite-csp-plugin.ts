import type { Plugin } from "vite";

/** CSP stricte pour le build production (fichiers script hashés, pas d'inline). */
export const PRODUCTION_CSP = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "connect-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:*",
  "img-src 'self' data: blob: http://127.0.0.1:* http://localhost:* https://*.replicate.delivery https://*.klingai.com https://replicate.delivery https://*.klingai.com",
  "font-src 'self' data:",
  "frame-src 'self' https: http://127.0.0.1:* http://localhost:* blob:",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "frame-ancestors 'none'",
].join("; ");

const CSP_META_RE =
  /\s*<meta[^>]*http-equiv=["']Content-Security-Policy["'][^>]*>\s*/gi;

/**
 * En dev (Vite + HMR), la meta CSP bloque les scripts inline injectés par @vite/client.
 * En production, on injecte une CSP stricte dans index.html.
 */
export function electronCspPlugin(): Plugin {
  return {
    name: "cyberforge-electron-csp",
    transformIndexHtml: {
      order: "pre",
      handler(html, ctx) {
        if (ctx.server) {
          return html.replace(CSP_META_RE, "\n");
        }
        const without = html.replace(CSP_META_RE, "\n");
        const meta = `    <meta http-equiv="Content-Security-Policy" content="${PRODUCTION_CSP}" />\n`;
        if (without.includes("</head>")) {
          return without.replace("</head>", `${meta}  </head>`);
        }
        return without;
      },
    },
  };
}

import { defineConfig, loadEnv, type ProxyOptions } from "vite";
import react from "@vitejs/plugin-react";
import electron from "vite-plugin-electron/simple";
import path from "node:path";
import { electronCspPlugin } from "./vite-csp-plugin";

// Monorepo : backend/.env (réel) + .env racine optionnel
const monorepoRoot = path.resolve(__dirname, "..");
const backendDir = path.join(monorepoRoot, "backend");
const DEV_PORT = 5173;
const DEFAULT_BACKEND_TARGET = "http://127.0.0.1:8002";

/** Racine backend sans slash final ni suffixe /api. */
function normalizeBackendTarget(raw: string): string {
  return raw.trim().replace(/\/+$/, "").replace(/\/api$/i, "");
}

/** Fusionne backend/.env puis .env racine (racine prioritaire). */
function loadMergedEnv(mode: string): Record<string, string> {
  return {
    ...loadEnv(mode, backendDir, ""),
    ...loadEnv(mode, monorepoRoot, ""),
  };
}

function resolveBackendProxyTarget(env: Record<string, string>): string {
  const fromVite = env.VITE_API_BASE_URL?.trim();
  if (fromVite) return normalizeBackendTarget(fromVite);

  const backendUrl = env.BACKEND_URL?.trim();
  if (backendUrl) return normalizeBackendTarget(backendUrl);

  const host = env.BACKEND_HOST?.trim() || "127.0.0.1";
  const port = env.BACKEND_PORT?.trim() || "8002";
  return `http://${host}:${port}`;
}

/** Évite une boucle proxy si VITE_API_BASE_URL pointe vers le serveur Vite. */
function sanitizeProxyTarget(raw: string): string {
  const normalized = normalizeBackendTarget(raw) || DEFAULT_BACKEND_TARGET;
  try {
    const url = new URL(normalized);
    if (url.port === String(DEV_PORT) || url.hostname === "localhost" && url.port === String(DEV_PORT)) {
      console.warn(
        `[vite] VITE_API_BASE_URL pointe vers :${DEV_PORT} — proxy forcé vers ${DEFAULT_BACKEND_TARGET}`,
      );
      return DEFAULT_BACKEND_TARGET;
    }
  } catch {
    return DEFAULT_BACKEND_TARGET;
  }
  return normalized;
}

/** Proxy dev/preview → FastAPI (routes /api/* et /cms/panel.js). */
function createDevProxy(target: string): Record<string, ProxyOptions> {
  const resolved = sanitizeProxyTarget(target);
  console.info(`[vite] Proxy API → ${resolved}`);

  const common: ProxyOptions = {
    target: resolved,
    changeOrigin: true,
    secure: false,
    ws: true,
  };

  return {
    "/api": common,
    // Panneau CMS injecté dans les HTML générés (hors préfixe /api)
    "/cms": common,
  };
}

const resolveAlias = {
  "@": path.resolve(__dirname, "src"),
  "@shared": path.resolve(__dirname, "../shared"),
};

// Configuration Vite : React côté renderer, Electron pour le processus principal
export default defineConfig(({ mode }) => {
  const env = loadMergedEnv(mode);
  const backendTarget = resolveBackendProxyTarget(env);
  const apiProxy = createDevProxy(backendTarget);

  return {
    // Charge VITE_* depuis backend/.env (fichier réel du projet)
    envDir: backendDir,
    plugins: [
      electronCspPlugin(),
      react(),
      electron({
        main: {
          entry: "electron/main.ts",
          vite: {
            resolve: { alias: resolveAlias },
            build: {
              rollupOptions: {
                external: ["electron"],
              },
            },
          },
        },
        preload: {
          input: path.join(__dirname, "electron/preload.ts"),
          vite: {
            resolve: { alias: resolveAlias },
            build: {
              rollupOptions: {
                external: ["electron"],
                output: {
                  format: "cjs",
                  entryFileNames: "preload.cjs",
                  inlineDynamicImports: true,
                },
              },
              minify: false,
            },
          },
        },
        onstart({ startup }) {
          startup();
        },
      }),
    ],
    resolve: {
      alias: resolveAlias,
    },
    server: {
      port: DEV_PORT,
      strictPort: true,
      host: true,
      proxy: apiProxy,
    },
    preview: {
      port: DEV_PORT,
      strictPort: true,
      host: true,
      proxy: apiProxy,
    },
    appType: "spa",
  };
});

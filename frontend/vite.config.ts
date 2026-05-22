import { defineConfig, loadEnv, type ProxyOptions } from "vite";
import react from "@vitejs/plugin-react";
import electron from "vite-plugin-electron/simple";
import path from "node:path";
import fs from "node:fs";
import { electronCspPlugin } from "./vite-csp-plugin";

// .env à la racine du monorepo (voir docs/ARCHITECTURE.md)
const monorepoRoot = path.resolve(__dirname, "..");
const DEV_PORT = 5173;
const DEFAULT_BACKEND_TARGET = "http://127.0.0.1:8002";

/** Racine backend sans slash final ni suffixe /api. */
function normalizeBackendTarget(raw: string): string {
  return raw.trim().replace(/\/+$/, "").replace(/\/api$/i, "");
}

function parseEnvValue(raw: string): string {
  let value = raw.trim();
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  return value;
}

/** Charge VITE_* et BACKEND_* depuis backend/.env (non couvert par envDir seul). */
function loadBackendEnv(): void {
  const envPath = path.join(monorepoRoot, "backend", ".env");
  if (!fs.existsSync(envPath)) return;
  const text = fs.readFileSync(envPath, "utf8");
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    const allowed =
      key.startsWith("VITE_") ||
      key === "BACKEND_URL" ||
      key === "BACKEND_HOST" ||
      key === "BACKEND_PORT";
    if (!allowed) continue;
    if (process.env[key] !== undefined) continue;
    process.env[key] = parseEnvValue(trimmed.slice(eq + 1));
  }
}

function resolveBackendProxyTarget(): string {
  const fromVite = process.env.VITE_API_BASE_URL?.trim();
  if (fromVite) return normalizeBackendTarget(fromVite);

  const backendUrl = process.env.BACKEND_URL?.trim();
  if (backendUrl) return normalizeBackendTarget(backendUrl);

  const host = process.env.BACKEND_HOST?.trim() || "127.0.0.1";
  const port = process.env.BACKEND_PORT?.trim() || "8002";
  return `http://${host}:${port}`;
}

/** Proxy /api → FastAPI (dev + preview). */
function createApiProxy(target: string): Record<string, ProxyOptions> {
  return {
    "/api": {
      target,
      changeOrigin: true,
      secure: false,
      ws: true,
    },
  };
}

loadBackendEnv();

const resolveAlias = {
  "@": path.resolve(__dirname, "src"),
  "@shared": path.resolve(__dirname, "../shared"),
};

// Configuration Vite : React côté renderer, Electron pour le processus principal
export default defineConfig(({ mode }) => {
  loadEnv(mode, monorepoRoot, "VITE_");
  const backendTarget = resolveBackendProxyTarget() || DEFAULT_BACKEND_TARGET;
  const apiProxy = createApiProxy(backendTarget);

  return {
    envDir: monorepoRoot,
    plugins: [
      electronCspPlugin(),
      react(),
      electron({
        main: {
          entry: "electron/main.ts",
          vite: { resolve: { alias: resolveAlias } },
        },
        preload: {
          input: path.join(__dirname, "electron/preload.ts"),
          vite: { resolve: { alias: resolveAlias } },
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

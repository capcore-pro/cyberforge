import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import electron from "vite-plugin-electron/simple";
import path from "node:path";
import fs from "node:fs";
import { electronCspPlugin } from "./vite-csp-plugin";

// .env à la racine du monorepo (voir docs/ARCHITECTURE.md)
const monorepoRoot = path.resolve(__dirname, "..");

/** Charge VITE_* depuis backend/.env pour le dev server (fichier non couvert par envDir). */
function loadBackendViteEnv(): void {
  const envPath = path.join(monorepoRoot, "backend", ".env");
  if (!fs.existsSync(envPath)) return;
  const text = fs.readFileSync(envPath, "utf8");
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    if (!key.startsWith("VITE_")) continue;
    if (process.env[key] !== undefined) continue;
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    process.env[key] = value;
  }
}

loadBackendViteEnv();

const resolveAlias = {
  "@": path.resolve(__dirname, "src"),
  "@shared": path.resolve(__dirname, "../shared"),
};

// Configuration Vite : React côté renderer, Electron pour le processus principal
export default defineConfig(({ mode }) => {
  loadEnv(mode, monorepoRoot, "VITE_");

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
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8002",
        changeOrigin: true,
      },
    },
  },
  appType: "spa",
};
});

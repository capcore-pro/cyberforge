import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import electron from "vite-plugin-electron/simple";
import path from "node:path";

// .env à la racine du monorepo (voir docs/ARCHITECTURE.md)
const monorepoRoot = path.resolve(__dirname, "..");

const resolveAlias = {
  "@": path.resolve(__dirname, "src"),
  "@shared": path.resolve(__dirname, "../shared"),
};

// Configuration Vite : React côté renderer, Electron pour le processus principal
export default defineConfig({
  envDir: monorepoRoot,
  plugins: [
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
  },
  appType: "spa",
});

import { contextBridge } from "electron";
import process from "node:process";

/**
 * Script preload — expose une API minimale au renderer via contextBridge.
 * Ne jamais y placer de clés API ni de secrets.
 */
contextBridge.exposeInMainWorld("cyberforge", {
  getVersion: () => process.versions.electron ?? "0.1.0",
  getPlatform: () => process.platform,
});

import { contextBridge, ipcRenderer } from "electron";
import process from "node:process";
import { IPC_CHANNELS } from "@shared/ipc";
import type { ApiRequestPayload, ApiResponsePayload } from "@shared/ipc";

/**
 * Script preload — expose une API minimale au renderer via contextBridge.
 * Ne jamais y placer de clés API ni de secrets.
 */
contextBridge.exposeInMainWorld("cyberforge", {
  getVersion: () => process.versions.electron ?? "0.1.0",
  getPlatform: () => process.platform,
  api: {
    request: (payload: ApiRequestPayload): Promise<ApiResponsePayload> =>
      ipcRenderer.invoke(IPC_CHANNELS.API_REQUEST, payload),
  },
});

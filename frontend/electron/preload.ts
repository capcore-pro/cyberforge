import { contextBridge, ipcRenderer } from "electron";
import { IPC_CHANNELS } from "@shared/ipc";
import type {
  ApiRequestPayload,
  ApiResponsePayload,
  PreviewOpenPayload,
} from "@shared/ipc";

/** Preload CJS : `process` est un global Node — pas `globalThis.process` (undefined en sandbox). */
function readElectronVersion(): string {
  if (typeof process !== "undefined" && process.versions?.electron) {
    return process.versions.electron;
  }
  return "0.1.0";
}

function readPlatform(): string {
  if (typeof process !== "undefined") {
    return process.platform;
  }
  return "unknown";
}

const ELECTRON_VERSION = readElectronVersion();
const PLATFORM = readPlatform();

/**
 * Script preload — expose une API minimale au renderer via contextBridge.
 * Ne jamais y placer de clés API ni de secrets.
 */
contextBridge.exposeInMainWorld("cyberforge", {
  getVersion: () => ELECTRON_VERSION,
  getPlatform: () => PLATFORM,
  api: {
    request: (payload: ApiRequestPayload): Promise<ApiResponsePayload> =>
      ipcRenderer.invoke(IPC_CHANNELS.API_REQUEST, payload),
  },
  preview: {
    open: (payload: PreviewOpenPayload): Promise<void> =>
      ipcRenderer.invoke(IPC_CHANNELS.PREVIEW_OPEN, payload),
  },
  openExternal: (url: string): Promise<void> =>
    ipcRenderer.invoke(IPC_CHANNELS.OPEN_EXTERNAL, url),
});

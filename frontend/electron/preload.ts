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
const notify = (title: string, body: string): void => {
  ipcRenderer.send(IPC_CHANNELS.NOTIFY, title, body);
};

const restartAndUpdate = (): void => {
  ipcRenderer.send(IPC_CHANNELS.RESTART_AND_UPDATE);
};

const onUpdateReady = (callback: () => void): (() => void) => {
  const listener = () => callback();
  ipcRenderer.on(IPC_CHANNELS.UPDATE_READY, listener);
  return () => ipcRenderer.removeListener(IPC_CHANNELS.UPDATE_READY, listener);
};

const checkForUpdates = (): Promise<void> =>
  ipcRenderer.invoke(IPC_CHANNELS.CHECK_FOR_UPDATES);

const onUpdateStatus = (
  callback: (data: {
    status: "checking" | "up-to-date" | "downloading" | "ready" | "error";
    version?: string;
    message?: string;
  }) => void,
): (() => void) => {
  const listener = (_: unknown, data: unknown) => {
    callback(data as Parameters<typeof callback>[0]);
  };
  ipcRenderer.on(IPC_CHANNELS.UPDATE_STATUS, listener);
  return () => ipcRenderer.removeListener(IPC_CHANNELS.UPDATE_STATUS, listener);
};

const onDownloadProgress = (
  callback: (data: { percent: number; transferred: number; total: number }) => void,
): (() => void) => {
  const listener = (_: unknown, data: unknown) => {
    callback(data as Parameters<typeof callback>[0]);
  };
  ipcRenderer.on(IPC_CHANNELS.DOWNLOAD_PROGRESS, listener);
  return () => ipcRenderer.removeListener(IPC_CHANNELS.DOWNLOAD_PROGRESS, listener);
};

const restartBackend = (): Promise<{ ok: boolean }> =>
  ipcRenderer.invoke(IPC_CHANNELS.RESTART_BACKEND);

const onBackendStatus = (
  callback: (data: {
    status: "starting" | "online" | "offline" | "error";
    pid?: number;
    code?: number;
    message?: string;
  }) => void,
): (() => void) => {
  const listener = (_: unknown, data: unknown) => {
    callback(data as Parameters<typeof callback>[0]);
  };
  ipcRenderer.on(IPC_CHANNELS.BACKEND_STATUS, listener);
  return () => ipcRenderer.removeListener(IPC_CHANNELS.BACKEND_STATUS, listener);
};

const onBackendLog = (callback: (log: string) => void): (() => void) => {
  const listener = (_: unknown, log: string) => callback(log);
  ipcRenderer.on(IPC_CHANNELS.BACKEND_LOG, listener);
  return () => ipcRenderer.removeListener(IPC_CHANNELS.BACKEND_LOG, listener);
};

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
  notify,
  restartAndUpdate,
  onUpdateReady,
  checkForUpdates,
  onUpdateStatus,
  onDownloadProgress,
  restartBackend,
  onBackendStatus,
  onBackendLog,
});

contextBridge.exposeInMainWorld("electronAPI", {
  notify,
  restartAndUpdate,
  onUpdateReady,
  checkForUpdates,
  onUpdateStatus,
  onDownloadProgress,
  restartBackend,
  onBackendStatus,
  onBackendLog,
});

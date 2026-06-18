/// <reference types="vite/client" />

import type {
  ApiRequestPayload,
  ApiResponsePayload,
  PreviewOpenPayload,
} from "@shared/ipc";

// Variables d'environnement exposées au renderer (préfixe VITE_)
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// API IPC exposée par le preload Electron
declare global {
  interface Window {
    cyberforge?: {
      getVersion: () => string;
      getPlatform: () => string;
      api?: {
        request: (payload: ApiRequestPayload) => Promise<ApiResponsePayload>;
      };
      preview?: {
        open: (payload: PreviewOpenPayload) => Promise<void>;
      };
      openExternal?: (url: string) => Promise<void>;
      notify?: (title: string, body: string) => void;
      restartAndUpdate?: () => void;
      onUpdateReady?: (callback: () => void) => () => void;
      checkForUpdates?: () => Promise<void>;
      onUpdateStatus?: (
        callback: (data: {
          status: "checking" | "up-to-date" | "downloading" | "ready" | "error";
          version?: string;
          message?: string;
        }) => void,
      ) => () => void;
      onDownloadProgress?: (
        callback: (data: {
          percent: number;
          transferred: number;
          total: number;
        }) => void,
      ) => () => void;
      restartBackend?: () => Promise<{ ok: boolean }>;
      onBackendStatus?: (
        callback: (data: {
          status: "starting" | "online" | "offline" | "error";
          pid?: number;
          code?: number;
          message?: string;
        }) => void,
      ) => () => void;
      onBackendLog?: (callback: (log: string) => void) => () => void;
    };
    electronAPI?: {
      notify?: (title: string, body: string) => void;
      restartAndUpdate?: () => void;
      onUpdateReady?: (callback: () => void) => () => void;
      checkForUpdates?: () => Promise<void>;
      onUpdateStatus?: (
        callback: (data: {
          status: "checking" | "up-to-date" | "downloading" | "ready" | "error";
          version?: string;
          message?: string;
        }) => void,
      ) => () => void;
      onDownloadProgress?: (
        callback: (data: {
          percent: number;
          transferred: number;
          total: number;
        }) => void,
      ) => () => void;
      restartBackend?: () => Promise<{ ok: boolean }>;
      onBackendStatus?: (
        callback: (data: {
          status: "starting" | "online" | "offline" | "error";
          pid?: number;
          code?: number;
          message?: string;
        }) => void,
      ) => () => void;
      onBackendLog?: (callback: (log: string) => void) => () => void;
    };
  }
}

export {};

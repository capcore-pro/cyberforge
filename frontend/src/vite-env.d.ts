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
    };
  }
}

export {};

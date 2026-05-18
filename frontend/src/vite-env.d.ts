/// <reference types="vite/client" />

// Variables d'environnement exposées au renderer (préfixe VITE_)
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// API IPC exposée par le preload Electron
interface Window {
  cyberforge?: {
    getVersion: () => string;
    getPlatform: () => string;
  };
}

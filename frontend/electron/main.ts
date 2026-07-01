import "./load-env.js";
import { app, BrowserWindow, ipcMain, session, shell } from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { setupAutoUpdater } from "./auto-updater";
import {
  isBackendProcessRunning,
  registerBackendIpc,
  startBackend,
  stopBackend,
} from "./backend-process";
import { registerIpcHandlers } from "./ipc-handlers";
import { getAppVersion } from "./app-version.js";
import { IPC_CHANNELS } from "@shared/ipc";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const HEALTH_URL = "http://127.0.0.1:8002/api/health";
const HEALTH_POLL_INTERVAL_MS = 300;
const HEALTH_MAX_WAIT_MS = 30_000;
const SPLASH_FADE_MS = 400;

const SPLASH_WIDTH = 960;
const SPLASH_HEIGHT = 600;

let mainWindow: BrowserWindow | null = null;
let splashWindow: BrowserWindow | null = null;
let mainReadyToShow = false;
let isQuitting = false;

const isDev = !app.isPackaged;
const useSplash = app.isPackaged;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pingBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(HEALTH_URL, {
      signal: AbortSignal.timeout(2_000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

async function waitForBackendHealth(): Promise<boolean> {
  const started = Date.now();
  while (Date.now() - started < HEALTH_MAX_WAIT_MS) {
    if (await pingBackendHealth()) {
      return true;
    }
    await sleep(HEALTH_POLL_INTERVAL_MS);
  }
  return false;
}

function createSplashWindow(): void {
  splashWindow = new BrowserWindow({
    width: SPLASH_WIDTH,
    height: SPLASH_HEIGHT,
    center: true,
    frame: false,
    resizable: false,
    movable: true,
    show: false,
    backgroundColor: "#030308",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  void splashWindow.loadFile(path.join(__dirname, "splash.html"));

  splashWindow.on("closed", () => {
    splashWindow = null;
  });
}

async function closeSplashWithFade(): Promise<void> {
  const win = splashWindow;
  if (!win || win.isDestroyed()) {
    splashWindow = null;
    return;
  }

  try {
    await win.webContents.executeJavaScript(
      `document.documentElement.classList.add('fade-out')`,
      true,
    );
  } catch {
    /* fenêtre déjà détruite */
  }

  await sleep(SPLASH_FADE_MS);

  if (!win.isDestroyed()) {
    win.destroy();
  }
  splashWindow = null;
}

function revealMainWindow(): void {
  if (!mainWindow || mainWindow.isDestroyed()) return;

  const show = () => {
    if (mainWindow && !mainWindow.isDestroyed() && !mainWindow.isVisible()) {
      mainWindow.show();
    }
  };

  if (mainReadyToShow) {
    show();
  } else {
    mainWindow.once("ready-to-show", show);
  }
}

function createWindow(deferShow: boolean): void {
  mainReadyToShow = false;

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: "CyberForge",
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.cjs"),
    },
  });

  if (deferShow) {
    mainWindow.once("ready-to-show", () => {
      mainReadyToShow = true;
    });
  } else {
    mainWindow.once("ready-to-show", () => {
      mainWindow?.show();
    });
  }

  if (isDev && process.env.VITE_DEV_SERVER_URL) {
    void mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    void mainWindow.loadFile(path.join(__dirname, "../dist/index.html"));
  }

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("https:") || url.startsWith("http:")) {
      void shell.openExternal(url);
    }
    return { action: "deny" };
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
    mainReadyToShow = false;
  });
}

async function bootstrap(): Promise<void> {
  if (useSplash) {
    createSplashWindow();
    splashWindow?.show();
  }

  createWindow(useSplash);
  startBackend(() => mainWindow);

  if (useSplash) {
    const healthy = await waitForBackendHealth();
    if (!healthy) {
      console.warn(
        "[splash] Backend health timeout après 30s — ouverture avec bandeau offline",
      );
    }
    await closeSplashWithFade();
    revealMainWindow();
  }

  if (!isDev) {
    setupAutoUpdater(() => mainWindow);
  }
}

app.whenReady().then(() => {
  console.log("app.getVersion():", app.getVersion());
  console.log("getAppVersion():", getAppVersion());
  console.log("__dirname:", __dirname);

  if (isDev) {
    session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
      const headers = { ...details.responseHeaders };
      for (const key of Object.keys(headers)) {
        if (key.toLowerCase() === "content-security-policy") {
          delete headers[key];
        }
      }
      callback({ responseHeaders: headers });
    });
  }

  registerIpcHandlers();
  ipcMain.handle(IPC_CHANNELS.GET_VERSION, () => getAppVersion());
  registerBackendIpc(() => mainWindow);

  void bootstrap();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow(false);
      startBackend(() => mainWindow);
    }
  });
});

app.on("before-quit", (event) => {
  if (isQuitting || !isBackendProcessRunning()) return;
  event.preventDefault();
  isQuitting = true;
  void stopBackend().then(() => {
    app.quit();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

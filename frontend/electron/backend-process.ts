import { spawn, type ChildProcess } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { app, ipcMain, type BrowserWindow } from "electron";
import { IPC_CHANNELS } from "@shared/ipc";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const monorepoRoot = path.resolve(__dirname, "../..");

let backendProcess: ChildProcess | null = null;

function getBackendConfig() {
  const isDev = !app.isPackaged;

  if (isDev) {
    const venvPython =
      process.platform === "win32"
        ? path.join(monorepoRoot, "backend", ".venv-py311-backup", "Scripts", "python.exe")
        : path.join(monorepoRoot, "backend", ".venv", "bin", "python");
    return {
      python: venvPython,
      cwd: path.join(monorepoRoot, "backend"),
    };
  }

  const venvPython =
    process.platform === "win32"
      ? path.join(
          process.resourcesPath,
          "backend",
          ".venv-py311-backup",
          "Scripts",
          "python.exe",
        )
      : path.join(process.resourcesPath, "backend", ".venv", "bin", "python");
  return {
    python: venvPython,
    cwd: path.join(process.resourcesPath, "backend"),
  };
}

export function isBackendProcessRunning(): boolean {
  return backendProcess !== null;
}

export function startBackend(getMainWindow: () => BrowserWindow | null): void {
  if (backendProcess) return;

  const { python, cwd } = getBackendConfig();
  const send = (channel: string, data?: unknown) => {
    getMainWindow()?.webContents.send(channel, data);
  };

  send(IPC_CHANNELS.BACKEND_STATUS, { status: "starting" });

  backendProcess = spawn(
    python,
    ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8002"],
    { cwd, stdio: ["ignore", "pipe", "pipe"] },
  );

  const proc = backendProcess;

  proc.stdout?.on("data", (data: Buffer) => {
    const log = data.toString().trim();
    if (log) send(IPC_CHANNELS.BACKEND_LOG, log);
    if (log.includes("Application startup complete")) {
      send(IPC_CHANNELS.BACKEND_STATUS, { status: "online", pid: proc.pid });
    }
  });

  proc.stderr?.on("data", (data: Buffer) => {
    const log = data.toString().trim();
    if (!log) return;
    send(IPC_CHANNELS.BACKEND_LOG, log);

    const isPortBusy =
      log.includes("address already in use") ||
      log.includes("Only one usage of each socket") ||
      log.includes("EADDRINUSE") ||
      log.includes("error while attempting to bind");

    if (isPortBusy) {
      send(IPC_CHANNELS.BACKEND_STATUS, {
        status: "error",
        message: "Port 8002 déjà occupé. Un backend tourne peut-être déjà.",
      });
    }
  });

  proc.on("exit", (code) => {
    if (backendProcess === proc) {
      backendProcess = null;
    }
    send(IPC_CHANNELS.BACKEND_STATUS, { status: "offline", code });
  });

  proc.on("error", (err) => {
    if (backendProcess === proc) {
      backendProcess = null;
    }
    send(IPC_CHANNELS.BACKEND_STATUS, { status: "error", message: err.message });
  });
}

export function stopBackend(): Promise<void> {
  return new Promise((resolve) => {
    if (!backendProcess) {
      resolve();
      return;
    }

    const proc = backendProcess;

    const finish = () => {
      if (backendProcess === proc) {
        backendProcess = null;
      }
      resolve();
    };

    proc.once("exit", finish);

    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(proc.pid), "/f", "/t"]);
    } else {
      proc.kill("SIGTERM");
    }

    setTimeout(finish, 2000);
  });
}

export function registerBackendIpc(getMainWindow: () => BrowserWindow | null): void {
  ipcMain.handle(IPC_CHANNELS.RESTART_BACKEND, async () => {
    await stopBackend();
    await new Promise((r) => setTimeout(r, 1000));
    startBackend(getMainWindow);
    return { ok: true };
  });
}

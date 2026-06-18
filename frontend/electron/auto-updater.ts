import { Notification, ipcMain, type BrowserWindow } from "electron";
import pkg from "electron-updater";
import { IPC_CHANNELS } from "@shared/ipc";

const { autoUpdater } = pkg;

export function setupAutoUpdater(
  getMainWindow: () => BrowserWindow | null,
): void {
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;
  autoUpdater.logger = null;

  const send = (channel: string, data?: unknown) => {
    getMainWindow()?.webContents.send(channel, data);
  };

  autoUpdater.on("update-available", (info) => {
    new Notification({
      title: "CyberForge — Mise à jour disponible",
      body: `Version ${info.version} — Téléchargement en cours...`,
    }).show();
    send(IPC_CHANNELS.UPDATE_STATUS, {
      status: "downloading",
      version: info.version,
    });
  });

  autoUpdater.on("update-not-available", (info) => {
    send(IPC_CHANNELS.UPDATE_STATUS, {
      status: "up-to-date",
      version: info.version,
    });
  });

  autoUpdater.on("download-progress", (progress) => {
    send(IPC_CHANNELS.DOWNLOAD_PROGRESS, {
      percent: Math.round(progress.percent),
      transferred: progress.transferred,
      total: progress.total,
    });
  });

  autoUpdater.on("update-downloaded", (info) => {
    new Notification({
      title: "CyberForge — Prêt à installer",
      body: `Version ${info.version} — Redémarre pour appliquer.`,
    }).show();
    send(IPC_CHANNELS.UPDATE_STATUS, { status: "ready", version: info.version });
    send(IPC_CHANNELS.UPDATE_READY);
  });

  autoUpdater.on("error", (err) => {
    send(IPC_CHANNELS.UPDATE_STATUS, {
      status: "error",
      message: err.message,
    });
  });

  ipcMain.handle(IPC_CHANNELS.CHECK_FOR_UPDATES, async () => {
    try {
      send(IPC_CHANNELS.UPDATE_STATUS, { status: "checking" });
      await autoUpdater.checkForUpdates();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      send(IPC_CHANNELS.UPDATE_STATUS, { status: "error", message });
    }
  });

  ipcMain.on(IPC_CHANNELS.RESTART_AND_UPDATE, () => {
    autoUpdater.quitAndInstall();
  });

  void autoUpdater.checkForUpdatesAndNotify();
}

import { Notification, ipcMain, type BrowserWindow } from "electron";
import { autoUpdater } from "electron-updater";
import { IPC_CHANNELS } from "@shared/ipc";

/** Active les mises à jour automatiques via GitHub Releases (production uniquement). */
export function setupAutoUpdater(
  getMainWindow: () => BrowserWindow | null,
): void {
  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on("update-available", () => {
    new Notification({
      title: "CyberForge — Mise à jour disponible",
      body: "Téléchargement en cours...",
    }).show();
  });

  autoUpdater.on("update-downloaded", () => {
    new Notification({
      title: "CyberForge — Prêt à installer",
      body: "Redémarre CyberForge pour appliquer la mise à jour.",
    }).show();

    getMainWindow()?.webContents.send(IPC_CHANNELS.UPDATE_READY);
  });

  ipcMain.on(IPC_CHANNELS.RESTART_AND_UPDATE, () => {
    autoUpdater.quitAndInstall();
  });

  void autoUpdater.checkForUpdatesAndNotify();
}

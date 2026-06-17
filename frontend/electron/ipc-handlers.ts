import { ipcMain, Notification, shell } from "electron";
import {
  IPC_CHANNELS,
  type ApiRequestPayload,
  type PreviewOpenPayload,
} from "@shared/ipc";
import { proxyApiRequest } from "./api-proxy";
import { openPreviewWindow } from "./preview-window";

/** Enregistre les handlers IPC du processus principal. */
export function registerIpcHandlers(): void {
  ipcMain.handle(
    IPC_CHANNELS.API_REQUEST,
    async (_event, payload: ApiRequestPayload) => {
      return proxyApiRequest(payload);
    },
  );

  ipcMain.handle(
    IPC_CHANNELS.PREVIEW_OPEN,
    async (_event, payload: PreviewOpenPayload) => {
      await openPreviewWindow(payload);
    },
  );

  ipcMain.handle(IPC_CHANNELS.OPEN_EXTERNAL, async (_event, url: string) => {
    const target = (url || "").trim();
    if (
      target.startsWith("https:") ||
      target.startsWith("http:") ||
      target.startsWith("mailto:") ||
      target.startsWith("tel:")
    ) {
      await shell.openExternal(target);
    }
  });

  ipcMain.on(
    IPC_CHANNELS.NOTIFY,
    (_event, title: unknown, body: unknown) => {
      const notificationTitle =
        typeof title === "string" && title.trim() ? title.trim() : "CyberForge";
      const notificationBody = typeof body === "string" ? body : "";
      new Notification({
        title: notificationTitle,
        body: notificationBody,
      }).show();
    },
  );
}

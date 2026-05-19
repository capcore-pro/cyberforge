import { ipcMain } from "electron";
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
}

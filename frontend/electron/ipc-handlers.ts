import { ipcMain } from "electron";
import { IPC_CHANNELS, type ApiRequestPayload } from "@shared/ipc";
import { proxyApiRequest } from "./api-proxy";

/** Enregistre les handlers IPC du processus principal. */
export function registerIpcHandlers(): void {
  ipcMain.handle(
    IPC_CHANNELS.API_REQUEST,
    async (_event, payload: ApiRequestPayload) => {
      return proxyApiRequest(payload);
    },
  );
}

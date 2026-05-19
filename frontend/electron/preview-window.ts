import { BrowserWindow } from "electron";
import { writeFile } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import type { PreviewOpenPayload } from "@shared/ipc";

let previewWindow: BrowserWindow | null = null;

/** Ouvre ou remplace une fenêtre de prévisualisation HTML. */
export async function openPreviewWindow(payload: PreviewOpenPayload): Promise<void> {
  if (previewWindow && !previewWindow.isDestroyed()) {
    previewWindow.close();
    previewWindow = null;
  }

  const filePath = join(
    tmpdir(),
    `cyberforge-preview-${Date.now()}.html`,
  );
  await writeFile(filePath, payload.html, "utf-8");

  previewWindow = new BrowserWindow({
    width: 1024,
    height: 720,
    minWidth: 480,
    minHeight: 360,
    title: payload.title ?? "Prévisualisation CyberForge",
    autoHideMenuBar: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  });

  previewWindow.on("closed", () => {
    previewWindow = null;
  });

  await previewWindow.loadFile(filePath);
}

import { BrowserWindow, shell } from "electron";
import { writeFile } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
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

  previewWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (
      url.startsWith("https:") ||
      url.startsWith("http:") ||
      url.startsWith("mailto:") ||
      url.startsWith("tel:")
    ) {
      void shell.openExternal(url);
    }
    return { action: "deny" };
  });

  previewWindow.webContents.on("will-navigate", (event, url) => {
    const current = previewWindow?.webContents.getURL() ?? "";
    if (!current || url === current) {
      return;
    }
    if (url.startsWith("file:") && url.split("#")[0] === current.split("#")[0]) {
      return;
    }
    event.preventDefault();
    if (
      url.startsWith("https:") ||
      url.startsWith("http:") ||
      url.startsWith("mailto:") ||
      url.startsWith("tel:")
    ) {
      void shell.openExternal(url);
    }
  });

  const fileUrl = pathToFileURL(filePath);
  fileUrl.searchParams.set("preview", "cyberforge_internal");
  await previewWindow.loadURL(fileUrl.toString());
}

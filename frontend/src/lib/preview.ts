import type { PreviewOpenPayload } from "@shared/ipc";
import { buildPreviewDocument, type PreviewSourceFile } from "@/lib/preview-html";

/** Ouvre la prévisualisation (fenêtre Electron ou iframe via callback). */
export async function openCodePreview(
  files: PreviewSourceFile[],
  options: {
    title?: string;
    onIframe: (html: string) => void;
  },
): Promise<void> {
  const html = buildPreviewDocument(files);
  const payload: PreviewOpenPayload = {
    html,
    title: options.title ?? "Prévisualisation CyberForge",
  };

  if (typeof window.cyberforge?.preview?.open === "function") {
    await window.cyberforge.preview.open(payload);
    return;
  }

  options.onIframe(html);
}

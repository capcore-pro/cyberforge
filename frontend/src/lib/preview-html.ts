import {
  buildMockupPreviewHtml,
  extractPreviewMockup,
  escapeHtml,
} from "@/lib/preview-mockup";

/** Fichier source pour la prévisualisation. */
export interface PreviewSourceFile {
  path: string;
  content: string;
}

/**
 * Construit un document HTML statique pour iframe / fenêtre Electron.
 * Le TSX/React est converti en maquette visuelle (titre, sections, couleurs).
 */
export function buildPreviewDocument(files: PreviewSourceFile[]): string {
  if (files.length === 0) {
    return _emptyPreviewHtml("Aucun fichier à prévisualiser.");
  }

  const htmlFile = files.find((f) => /\.html?$/i.test(f.path));
  if (htmlFile && _isCompleteHtml(htmlFile.content)) {
    return htmlFile.content;
  }

  const sources = files
    .filter((f) => /\.(tsx|jsx|ts|js|css)$/i.test(f.path))
    .map((f) => f.content)
    .join("\n\n");

  const mockup = extractPreviewMockup(sources || files[0].content);
  return buildMockupPreviewHtml(mockup);
}

function _isCompleteHtml(content: string): boolean {
  const lower = content.trim().toLowerCase();
  return lower.includes("<html") && lower.includes("<body");
}

function _emptyPreviewHtml(message: string): string {
  return `<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><style>body{font-family:system-ui;background:#0a0a0f;color:#f87171;padding:2rem;}</style></head><body><p>${escapeHtml(message)}</p></body></html>`;
}

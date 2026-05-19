import { zipSync } from "fflate";

export interface ExportableFile {
  path: string;
  content: string;
}

/** Télécharge les fichiers générés sous forme d'archive ZIP. */
export function downloadProjectZip(
  files: ExportableFile[],
  archiveName = "cyberforge-export.zip",
): void {
  if (files.length === 0) {
    throw new Error("Aucun fichier à exporter.");
  }

  const archive: Record<string, Uint8Array> = {};
  for (const file of files) {
    const path = file.path.replace(/^\/+/, "");
    archive[path] = new TextEncoder().encode(file.content);
  }

  const zipped = zipSync(archive);
  const blob = new Blob([zipped], { type: "application/zip" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = archiveName;
  anchor.click();
  URL.revokeObjectURL(url);
}

/** Copie du texte dans le presse-papiers. */
export async function copyTextToClipboard(text: string): Promise<void> {
  if (!text.trim()) {
    throw new Error("Rien à copier.");
  }
  await navigator.clipboard.writeText(text);
}

/** Nom d'archive dérivé du prompt. */
export function zipFilenameFromPrompt(prompt: string): string {
  const slug = prompt
    .trim()
    .toLowerCase()
    .slice(0, 40)
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  const stamp = new Date().toISOString().slice(0, 10);
  return `cyberforge-${slug || "projet"}-${stamp}.zip`;
}

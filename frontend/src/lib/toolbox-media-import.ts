import type { ApiResponsePayload } from "@shared/ipc";
import { uploadMediaAsset, type MediaAsset } from "@/lib/media-api";

async function fetchAsFile(url: string, filename: string, mime: string): Promise<File> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Téléchargement impossible (${response.status})`);
  }
  const blob = await response.blob();
  const type = blob.type && blob.type !== "application/octet-stream" ? blob.type : mime;
  return new File([blob], filename, { type });
}

/** Convertit une URL SVG Iconify / unDraw en PNG pour la médiathèque. */
async function svgUrlToPngFile(svgUrl: string, filename: string): Promise<File> {
  const response = await fetch(svgUrl);
  if (!response.ok) {
    throw new Error(`SVG inaccessible (${response.status})`);
  }
  const svgText = await response.text();
  const objectUrl = URL.createObjectURL(new Blob([svgText], { type: "image/svg+xml" }));

  try {
    const img = await new Promise<HTMLImageElement>((resolve, reject) => {
      const el = new Image();
      el.onload = () => resolve(el);
      el.onerror = () => reject(new Error("SVG illisible"));
      el.src = objectUrl;
    });

    const size = 512;
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      throw new Error("Canvas indisponible");
    }
    ctx.fillStyle = "#0D0D0D";
    ctx.fillRect(0, 0, size, size);
    const scale = Math.min(size / img.width, size / img.height) * 0.85;
    const w = img.width * scale;
    const h = img.height * scale;
    ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h);

    const pngBlob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Export PNG impossible"))), "image/png");
    });
    return new File([pngBlob], filename.replace(/\.svg$/i, ".png"), { type: "image/png" });
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

export async function importToolboxPhotoToMedia(
  photo: { url_full: string; id: string; source: string },
  tags: string,
): Promise<ApiResponsePayload<MediaAsset>> {
  const ext = photo.url_full.includes(".png") ? "png" : "jpg";
  const file = await fetchAsFile(
    photo.url_full,
    `toolbox-${photo.source}-${photo.id}.${ext}`,
    ext === "png" ? "image/png" : "image/jpeg",
  );
  return uploadMediaAsset(file, { tags });
}

export async function importToolboxSvgToMedia(
  svgUrl: string,
  filename: string,
  tags: string,
): Promise<ApiResponsePayload<MediaAsset>> {
  const file = await svgUrlToPngFile(svgUrl, filename);
  return uploadMediaAsset(file, { tags });
}

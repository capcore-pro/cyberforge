export type PreviewDeviceType = "mobile" | "tablet" | "desktop";

export interface PreviewDeviceSpec {
  width: number;
  height: number;
  label: string;
  shortLabel: string;
}

export const PREVIEW_DEVICE_SPECS: Record<PreviewDeviceType, PreviewDeviceSpec> = {
  mobile: {
    width: 375,
    height: 812,
    label: "Mobile",
    shortLabel: "📱 Mobile",
  },
  tablet: {
    width: 768,
    height: 1024,
    label: "Tablette",
    shortLabel: "💻 Tablette",
  },
  desktop: {
    width: 1280,
    height: 800,
    label: "Desktop",
    shortLabel: "🖥️ Desktop",
  },
};

export const PREVIEW_DEVICE_ORDER: PreviewDeviceType[] = [
  "mobile",
  "tablet",
  "desktop",
];

export function previewDeviceFrameRadius(device: PreviewDeviceType): number {
  if (device === "mobile") return 40;
  if (device === "tablet") return 20;
  return 8;
}

export function previewDeviceChromeHeight(device: PreviewDeviceType): number {
  if (device === "mobile") return 48;
  if (device === "tablet") return 24;
  return 36;
}

export function computePreviewDeviceScale(
  device: PreviewDeviceType,
  containerWidth: number,
  containerHeight: number,
): number {
  const spec = PREVIEW_DEVICE_SPECS[device];
  const framePad = device === "mobile" ? 12 : device === "tablet" ? 8 : 0;
  const chrome = previewDeviceChromeHeight(device);
  const totalW = spec.width + framePad * 2;
  const totalH = spec.height + chrome + framePad * 2;
  const availW = Math.max(containerWidth - 32, 100);
  const availH = Math.max(containerHeight - 32, 100);
  return Math.min(1, availW / totalW, availH / totalH);
}

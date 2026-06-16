import { useEffect, useMemo, useRef, useState } from "react";
import {
  PREVIEW_DEVICE_SPECS,
  computePreviewDeviceScale,
  previewDeviceFrameRadius,
  type PreviewDeviceType,
} from "@/lib/preview-devices";

interface PreviewDeviceProps {
  html: string;
  device: PreviewDeviceType;
  className?: string;
}

export function PreviewDevice({ html, device, className }: PreviewDeviceProps) {
  const spec = PREVIEW_DEVICE_SPECS[device];
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  const blobUrl = useMemo(() => {
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    return URL.createObjectURL(blob);
  }, [html]);

  useEffect(() => {
    return () => {
      URL.revokeObjectURL(blobUrl);
    };
  }, [blobUrl]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const update = () => {
      setScale(
        computePreviewDeviceScale(device, el.clientWidth, el.clientHeight),
      );
    };

    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [device]);

  const frameRadius = previewDeviceFrameRadius(device);
  const framePad = device === "mobile" ? 12 : device === "tablet" ? 8 : 0;
  const iframeRadius =
    device === "mobile" ? 28 : device === "tablet" ? 12 : "0 0 8px 8px";

  return (
    <div
      ref={containerRef}
      className={`flex min-h-[60vh] items-center justify-center bg-[#0a0a0a] p-4 ${className ?? ""}`}
      data-testid="preview-device-container"
    >
      <div
        style={{
          transform: `scale(${scale})`,
          transformOrigin: "center center",
        }}
        data-testid="preview-device-scaler"
        data-scale={scale}
      >
        <div
          className="relative bg-black shadow-2xl"
          style={{
            width: spec.width + framePad * 2,
            borderRadius: frameRadius,
            padding: framePad,
          }}
          data-testid={`preview-device-frame-${device}`}
          data-frame-radius={frameRadius}
          data-device-width={spec.width}
        >
          {device === "mobile" ? (
            <div
              className="pointer-events-none absolute left-1/2 top-3 z-10 h-5 w-24 -translate-x-1/2 rounded-full bg-black"
              aria-hidden
              data-testid="preview-device-notch"
            />
          ) : null}

          {device === "desktop" ? (
            <div
              className="flex items-center gap-1.5 border-b border-white/10 px-3 py-2"
              data-testid="preview-desktop-titlebar"
            >
              <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
              <span className="h-2.5 w-2.5 rounded-full bg-yellow-400" />
              <span className="h-2.5 w-2.5 rounded-full bg-green-500" />
            </div>
          ) : null}

          <iframe
            title={`Aperçu ${spec.label}`}
            src={blobUrl}
            className="block border-0 bg-white"
            style={{
              width: spec.width,
              height: spec.height,
              borderRadius: iframeRadius,
              pointerEvents: "none",
            }}
            sandbox="allow-scripts allow-same-origin"
            data-testid="preview-device-iframe"
          />
        </div>
      </div>
    </div>
  );
}

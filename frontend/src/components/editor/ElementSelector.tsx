import { useEffect, useMemo, useRef } from "react";
import { injectEditorScript } from "@/lib/editor-inject";
import {
  PREVIEW_DEVICE_SPECS,
  type PreviewDeviceType,
} from "@/lib/preview-devices";

interface ElementSelectorProps {
  html: string;
  viewport: PreviewDeviceType;
  className?: string;
}

export function ElementSelector({ html, viewport, className }: ElementSelectorProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const spec = PREVIEW_DEVICE_SPECS[viewport];

  const blobUrl = useMemo(() => {
    const enriched = injectEditorScript(html);
    const blob = new Blob([enriched], { type: "text/html;charset=utf-8" });
    return URL.createObjectURL(blob);
  }, [html]);

  useEffect(() => {
    return () => {
      URL.revokeObjectURL(blobUrl);
    };
  }, [blobUrl]);

  const width = viewport === "desktop" ? "100%" : `${spec.width}px`;
  const maxWidth = viewport === "desktop" ? "100%" : `${spec.width}px`;

  return (
    <div
      className={`relative flex h-full justify-center overflow-auto bg-[#0a0a0a] ${className ?? ""}`}
      data-testid="element-selector-viewport"
      data-viewport={viewport}
      data-viewport-width={spec.width}
    >
      <iframe
        ref={iframeRef}
        title="Aperçu éditable"
        src={blobUrl}
        className="h-full border-0 bg-white shadow-2xl transition-all duration-300"
        style={{
          width,
          maxWidth,
          minWidth: viewport === "desktop" ? undefined : spec.width,
        }}
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  );
}

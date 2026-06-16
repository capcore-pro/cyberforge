import { useEffect, useMemo, useRef } from "react";
import { injectEditorScript } from "@/lib/editor-inject";

interface ElementSelectorProps {
  html: string;
  viewport: "desktop" | "mobile";
  className?: string;
}

export function ElementSelector({ html, viewport, className }: ElementSelectorProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

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

  const width = viewport === "mobile" ? "390px" : "100%";

  return (
    <div className={`relative flex h-full justify-center bg-[#0a0a0a] ${className ?? ""}`}>
      <iframe
        ref={iframeRef}
        title="Aperçu éditable"
        src={blobUrl}
        className="h-full border-0 bg-white shadow-2xl transition-all duration-300"
        style={{ width, maxWidth: "100%" }}
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  );
}

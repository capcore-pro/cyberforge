import type { SelectedElementPayload } from "@/lib/editor-inject";
import { ColorPanel } from "./panels/ColorPanel";
import { DefaultPanel } from "./panels/DefaultPanel";
import { ImagePanel, LogoPanel } from "./panels/ImagePanel";
import { SectionPanel } from "./panels/SectionPanel";
import { TextPanel } from "./panels/TextPanel";

const TEXT_TAGS = new Set(["P", "H1", "H2", "H3", "H4", "H5", "H6", "SPAN", "LI", "BUTTON", "A"]);
const SECTION_TAGS = new Set(["SECTION", "DIV", "ARTICLE", "MAIN", "HEADER", "FOOTER", "NAV"]);

function isLogoContext(el: SelectedElementPayload): boolean {
  const cls = el.className.toLowerCase();
  return (
    el.tagName === "IMG" &&
    (cls.includes("logo") || cls.includes("brand") || el.xpath.includes("header"))
  );
}

interface EditorToolsPanelProps {
  projectId: string;
  selected: SelectedElementPayload | null;
  swatches: string[];
  onTextApply: (xpath: string, changes: { textContent: string; style?: Record<string, string> }) => void;
  onImageReplace: (xpath: string, src: string, alt?: string) => void;
  onColorApply: (xpath: string, style: Record<string, string>) => void;
  onGlobalColor: (oldColor: string, newColor: string) => void;
  onMove: (xpath: string, direction: "up" | "down") => void;
  onDuplicate: (xpath: string) => void;
  onDelete: (xpath: string) => void;
  onToggleVisibility: (xpath: string, hidden: boolean) => void;
}

export function EditorToolsPanel({
  projectId,
  selected,
  swatches,
  onTextApply,
  onImageReplace,
  onColorApply,
  onGlobalColor,
  onMove,
  onDuplicate,
  onDelete,
  onToggleVisibility,
}: EditorToolsPanelProps) {
  if (!selected) {
    return <DefaultPanel />;
  }

  if (selected.tagName === "IMG") {
    if (isLogoContext(selected)) {
      return (
        <LogoPanel
          projectId={projectId}
          element={selected}
          onReplace={(src, alt) => onImageReplace(selected.xpath, src, alt)}
        />
      );
    }
    return (
      <ImagePanel
        projectId={projectId}
        element={selected}
        onReplace={(src, alt) => onImageReplace(selected.xpath, src, alt)}
      />
    );
  }

  if (TEXT_TAGS.has(selected.tagName)) {
    return (
      <TextPanel
        element={selected}
        onApply={(changes) => onTextApply(selected.xpath, changes)}
      />
    );
  }

  if (SECTION_TAGS.has(selected.tagName)) {
    return (
      <div className="space-y-6">
        <SectionPanel
          element={selected}
          onMove={(dir) => onMove(selected.xpath, dir)}
          onDuplicate={() => onDuplicate(selected.xpath)}
          onDelete={() => onDelete(selected.xpath)}
          onToggleVisibility={(hidden) => onToggleVisibility(selected.xpath, hidden)}
        />
        <ColorPanel
          element={selected}
          swatches={swatches}
          onApply={(style) => onColorApply(selected.xpath, style)}
          onGlobalColor={onGlobalColor}
        />
      </div>
    );
  }

  return (
    <ColorPanel
      element={selected}
      swatches={swatches}
      onApply={(style) => onColorApply(selected.xpath, style)}
      onGlobalColor={onGlobalColor}
    />
  );
}

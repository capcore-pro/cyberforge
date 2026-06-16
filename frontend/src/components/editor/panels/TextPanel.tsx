import { useEffect, useState } from "react";
import { Button } from "@/components/ui";
import type { SelectedElementPayload } from "@/lib/editor-inject";

interface TextPanelProps {
  element: SelectedElementPayload;
  onApply: (changes: { textContent: string; style?: Record<string, string> }) => void;
}

const SIZES: Record<string, string> = {
  sm: "0.875rem",
  md: "1rem",
  lg: "1.25rem",
  xl: "1.75rem",
};

export function TextPanel({ element, onApply }: TextPanelProps) {
  const [text, setText] = useState(element.textContent.trim());
  const [bold, setBold] = useState(false);
  const [italic, setItalic] = useState(false);
  const [size, setSize] = useState<keyof typeof SIZES>("md");
  const [color, setColor] = useState("#f8fafc");

  useEffect(() => {
    setText(element.textContent.trim());
  }, [element.xpath, element.textContent]);

  function preview() {
    onApply({
      textContent: text,
      style: {
        fontWeight: bold ? "700" : "400",
        fontStyle: italic ? "italic" : "normal",
        fontSize: SIZES[size],
        color,
      },
    });
  }

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium uppercase tracking-wider text-cf-label">Texte</p>
      <p className="text-[11px] text-cf-muted">
        &lt;{element.tagName.toLowerCase()}&gt;
      </p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={4}
        className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text"
      />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setBold((v) => !v)}
          className={`rounded border px-2 py-1 text-xs ${bold ? "border-cf-gold text-cf-gold" : "border-cf-border-input"}`}
        >
          B
        </button>
        <button
          type="button"
          onClick={() => setItalic((v) => !v)}
          className={`rounded border px-2 py-1 text-xs italic ${italic ? "border-cf-gold text-cf-gold" : "border-cf-border-input"}`}
        >
          I
        </button>
        <select
          value={size}
          onChange={(e) => setSize(e.target.value as keyof typeof SIZES)}
          className="rounded border border-cf-border-input bg-cf-secondary px-2 py-1 text-xs"
        >
          <option value="sm">Petit</option>
          <option value="md">Moyen</option>
          <option value="lg">Grand</option>
          <option value="xl">Très grand</option>
        </select>
        <input
          type="color"
          value={color}
          onChange={(e) => setColor(e.target.value)}
          className="h-8 w-10 cursor-pointer rounded border border-cf-border-input"
          title="Couleur du texte"
        />
      </div>
      <Button variant="primary" size="sm" onClick={preview}>
        Appliquer
      </Button>
    </div>
  );
}

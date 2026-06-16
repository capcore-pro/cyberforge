import { useState } from "react";
import { Button } from "@/components/ui";
import type { SelectedElementPayload } from "@/lib/editor-inject";

interface ColorPanelProps {
  element: SelectedElementPayload;
  swatches: string[];
  onApply: (style: Record<string, string>) => void;
  onGlobalColor: (oldColor: string, newColor: string) => void;
}

export function ColorPanel({
  element,
  swatches,
  onApply,
  onGlobalColor,
}: ColorPanelProps) {
  const [color, setColor] = useState("#d4a843");
  const [scope, setScope] = useState<"element" | "global">("element");
  const [globalFrom, setGlobalFrom] = useState(swatches[0] ?? "#d4a843");

  return (
    <div className="space-y-3">
      <p className="text-xs font-medium uppercase tracking-wider text-cf-label">Couleur</p>
      <p className="text-[11px] text-cf-muted">
        &lt;{element.tagName.toLowerCase()}&gt;
      </p>
      <input
        type="color"
        value={color}
        onChange={(e) => setColor(e.target.value)}
        className="h-10 w-full cursor-pointer rounded border border-cf-border-input"
      />
      {swatches.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {swatches.map((sw) => (
            <button
              key={sw}
              type="button"
              title={sw}
              className="h-6 w-6 rounded border border-white/20"
              style={{ backgroundColor: sw }}
              onClick={() => setColor(sw)}
            />
          ))}
        </div>
      ) : null}
      <div className="space-y-1 text-xs">
        <label className="flex items-center gap-2">
          <input
            type="radio"
            checked={scope === "element"}
            onChange={() => setScope("element")}
          />
          Cet élément
        </label>
        <label className="flex items-center gap-2">
          <input
            type="radio"
            checked={scope === "global"}
            onChange={() => setScope("global")}
          />
          Couleur primaire globale
        </label>
      </div>
      {scope === "global" ? (
        <select
          value={globalFrom}
          onChange={(e) => setGlobalFrom(e.target.value)}
          className="w-full rounded border border-cf-border-input bg-cf-secondary px-2 py-1 text-xs"
        >
          {swatches.map((sw) => (
            <option key={sw} value={sw}>
              {sw}
            </option>
          ))}
        </select>
      ) : null}
      <Button
        variant="primary"
        size="sm"
        onClick={() => {
          if (scope === "global") {
            onGlobalColor(globalFrom, color);
          } else {
            onApply({ color });
          }
        }}
      >
        Appliquer
      </Button>
    </div>
  );
}

/** Maquette visuelle extraite du code généré. */
export interface PreviewMockup {
  title: string;
  subtitle: string;
  sections: PreviewSection[];
  buttons: string[];
  colors: PreviewColorSwatch[];
  hints: string[];
}

export interface PreviewSection {
  heading: string;
  lines: string[];
}

export interface PreviewColorSwatch {
  label: string;
  value: string;
}

const TAILWIND_PALETTE: Record<string, string> = {
  "slate-950": "#020617",
  "slate-900": "#0f172a",
  "gray-900": "#111827",
  "gray-800": "#1f2937",
  "zinc-900": "#18181b",
  "neutral-900": "#171717",
  "black": "#000000",
  "white": "#f8fafc",
  "violet-600": "#7c3aed",
  "violet-500": "#8b5cf6",
  "purple-600": "#9333ea",
  "purple-500": "#a855f7",
  "fuchsia-500": "#d946ef",
  "cyan-400": "#22d3ee",
  "cyan-500": "#06b6d4",
  "teal-400": "#2dd4bf",
  "emerald-400": "#34d399",
  "green-500": "#22c55e",
  "amber-400": "#fbbf24",
  "orange-500": "#f97316",
  "red-400": "#f87171",
  "rose-500": "#f43f5e",
  "blue-500": "#3b82f6",
  "indigo-600": "#4f46e5",
};

const NOISE_STRINGS =
  /^(true|false|null|undefined|react|typescript|tailwind|className|onClick|flex|grid|block|inline|relative|absolute|fixed|w-full|h-full|min-h-screen|px-\d|py-\d|mx-auto|items-center|justify-center|gap-\d|rounded|border|shadow|text-(xs|sm|base|lg|xl|2xl|3xl|4xl)|font-(bold|semibold|medium)|transition|hover:|focus:|md:|lg:|sm:)/i;

/**
 * Analyse du TSX/JSX pour produire une maquette affichable sans React.
 */
export function extractPreviewMockup(source: string): PreviewMockup {
  const code = source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");

  const headings = _extractHeadings(code);
  const strings = _extractReadableStrings(code);
  const classNames = _extractClassNames(code);
  const colors = _extractColors(classNames);
  const buttons = _extractButtons(code, strings);

  const title =
    headings.find((h) => h.level === 1)?.text ??
    strings.find((s) => s.length > 4 && s.length < 80) ??
    "Prototype généré";

  const subtitle =
    strings.find((s) => s !== title && s.length > 12 && s.length < 140) ??
    "Aperçu simplifié — structure et ambiance du site généré.";

  const sectionHeadings = headings
    .filter((h) => h.level >= 2)
    .map((h) => h.text)
    .filter((t) => t !== title);

  const bodyLines = strings
    .filter((s) => s !== title && s !== subtitle && !sectionHeadings.includes(s))
    .filter((s) => !buttons.includes(s))
    .slice(0, 8);

  const sections: PreviewSection[] = [];

  if (sectionHeadings.length > 0) {
    for (const heading of sectionHeadings.slice(0, 5)) {
      const lines = bodyLines.splice(0, 2);
      sections.push({
        heading,
        lines: lines.length
          ? lines
          : ["Contenu de section généré par CoreMindAI."],
      });
    }
  } else if (bodyLines.length > 0) {
    sections.push({
      heading: "Contenu principal",
      lines: bodyLines.slice(0, 4),
    });
  } else {
    sections.push({
      heading: "Structure détectée",
      lines: [
        "Le composant React contient une mise en page Tailwind.",
        "Ouvrez le code source pour le détail des interactions.",
      ],
    });
  }

  const hints = _extractLayoutHints(classNames);

  return {
    title,
    subtitle,
    sections,
    buttons: buttons.slice(0, 6),
    colors: colors.slice(0, 8),
    hints,
  };
}

/** Document HTML statique (aucun script externe). */
export function buildMockupPreviewHtml(mockup: PreviewMockup): string {
  const primary = mockup.colors[0]?.value ?? "#0f172a";
  const accent = mockup.colors.find((c) => /cyan|violet|purple|teal|fuchsia/i.test(c.label))?.value ?? "#22d3ee";
  const accent2 = mockup.colors.find((c) => /violet|purple|fuchsia/i.test(c.label))?.value ?? "#a855f7";

  const sectionsHtml = mockup.sections
    .map(
      (section) => `
      <section class="mock-section">
        <h2>${escapeHtml(section.heading)}</h2>
        ${section.lines.map((line) => `<p>${escapeHtml(line)}</p>`).join("")}
      </section>`,
    )
    .join("");

  const buttonsHtml = mockup.buttons.length
    ? `<div class="mock-actions">${mockup.buttons
        .map((label, i) => `<span class="mock-btn" style="--i:${i}">${escapeHtml(label)}</span>`)
        .join("")}</div>`
    : "";

  const paletteHtml = mockup.colors.length
    ? `<div class="mock-palette">
        <p class="mock-palette-label">Palette détectée</p>
        <div class="mock-swatches">
          ${mockup.colors
            .map(
              (c) =>
                `<span class="mock-swatch" title="${escapeAttr(c.label)}" style="background:${c.value}"></span>`,
            )
            .join("")}
        </div>
      </div>`
    : "";

  const hintsHtml = mockup.hints.length
    ? `<ul class="mock-hints">${mockup.hints
        .map((h) => `<li>${escapeHtml(h)}</li>`)
        .join("")}</ul>`
    : "";

  return `<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(mockup.title)} — Aperçu</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: "Segoe UI", system-ui, sans-serif;
      background: ${primary};
      color: #e2e8f0;
      min-height: 100vh;
      line-height: 1.5;
    }
    .mock-banner {
      padding: 0.5rem 1rem;
      background: rgba(0,0,0,0.35);
      border-bottom: 1px solid rgba(34,211,238,0.25);
      font-size: 0.65rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: ${accent};
    }
    .mock-hero {
      padding: 2.5rem 1.5rem 2rem;
      background: linear-gradient(135deg, ${primary} 0%, color-mix(in srgb, ${accent2} 35%, ${primary}) 100%);
      border-bottom: 1px solid rgba(168,85,247,0.25);
    }
    .mock-hero h1 {
      font-size: clamp(1.5rem, 4vw, 2.25rem);
      font-weight: 800;
      color: ${accent};
      text-shadow: 0 0 24px color-mix(in srgb, ${accent} 50%, transparent);
      margin-bottom: 0.75rem;
    }
    .mock-hero p { color: #94a3b8; max-width: 40rem; font-size: 0.95rem; }
    .mock-body { padding: 1.5rem; max-width: 56rem; margin: 0 auto; }
    .mock-section {
      background: rgba(15,23,42,0.65);
      border: 1px solid rgba(148,163,184,0.15);
      border-radius: 0.75rem;
      padding: 1.25rem 1.5rem;
      margin-bottom: 1rem;
    }
    .mock-section h2 {
      font-size: 1.1rem;
      color: ${accent2};
      margin-bottom: 0.65rem;
      font-weight: 700;
    }
    .mock-section p { color: #cbd5e1; font-size: 0.9rem; margin-bottom: 0.4rem; }
    .mock-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin: 1rem 0;
    }
    .mock-btn {
      display: inline-block;
      padding: 0.5rem 1rem;
      border-radius: 0.5rem;
      background: linear-gradient(90deg, ${accent2}, ${accent});
      color: #0a0a0f;
      font-size: 0.8rem;
      font-weight: 700;
    }
    .mock-palette { margin-top: 1.25rem; }
    .mock-palette-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em; color: #64748b; margin-bottom: 0.5rem; }
    .mock-swatches { display: flex; flex-wrap: wrap; gap: 0.35rem; }
    .mock-swatch {
      width: 2rem;
      height: 2rem;
      border-radius: 0.35rem;
      border: 1px solid rgba(255,255,255,0.15);
    }
    .mock-hints {
      list-style: none;
      margin-top: 1rem;
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem;
    }
    .mock-hints li {
      font-size: 0.65rem;
      padding: 0.25rem 0.5rem;
      border-radius: 999px;
      border: 1px solid rgba(34,211,238,0.3);
      color: ${accent};
      background: rgba(34,211,238,0.08);
    }
    .mock-wireframe {
      margin-top: 1.5rem;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 0.75rem;
    }
    .mock-card {
      height: 5rem;
      border-radius: 0.5rem;
      background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
      border: 1px dashed rgba(148,163,184,0.25);
    }
  </style>
</head>
<body>
  <p class="mock-banner">Aperçu visuel simplifié · CyberForge</p>
  <header class="mock-hero">
    <h1>${escapeHtml(mockup.title)}</h1>
    <p>${escapeHtml(mockup.subtitle)}</p>
    ${buttonsHtml}
  </header>
  <main class="mock-body">
    ${sectionsHtml}
    ${paletteHtml}
    ${hintsHtml}
    <div class="mock-wireframe" aria-hidden="true">
      <div class="mock-card"></div>
      <div class="mock-card"></div>
      <div class="mock-card"></div>
    </div>
  </main>
</body>
</html>`;
}

function _extractHeadings(code: string): { level: number; text: string }[] {
  const found: { level: number; text: string }[] = [];
  const tagRe = /<h([1-3])[^>]*>([\s\S]*?)<\/h\1>/gi;
  let match: RegExpExecArray | null;
  while ((match = tagRe.exec(code)) !== null) {
    const text = _stripJsx(match[2]);
    if (text) found.push({ level: Number(match[1]), text });
  }
  return found;
}

function _extractReadableStrings(code: string): string[] {
  const results: string[] = [];
  const seen = new Set<string>();

  const textNodes = code.matchAll(/>([^<>{}]+)</g);
  for (const m of textNodes) {
    const text = _cleanLabel(m[1]);
    if (text && !seen.has(text)) {
      seen.add(text);
      results.push(text);
    }
  }

  const quoted = code.matchAll(/["'`]([^"'`\n]{4,120})["'`]/g);
  for (const m of quoted) {
    const text = _cleanLabel(m[1]);
    if (text && !seen.has(text) && !_looksLikeCodeToken(text)) {
      seen.add(text);
      results.push(text);
    }
  }

  return results;
}

function _extractClassNames(code: string): string[] {
  const classes: string[] = [];
  const re = /className\s*=\s*(?:\{`([^`]+)`\}|"([^"]+)"|'([^']+)')/g;
  let match: RegExpExecArray | null;
  while ((match = re.exec(code)) !== null) {
    const value = match[1] ?? match[2] ?? match[3];
    if (value) classes.push(value);
  }
  return classes;
}

function _extractColors(classStrings: string[]): PreviewColorSwatch[] {
  const swatches: PreviewColorSwatch[] = [];
  const seen = new Set<string>();

  for (const block of classStrings) {
    for (const token of block.split(/\s+/)) {
      const colorMatch = token.match(
        /^(?:bg|text|from|to|via|border|ring)-([a-z]+-\d{2,3}|[a-z]+)$/,
      );
      if (!colorMatch) continue;
      const label = colorMatch[1];
      const value = TAILWIND_PALETTE[label];
      if (!value || seen.has(label)) continue;
      seen.add(label);
      swatches.push({ label, value });
    }
  }

  if (swatches.length === 0) {
    swatches.push(
      { label: "fond", value: "#0a0a0f" },
      { label: "accent", value: "#22d3ee" },
      { label: "violet", value: "#a855f7" },
    );
  }

  return swatches;
}

function _extractButtons(code: string, strings: string[]): string[] {
  const buttons: string[] = [];
  const seen = new Set<string>();

  const buttonRe = /<button[^>]*>([\s\S]*?)<\/button>/gi;
  let match: RegExpExecArray | null;
  while ((match = buttonRe.exec(code)) !== null) {
    const label = _stripJsx(match[1]);
    if (label && !seen.has(label)) {
      seen.add(label);
      buttons.push(label);
    }
  }

  for (const s of strings) {
    if (
      s.length < 28 &&
      /réserver|contact|menu|acheter|commencer|découvrir|voir|envoyer|inscri|login|sign|cta/i.test(
        s,
      ) &&
      !seen.has(s)
    ) {
      seen.add(s);
      buttons.push(s);
    }
  }

  return buttons;
}

function _extractLayoutHints(classStrings: string[]): string[] {
  const hints: string[] = [];
  const joined = classStrings.join(" ");
  if (/grid/i.test(joined)) hints.push("Grille");
  if (/flex/i.test(joined)) hints.push("Flex");
  if (/hero|banner/i.test(joined)) hints.push("Hero");
  if (/dark|slate-9|gray-9|zinc-9/i.test(joined)) hints.push("Thème sombre");
  if (/gradient|from-|to-/i.test(joined)) hints.push("Dégradés");
  if (/rounded|shadow/i.test(joined)) hints.push("Cartes");
  if (/md:|lg:|sm:/i.test(joined)) hints.push("Responsive");
  return hints.slice(0, 6);
}

function _stripJsx(fragment: string): string {
  return _cleanLabel(fragment.replace(/<[^>]+>/g, " "));
}

function _cleanLabel(raw: string): string {
  return raw
    .replace(/\{[^}]+\}/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function _looksLikeCodeToken(text: string): boolean {
  if (NOISE_STRINGS.test(text)) return true;
  if (/^[\w./@-]+$/.test(text) && !/\s/.test(text)) return true;
  if (/^(src|className|import|export|return|function|const|let)$/.test(text)) return true;
  return false;
}

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function escapeAttr(text: string): string {
  return escapeHtml(text).replace(/'/g, "&#39;");
}

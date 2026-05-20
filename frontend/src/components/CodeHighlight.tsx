import { useMemo } from "react";

const KEYWORDS =
  /\b(const|let|var|function|return|export|default|import|from|if|else|async|await|interface|type|class|extends|new|true|false|null|undefined|void)\b/g;
const STRINGS = /(`[^`]*`|"[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*')/g;
const COMMENTS = /(\/\/.*$|\/\*[\s\S]*?\*\/)/g;
const TAGS = /(<\/?[A-Za-z][A-Za-z0-9]*|>)/g;
const NUMBERS = /\b(\d+\.?\d*)\b/g;
const NEXT_TOKEN =
  /\/\/|\/\*|`|"[^"\\]|'[^'\\]|<\/?[A-Za-z]|\b(const|let|return|export|import)\b|\d/;

const MAX_HIGHLIGHT_CHARS = 120_000;
const MAX_HIGHLIGHT_LINES = 800;

type TokenKind = "plain" | "keyword" | "string" | "comment" | "tag" | "number";

interface Token {
  text: string;
  kind: TokenKind;
}

function tokenizeLine(line: string): Token[] {
  const tokens: Token[] = [];
  let rest = line;

  while (rest.length > 0) {
    let matched = false;
    for (const [regex, kind] of [
      [COMMENTS, "comment"],
      [STRINGS, "string"],
      [TAGS, "tag"],
      [KEYWORDS, "keyword"],
      [NUMBERS, "number"],
    ] as const) {
      regex.lastIndex = 0;
      const m = regex.exec(rest);
      if (m && m.index === 0) {
        tokens.push({ text: m[0], kind });
        rest = rest.slice(m[0].length);
        matched = true;
        break;
      }
    }
    if (matched) continue;

    const next = rest.search(NEXT_TOKEN);
    if (next === -1) {
      if (rest) tokens.push({ text: rest, kind: "plain" });
      break;
    }
    if (next > 0) {
      tokens.push({ text: rest.slice(0, next), kind: "plain" });
      rest = rest.slice(next);
      continue;
    }
    // next === 0 mais aucun motif reconnu — avancer d'un caractère (évite boucle infinie)
    tokens.push({ text: rest[0], kind: "plain" });
    rest = rest.slice(1);
  }
  return tokens;
}

const KIND_CLASS: Record<TokenKind, string> = {
  plain: "text-cyber-text",
  keyword: "text-cyber-violet",
  string: "text-green-400",
  comment: "text-cyber-muted italic",
  tag: "text-cyber-neon",
  number: "text-amber-400",
};

interface CodeHighlightProps {
  code: string;
  filePath?: string;
}

/**
 * Coloration syntaxique légère (TS/JS/JSX) — thème cyber.
 */
export function CodeHighlight({ code, filePath }: CodeHighlightProps) {
  const { lines, truncated } = useMemo(() => {
    let text = code;
    let truncatedNote = false;
    if (text.length > MAX_HIGHLIGHT_CHARS) {
      text = text.slice(0, MAX_HIGHLIGHT_CHARS);
      truncatedNote = true;
    }
    const allLines = text.split("\n");
    const limited =
      allLines.length > MAX_HIGHLIGHT_LINES
        ? allLines.slice(0, MAX_HIGHLIGHT_LINES)
        : allLines;
    if (limited.length < allLines.length) truncatedNote = true;
    return { lines: limited, truncated: truncatedNote };
  }, [code]);

  const lang =
    filePath?.endsWith(".css") ? "css" : filePath?.endsWith(".html") ? "html" : "tsx";

  return (
    <div className="cyber-code-viewer overflow-hidden rounded-lg border border-cyber-border bg-cyber-bg">
      <div className="flex items-center justify-between border-b border-cyber-border bg-cyber-surfaceAlt/80 px-3 py-2">
        <span className="font-mono text-[10px] text-cyber-muted">
          {filePath ?? "output"} · {lang}
          {truncated ? " · aperçu tronqué" : ""}
        </span>
        <span className="text-[10px] uppercase tracking-wider text-cyber-violet">
          syntax highlight
        </span>
      </div>
      <pre className="max-h-[32rem] overflow-auto p-0 text-xs leading-relaxed">
        <code className="block font-mono">
          {lines.map((line, lineIndex) => (
            <div
              key={`${lineIndex}-${line.slice(0, 8)}`}
              className="flex hover:bg-cyber-violet/5"
            >
              <span className="select-none border-r border-cyber-border bg-cyber-surfaceAlt/50 px-3 py-0.5 text-right text-[10px] text-cyber-muted">
                {lineIndex + 1}
              </span>
              <span className="flex-1 whitespace-pre px-3 py-0.5">
                {tokenizeLine(line).map((token, i) => (
                  <span key={i} className={KIND_CLASS[token.kind]}>
                    {token.text}
                  </span>
                ))}
                {line.length === 0 ? "\u00a0" : null}
              </span>
            </div>
          ))}
        </code>
      </pre>
    </div>
  );
}

import type { GeneratedFile } from "@shared/types";

/** Dé-enveloppe une réponse LLM JSON stockée par erreur dans code ou files[].content */
export function unwrapGenerationPayload(
  files: GeneratedFile[],
  code: string,
): { code: string; files: GeneratedFile[] } {
  const trimmedCode = code.trim();

  const fromCode = tryUnwrapJsonBlob(trimmedCode);
  if (fromCode) return fromCode;

  if (files.length === 1) {
    const fromFile = tryUnwrapJsonBlob(files[0].content.trim());
    if (fromFile) return fromFile;
  }

  return { code: trimmedCode, files };
}

function tryUnwrapJsonBlob(
  text: string,
): { code: string; files: GeneratedFile[] } | null {
  if (!text.startsWith("{") || !text.includes('"code"')) {
    return null;
  }

  try {
    const parsed = JSON.parse(text) as Record<string, unknown>;
    return payloadFromObject(parsed);
  } catch {
    const extracted = extractQuotedField(text, "code");
    if (extracted && extracted.length > 20) {
      return { code: extracted, files: [] };
    }
  }
  return null;
}

function payloadFromObject(
  data: Record<string, unknown>,
): { code: string; files: GeneratedFile[] } | null {
  const rawCode = data.code;
  if (typeof rawCode !== "string" || !rawCode.trim()) {
    return null;
  }

  const files: GeneratedFile[] = [];
  if (Array.isArray(data.files)) {
    for (const item of data.files) {
      if (
        item &&
        typeof item === "object" &&
        typeof (item as GeneratedFile).path === "string" &&
        typeof (item as GeneratedFile).content === "string"
      ) {
        files.push({
          path: (item as GeneratedFile).path,
          content: (item as GeneratedFile).content,
        });
      }
    }
  }

  const code = rawCode.trim();
  if (!files.length && code) {
    files.push({
      path: guessPrimaryPath(code),
      content: code,
    });
  }

  return { code, files };
}

function extractQuotedField(text: string, key: string): string | null {
  const marker = `"${key}"`;
  const idx = text.indexOf(marker);
  if (idx < 0) return null;
  let rest = text.slice(idx + marker.length);
  const colon = rest.indexOf(":");
  if (colon < 0) return null;
  rest = rest.slice(colon + 1).trim();
  if (!rest.startsWith('"')) return null;

  let i = 1;
  let out = "";
  while (i < rest.length) {
    const ch = rest[i];
    if (ch === "\\" && i + 1 < rest.length) {
      const nxt = rest[i + 1];
      if (nxt === "n") out += "\n";
      else if (nxt === "t") out += "\t";
      else if (nxt === "r") out += "\r";
      else if (nxt === '"') out += '"';
      else if (nxt === "\\") out += "\\";
      else out += nxt;
      i += 2;
      continue;
    }
    if (ch === '"') break;
    out += ch;
    i += 1;
  }
  return out;
}

function guessPrimaryPath(code: string): string {
  const head = code.trimStart().slice(0, 800);
  if (head.startsWith("<!") || head.toLowerCase().includes("<html")) {
    return "index.html";
  }
  return "src/App.tsx";
}

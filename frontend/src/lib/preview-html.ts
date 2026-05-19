/** Fichier source pour la prévisualisation. */
export interface PreviewSourceFile {
  path: string;
  content: string;
}

/**
 * Construit un document HTML autonome pour iframe / fenêtre Electron.
 * HTML brut si présent, sinon React via CDN + Babel standalone.
 */
export function buildPreviewDocument(files: PreviewSourceFile[]): string {
  if (files.length === 0) {
    return _emptyPreviewHtml("Aucun fichier à prévisualiser.");
  }

  const htmlFile = files.find((f) => /\.html?$/i.test(f.path));
  if (htmlFile) {
    return htmlFile.content;
  }

  const cssBlocks = files
    .filter((f) => /\.css$/i.test(f.path))
    .map((f) => `<style data-file="${escapeAttr(f.path)}">\n${f.content}\n</style>`)
    .join("\n");

  const primary =
    files.find((f) => /App\.(tsx|jsx)$/i.test(f.path)) ??
    files.find((f) => /\.(tsx|jsx)$/i.test(f.path)) ??
    files[0];

  const script = _prepareReactScript(primary.content);
  const title = primary.path.split("/").pop() ?? "preview";

  return `<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CyberForge — ${escapeHtml(title)}</title>
  <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
  <script src="https://unpkg.com/@babel/standalone@7/babel.min.js"></script>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { margin: 0; min-height: 100vh; background: #0a0a0f; color: #e2e8f0; font-family: system-ui, sans-serif; }
    #root { min-height: 100vh; }
    .preview-error { padding: 1.5rem; color: #f87171; font-family: monospace; white-space: pre-wrap; }
  </style>
  ${cssBlocks}
</head>
<body>
  <div id="root"></div>
  <script type="text/babel" data-presets="react,typescript">
${script}
  </script>
</body>
</html>`;
}

function _emptyPreviewHtml(message: string): string {
  return `<!DOCTYPE html><html><body><p class="preview-error">${escapeHtml(message)}</p></body></html>`;
}

function _prepareReactScript(source: string): string {
  let code = source
    .replace(/^import\s+.+$/gm, "")
    .replace(/^export\s+default\s+/gm, "")
    .replace(/^export\s+/gm, "")
    .replace(/:\s*React\.FC[^=]*=/g, " =")
    .replace(/:\s*React\.FC<[^>]*>/g, "")
    .replace(/:\s*JSX\.Element/g, "")
    .trim();

  const nameMatch = code.match(/(?:function|const)\s+([A-Z][A-Za-z0-9]*)/);
  const componentName = nameMatch?.[1] ?? "App";

  return `${code}

try {
  const rootEl = document.getElementById('root');
  const root = ReactDOM.createRoot(rootEl);
  const Component = typeof ${componentName} !== 'undefined' ? ${componentName} : () => (
    <div className="preview-error">Composant « ${componentName} » introuvable dans le code généré.</div>
  );
  root.render(React.createElement(Component));
} catch (err) {
  document.getElementById('root').innerHTML = '<pre class="preview-error">' + (err && err.message ? err.message : err) + '</pre>';
}`;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(text: string): string {
  return escapeHtml(text).replace(/'/g, "&#39;");
}

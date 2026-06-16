/** Script injecté dans l'iframe pour la sélection d'éléments (postMessage). */
const EDITOR_BRIDGE_SCRIPT = `
(function () {
  if (window.__cfEditorBridge) return;
  window.__cfEditorBridge = true;

  function getXPath(el) {
    if (!el || el.nodeType !== 1) return "";
    var parts = [];
    var node = el;
    while (node && node.tagName && node.tagName !== "HTML") {
      var parent = node.parentElement;
      if (!parent) break;
      var idx = Array.prototype.indexOf.call(parent.children, node) + 1;
      parts.unshift(node.tagName.toLowerCase() + ":nth-child(" + idx + ")");
      node = parent;
    }
    return parts.join(" > ");
  }

  document.addEventListener(
    "click",
    function (e) {
      e.preventDefault();
      e.stopPropagation();
      var el = e.target;
      if (!el || el.nodeType !== 1) return;
      var rect = el.getBoundingClientRect();
      window.parent.postMessage(
        {
          type: "ELEMENT_SELECTED",
          tagName: el.tagName,
          className: el.className || "",
          innerHTML: el.innerHTML || "",
          textContent: el.textContent || "",
          src: el.src || null,
          href: el.href || null,
          rect: {
            top: rect.top,
            left: rect.left,
            width: rect.width,
            height: rect.height,
          },
          xpath: getXPath(el),
        },
        "*",
      );
    },
    true,
  );

  document.addEventListener(
    "mouseover",
    function (e) {
      var el = e.target;
      if (el && el.style) el.style.outline = "2px solid #d4a843";
    },
    true,
  );

  document.addEventListener(
    "mouseout",
    function (e) {
      var el = e.target;
      if (el && el.style) el.style.outline = "";
    },
    true,
  );
})();
`;

export function injectEditorScript(html: string): string {
  if (html.includes("data-cf-editor-inject")) {
    return html;
  }
  const tag = `<script data-cf-editor-inject>${EDITOR_BRIDGE_SCRIPT}</script>`;
  const lower = html.toLowerCase();
  const bodyIdx = lower.lastIndexOf("</body>");
  if (bodyIdx >= 0) {
    return `${html.slice(0, bodyIdx)}${tag}${html.slice(bodyIdx)}`;
  }
  return `${html}${tag}`;
}

export interface SelectedElementPayload {
  type: "ELEMENT_SELECTED";
  tagName: string;
  className: string;
  innerHTML: string;
  textContent: string;
  src: string | null;
  href: string | null;
  rect: { top: number; left: number; width: number; height: number };
  xpath: string;
}

export function isSelectedElementPayload(
  data: unknown,
): data is SelectedElementPayload {
  return (
    typeof data === "object" &&
    data !== null &&
    (data as SelectedElementPayload).type === "ELEMENT_SELECTED" &&
    typeof (data as SelectedElementPayload).xpath === "string"
  );
}

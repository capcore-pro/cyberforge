import { useEffect, useRef, useState } from "react";
import type { Client, Site } from "../App";

const API =
  import.meta.env.VITE_API_URL ||
  "https://cyberforge-backend-production.up.railway.app";

interface Edit {
  type: string;
  selector: string;
  old_value: string;
  new_value: string;
}

interface Props {
  client: Client;
  site: Site;
  onBack: () => void;
  onSaved: (site: Site) => void;
}

export default function Editor({ client, site, onBack, onSaved }: Props) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [edits, setEdits] = useState<Edit[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [htmlForSave, setHtmlForSave] = useState(site.html_content);

  function injectEditorScript() {
    const iframe = iframeRef.current;
    if (!iframe) return;

    iframe.onload = () => {
      const doc = iframe.contentDocument;
      if (!doc) return;

      const script = doc.createElement("script");
      script.textContent = `
        (function() {
          let selectedEl = null;
          let editBox = null;

          const toolbar = document.createElement('div');
          toolbar.style.cssText = \`
            position: fixed; top: 0; left: 0; right: 0; z-index: 99999;
            background: #1a1a2e; padding: 10px 20px;
            display: flex; align-items: center; gap: 12px;
            border-bottom: 2px solid #3b82f6;
            font-family: sans-serif;
          \`;
          toolbar.innerHTML = \`
            <span style="color:#3b82f6; font-weight:bold; font-size:14px;">
              ✏️ Mode édition
            </span>
            <span style="color:#6b7280; font-size:12px;">
              Cliquez sur un texte pour le modifier
            </span>
          \`;
          document.body.prepend(toolbar);
          document.body.style.paddingTop = '50px';

          document.querySelectorAll('p, h1, h2, h3, h4, h5, span, a, li, td, th, div')
            .forEach(el => {
              if (el.children.length > 0) return;
              if (!el.textContent.trim()) return;

              el.style.cursor = 'pointer';
              el.style.transition = 'outline 0.1s';

              el.addEventListener('mouseenter', function() {
                this.style.outline = '2px solid #3b82f6';
                this.style.outlineOffset = '2px';
              });

              el.addEventListener('mouseleave', function() {
                if (selectedEl !== this) {
                  this.style.outline = '';
                }
              });

              el.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                if (selectedEl && selectedEl !== this) {
                  selectedEl.style.outline = '';
                  if (editBox) editBox.remove();
                }

                selectedEl = this;
                this.style.outline = '2px solid #f59e0b';

                const rect = this.getBoundingClientRect();
                editBox = document.createElement('div');
                editBox.style.cssText = \`
                  position: fixed;
                  left: \${rect.left}px;
                  top: \${rect.bottom + window.scrollY + 8}px;
                  z-index: 100000;
                  background: #1f2937;
                  border: 1px solid #3b82f6;
                  border-radius: 8px;
                  padding: 10px;
                  min-width: 300px;
                  max-width: 500px;
                  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
                \`;

                const textarea = document.createElement('textarea');
                textarea.value = this.textContent;
                textarea.style.cssText = \`
                  width: 100%; min-height: 60px; background: #374151;
                  color: white; border: 1px solid #4b5563; border-radius: 6px;
                  padding: 8px; font-size: 14px; resize: vertical;
                  font-family: sans-serif;
                \`;

                const btnRow = document.createElement('div');
                btnRow.style.cssText = 'display:flex; gap:8px; margin-top:8px;';

                const btnOk = document.createElement('button');
                btnOk.textContent = '✓ Valider';
                btnOk.style.cssText = \`
                  flex:1; padding:6px; background:#3b82f6; color:white;
                  border:none; border-radius:6px; cursor:pointer; font-size:13px;
                \`;

                const btnCancel = document.createElement('button');
                btnCancel.textContent = 'Annuler';
                btnCancel.style.cssText = \`
                  padding:6px 12px; background:#374151; color:#9ca3af;
                  border:none; border-radius:6px; cursor:pointer; font-size:13px;
                \`;

                const oldValue = this.textContent;
                const elRef = this;

                btnOk.addEventListener('click', () => {
                  const newVal = textarea.value;
                  elRef.textContent = newVal;
                  elRef.style.outline = '';
                  editBox.remove();
                  selectedEl = null;

                  window.parent.postMessage({
                    type: 'PORTAL_EDIT',
                    edit: {
                      type: 'text',
                      selector: elRef.tagName.toLowerCase(),
                      old_value: oldValue,
                      new_value: newVal,
                    },
                    html: document.documentElement.outerHTML,
                  }, '*');
                });

                btnCancel.addEventListener('click', () => {
                  elRef.style.outline = '';
                  editBox.remove();
                  selectedEl = null;
                });

                btnRow.append(btnOk, btnCancel);
                editBox.append(textarea, btnRow);
                document.body.append(editBox);
              });
            });
        })();
      `;
      doc.body.appendChild(script);
    };
  }

  useEffect(() => {
    injectEditorScript();
  }, []);

  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      if (event.data?.type !== "PORTAL_EDIT") return;
      const edit = event.data.edit as Edit;
      const newHtml = event.data.html as string;

      setEdits((prev) => [...prev, edit]);
      setHtmlForSave(newHtml);
      setSaved(false);
    }

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  async function handleSave() {
    if (edits.length === 0) return;
    setSaving(true);

    try {
      const res = await fetch(`${API}/api/portal/save-deploy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          site_id: site.id,
          client_id: client.id,
          edits,
          html_updated: htmlForSave,
        }),
      });

      const data = await res.json();
      if (data.success) {
        setSaved(true);
        setEdits([]);
        onSaved({
          ...site,
          html_content: htmlForSave,
          site_url: data.url || site.site_url,
        });
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="h-screen flex flex-col">
      <div
        className="bg-gray-900 border-b border-gray-700 px-4 py-3
                      flex items-center justify-between shrink-0"
      >
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="text-gray-400 hover:text-white text-sm transition-colors"
          >
            ← Retour
          </button>
          <span className="text-white font-medium">{site.site_name}</span>
          {edits.length > 0 && (
            <span
              className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400
                             text-xs rounded-full"
            >
              {edits.length} modification{edits.length > 1 ? "s" : ""}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {saved && (
            <span className="text-green-400 text-sm">✅ Site mis à jour</span>
          )}
          <button
            type="button"
            onClick={() => void handleSave()}
            disabled={saving || edits.length === 0}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50
                       text-white text-sm rounded-lg transition-colors font-medium"
          >
            {saving ? "Enregistrement..." : "💾 Enregistrer & Publier"}
          </button>
        </div>
      </div>

      <iframe
        ref={iframeRef}
        srcDoc={site.html_content}
        onLoad={injectEditorScript}
        className="flex-1 w-full border-0"
        title="Éditeur de site"
        sandbox="allow-scripts allow-same-origin"
      />
    </div>
  );
}

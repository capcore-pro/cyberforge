import { useEffect, useRef, useState } from "react";
import type { Client, Site } from "../App";
import { getMyFeatures, type ClientFeatures } from "../lib/portal-api";

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
  const [features, setFeatures] = useState<ClientFeatures | null>(null);
  const [activePanel, setActivePanel] = useState<
    "colors" | "fonts" | "sections" | null
  >(null);
  const [selectedElement, setSelectedElement] = useState<string | null>(null);
  const [sections, setSections] = useState<
    Array<{ selector: string; label: string; visible: boolean }>
  >([]);

  const detectSections = () => {
    const iframe = iframeRef.current;
    if (!iframe?.contentDocument) return;
    const sectionEls = iframe.contentDocument.querySelectorAll(
      "section, [data-section], header, footer, nav, .hero, .features, .contact, .about",
    );
    const detected = Array.from(sectionEls).map((el, i) => ({
      selector:
        el.tagName.toLowerCase() +
        (el.id ? `#${el.id}` : `:nth-of-type(${i + 1})`),
      label:
        el.id ||
        el.getAttribute("data-section") ||
        el.tagName.toLowerCase() + ` ${i + 1}`,
      visible: (el as HTMLElement).style.display !== "none",
    }));
    setSections(detected);
  };

  const applyColor = (
    selector: string,
    property: "color" | "background-color",
    value: string,
  ) => {
    const iframe = iframeRef.current;
    if (!iframe?.contentDocument) return;
    const el = iframe.contentDocument.querySelector(selector) as HTMLElement | null;
    if (!el) return;
    el.style[property === "color" ? "color" : "backgroundColor"] = value;
    const newHtml = iframe.contentDocument.documentElement.outerHTML;
    setHtmlForSave(newHtml);
    setEdits((prev) => [
      ...prev,
      {
        type: "color",
        selector,
        old_value: "",
        new_value: JSON.stringify({ property, value }),
      },
    ]);
  };

  const applyFont = (selector: string, fontFamily: string, fontSize: string) => {
    const iframe = iframeRef.current;
    if (!iframe?.contentDocument) return;
    const els = iframe.contentDocument.querySelectorAll(selector);
    els.forEach((el) => {
      (el as HTMLElement).style.fontFamily = fontFamily;
      if (fontSize) (el as HTMLElement).style.fontSize = fontSize;
    });
    const newHtml = iframe.contentDocument.documentElement.outerHTML;
    setHtmlForSave(newHtml);
    setEdits((prev) => [
      ...prev,
      {
        type: "font",
        selector,
        old_value: "",
        new_value: JSON.stringify({ fontFamily, fontSize }),
      },
    ]);
  };

  const toggleSection = (sectionSelector: string, visible: boolean) => {
    const iframe = iframeRef.current;
    if (!iframe?.contentDocument) return;
    const el = iframe.contentDocument.querySelector(
      sectionSelector,
    ) as HTMLElement | null;
    if (!el) return;
    el.style.display = visible ? "" : "none";
    const newHtml = iframe.contentDocument.documentElement.outerHTML;
    setHtmlForSave(newHtml);
    setSections((prev) =>
      prev.map((s) =>
        s.selector === sectionSelector ? { ...s, visible } : s,
      ),
    );
    setEdits((prev) => [
      ...prev,
      {
        type: "section",
        selector: sectionSelector,
        old_value: visible ? "none" : "",
        new_value: visible ? "" : "none",
      },
    ]);
  };

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

  useEffect(() => {
    void getMyFeatures(client.id).then((f) => {
      setFeatures(f);
      if (f.can_edit_sections) {
        detectSections();
      }
    });
  }, [client.id]);

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

      {features &&
        (features.can_edit_colors ||
          features.can_edit_fonts ||
          features.can_edit_sections) && (
          <div className="flex gap-2 px-4 py-2 bg-[#0a0a12] border-b border-white/10 shrink-0">
            {features.can_edit_colors && (
              <button
                type="button"
                onClick={() =>
                  setActivePanel(activePanel === "colors" ? null : "colors")
                }
                className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                  activePanel === "colors"
                    ? "bg-cyan-400 text-black"
                    : "bg-white/5 text-white/60 hover:text-white"
                }`}
              >
                🎨 Couleurs
              </button>
            )}
            {features.can_edit_fonts && (
              <button
                type="button"
                onClick={() =>
                  setActivePanel(activePanel === "fonts" ? null : "fonts")
                }
                className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                  activePanel === "fonts"
                    ? "bg-cyan-400 text-black"
                    : "bg-white/5 text-white/60 hover:text-white"
                }`}
              >
                Aa Fonts
              </button>
            )}
            {features.can_edit_sections && (
              <button
                type="button"
                onClick={() => {
                  setActivePanel(
                    activePanel === "sections" ? null : "sections",
                  );
                  detectSections();
                }}
                className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                  activePanel === "sections"
                    ? "bg-cyan-400 text-black"
                    : "bg-white/5 text-white/60 hover:text-white"
                }`}
              >
                ☰ Sections
              </button>
            )}
          </div>
        )}

      <div className="relative flex-1 min-h-0">
        <iframe
          ref={iframeRef}
          srcDoc={site.html_content}
          onLoad={injectEditorScript}
          className="h-full w-full border-0"
          title="Éditeur de site"
          sandbox="allow-scripts allow-same-origin"
        />

        {activePanel && (
          <div className="absolute right-0 top-0 h-full w-72 bg-[#0f0f13] border-l border-white/10 z-10 overflow-y-auto">
            <div className="p-4 space-y-4">
              {activePanel === "colors" && (
                <>
                  <h3 className="text-sm font-medium text-white">Couleurs</h3>
                  {[
                    {
                      label: "Fond principal",
                      selector: "body",
                      property: "background-color" as const,
                    },
                    {
                      label: "Texte principal",
                      selector: "body",
                      property: "color" as const,
                    },
                    {
                      label: "Titres (h1)",
                      selector: "h1",
                      property: "color" as const,
                    },
                    {
                      label: "Titres (h2)",
                      selector: "h2",
                      property: "color" as const,
                    },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className="flex items-center justify-between"
                    >
                      <span className="text-xs text-white/60">{item.label}</span>
                      <input
                        type="color"
                        defaultValue="#ffffff"
                        onChange={(e) =>
                          applyColor(item.selector, item.property, e.target.value)
                        }
                        className="w-8 h-8 rounded cursor-pointer border border-white/20 bg-transparent"
                      />
                    </div>
                  ))}
                </>
              )}

              {activePanel === "fonts" && (
                <>
                  <h3 className="text-sm font-medium text-white">Typographie</h3>
                  {[
                    { label: "Titres", selector: "h1, h2, h3" },
                    { label: "Corps de texte", selector: "p, li, span" },
                    { label: "Boutons", selector: "button, a.btn, .btn" },
                  ].map((item) => (
                    <div key={item.label} className="space-y-2">
                      <p className="text-xs text-white/60">{item.label}</p>
                      <select
                        onChange={(e) =>
                          applyFont(item.selector, e.target.value, "")
                        }
                        className="w-full bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white text-xs focus:outline-none focus:border-cyan-400"
                      >
                        <option value="" className="bg-[#0f0f13]">
                          Choisir une police
                        </option>
                        {[
                          "Arial",
                          "Georgia",
                          "Helvetica",
                          "Inter",
                          "Montserrat",
                          "Playfair Display",
                          "Roboto",
                          "Open Sans",
                        ].map((f) => (
                          <option key={f} value={f} className="bg-[#0f0f13]">
                            {f}
                          </option>
                        ))}
                      </select>
                      <select
                        onChange={(e) =>
                          applyFont(item.selector, "", e.target.value)
                        }
                        className="w-full bg-white/5 border border-white/10 rounded px-2 py-1.5 text-white text-xs focus:outline-none focus:border-cyan-400"
                      >
                        <option value="" className="bg-[#0f0f13]">
                          Taille
                        </option>
                        {[
                          "12px",
                          "14px",
                          "16px",
                          "18px",
                          "20px",
                          "24px",
                          "28px",
                          "32px",
                        ].map((s) => (
                          <option key={s} value={s} className="bg-[#0f0f13]">
                            {s}
                          </option>
                        ))}
                      </select>
                    </div>
                  ))}
                </>
              )}

              {activePanel === "sections" && (
                <>
                  <h3 className="text-sm font-medium text-white">Sections</h3>
                  {sections.length === 0 && (
                    <p className="text-xs text-white/30">
                      Aucune section détectée
                    </p>
                  )}
                  {sections.map((s) => (
                    <div
                      key={s.selector}
                      className="flex items-center justify-between"
                    >
                      <span className="text-xs text-white/60 capitalize">
                        {s.label}
                      </span>
                      <button
                        type="button"
                        onClick={() => toggleSection(s.selector, !s.visible)}
                        className={`px-2 py-1 rounded text-xs transition-colors ${
                          s.visible
                            ? "bg-cyan-400/20 text-cyan-400"
                            : "bg-white/5 text-white/30"
                        }`}
                      >
                        {s.visible ? "Visible" : "Masqué"}
                      </button>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

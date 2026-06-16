import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ElementSelector } from "@/components/editor/ElementSelector";
import { EditorToolsPanel } from "@/components/editor/EditorToolsPanel";
import { Badge, Button, Modal } from "@/components/ui";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  exportZip,
  fetchProjectHTML,
  redeployHTML,
  saveHTML,
} from "@/lib/editor-api";
import { isSelectedElementPayload, type SelectedElementPayload } from "@/lib/editor-inject";
import { HTMLEditor } from "@/lib/html-editor";
import {
  PREVIEW_DEVICE_ORDER,
  PREVIEW_DEVICE_SPECS,
  type PreviewDeviceType,
} from "@/lib/preview-devices";

interface EditorPageProps {
  projectId: string;
  onBack: () => void;
}

export function EditorPage({ projectId, onBack }: EditorPageProps) {
  const editorRef = useRef<HTMLEditor | null>(null);
  const [generationId, setGenerationId] = useState<string | null>(null);
  const [projectTitle, setProjectTitle] = useState("Projet");
  const [demoUrl, setDemoUrl] = useState<string | null>(null);
  const [html, setHtml] = useState("");
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"save" | "deploy" | "export" | null>(null);
  const [viewport, setViewport] = useState<PreviewDeviceType>("desktop");
  const [selected, setSelected] = useState<SelectedElementPayload | null>(null);
  const [successUrl, setSuccessUrl] = useState<string | null>(null);

  const swatches = useMemo(
    () => editorRef.current?.extractSiteColors() ?? [],
    [html],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await fetchProjectHTML(projectId);
    setLoading(false);
    if (!res.ok || !res.data) {
      setError(apiErrorMessage(res, "Impossible de charger le HTML."));
      return;
    }
    const payload = res.data;
    setGenerationId(payload.generation_id);
    setProjectTitle(payload.project_title?.trim() || "Projet");
    setDemoUrl(payload.demo_url);
    editorRef.current = new HTMLEditor(payload.html);
    setHtml(editorRef.current.getHTML());
    setDirty(false);
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    function onMessage(event: MessageEvent) {
      if (isSelectedElementPayload(event.data)) {
        setSelected(event.data);
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  const applyHtml = useCallback((next: string) => {
    setHtml(next);
    setDirty(true);
  }, []);

  const handleSave = useCallback(async () => {
    const ed = editorRef.current;
    if (!ed || !generationId) return;
    setBusy("save");
    const res = await saveHTML(projectId, generationId, ed.getHTML());
    setBusy(null);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Sauvegarde impossible."));
      return;
    }
    setDirty(false);
    setError(null);
  }, [generationId, projectId]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (!(e.ctrlKey || e.metaKey)) return;
      if (e.key === "s") {
        e.preventDefault();
        void handleSave();
      }
      if (e.key === "z") {
        e.preventDefault();
        const ed = editorRef.current;
        if (!ed) return;
        applyHtml(ed.undo());
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [applyHtml, handleSave]);

  async function handleRedeploy() {
    const ed = editorRef.current;
    if (!ed || !generationId) return;
    setBusy("deploy");
    const res = await redeployHTML(projectId, generationId, ed.getHTML());
    setBusy(null);
    if (!res.ok || !res.data?.url) {
      setError(apiErrorMessage(res, "Redéploiement impossible."));
      return;
    }
    setDirty(false);
    setDemoUrl(res.data.url);
    setSuccessUrl(res.data.url);
    setError(null);
  }

  function mutate(fn: (ed: HTMLEditor) => string) {
    const ed = editorRef.current;
    if (!ed) return;
    applyHtml(fn(ed));
  }

  async function handleExportZip() {
    setBusy("export");
    setError(null);
    try {
      await exportZip(projectId, projectTitle);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export ZIP impossible.");
    } finally {
      setBusy(null);
    }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-cf-bg text-cf-muted">
        Chargement de l&apos;éditeur…
      </div>
    );
  }

  if (error && !html) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-cf-bg p-6">
        <p className="text-red-300">{error}</p>
        <Button variant="ghost" onClick={onBack}>
          ← Retour
        </Button>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-cf-bg text-cf-text">
      <header className="flex flex-wrap items-center gap-3 border-b border-cf-border-input px-4 py-3">
        <Button variant="ghost" size="sm" onClick={onBack}>
          ← Retour
        </Button>
        <input
          type="text"
          value={projectTitle}
          onChange={(e) => setProjectTitle(e.target.value)}
          className="min-w-0 flex-1 rounded border border-cf-border-input bg-cf-secondary px-2 py-1 text-sm font-semibold"
        />
        {dirty ? (
          <Badge variant="amber" size="sm">
            Non sauvegardé
          </Badge>
        ) : null}
        <div className="flex flex-wrap items-center gap-1 rounded-control border border-cf-border-input bg-cf-secondary p-1">
          {PREVIEW_DEVICE_ORDER.map((device) => (
            <button
              key={device}
              type="button"
              onClick={() => setViewport(device)}
              className={`rounded px-2 py-1 text-xs transition ${
                viewport === device
                  ? "bg-cf-gold/20 text-cf-gold"
                  : "text-cf-muted hover:text-cf-text"
              }`}
            >
              {PREVIEW_DEVICE_SPECS[device].shortLabel} ({PREVIEW_DEVICE_SPECS[device].width}px)
            </button>
          ))}
        </div>
        <Button
          variant="ghost"
          size="sm"
          icon="ti ti-download"
          loading={busy === "export"}
          onClick={() => void handleExportZip()}
        >
          Télécharger ZIP
        </Button>
        <Button
          variant="ghost"
          size="sm"
          loading={busy === "save"}
          onClick={() => void handleSave()}
        >
          Sauvegarder
        </Button>
        <Button
          variant="primary"
          size="sm"
          icon="ti ti-external-link"
          iconPosition="right"
          loading={busy === "deploy"}
          onClick={() => void handleRedeploy()}
        >
          Redéployer
        </Button>
      </header>

      {error ? (
        <p className="border-b border-red-500/30 bg-red-950/30 px-4 py-2 text-xs text-red-200">
          {error}
        </p>
      ) : null}

      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-[7] border-r border-cf-border-input">
          <ElementSelector html={html} viewport={viewport} className="h-full" />
        </div>
        <aside className="flex-[3] overflow-y-auto p-4">
          <p className="mb-3 text-[10px] font-medium uppercase tracking-wider text-cf-label">
            Panneau outils
          </p>
          <EditorToolsPanel
            projectId={projectId}
            selected={selected}
            swatches={swatches}
            onTextApply={(xpath, changes) =>
              mutate((ed) => ed.updateElement(xpath, changes))
            }
            onImageReplace={(xpath, src, alt) =>
              mutate((ed) => ed.replaceImage(xpath, src, alt))
            }
            onColorApply={(xpath, style) =>
              mutate((ed) => ed.updateElement(xpath, { style }))
            }
            onGlobalColor={(oldColor, newColor) =>
              mutate((ed) => ed.updateGlobalColor(oldColor, newColor))
            }
            onMove={(xpath, direction) =>
              mutate((ed) => ed.moveSection(xpath, direction))
            }
            onDuplicate={(xpath) => mutate((ed) => ed.duplicateSection(xpath))}
            onDelete={(xpath) => {
              mutate((ed) => ed.deleteSection(xpath));
              setSelected(null);
            }}
            onToggleVisibility={(xpath, hidden) =>
              mutate((ed) => ed.updateElement(xpath, { hidden }))
            }
          />
          {demoUrl ? (
            <p className="mt-6 break-all text-[10px] text-cf-muted">
              Live : {demoUrl}
            </p>
          ) : null}
        </aside>
      </div>

      <Modal
        isOpen={Boolean(successUrl)}
        onClose={() => setSuccessUrl(null)}
        title="Site redéployé"
        size="sm"
        footer={
          <Button variant="primary" onClick={() => setSuccessUrl(null)}>
            Fermer
          </Button>
        }
      >
        <p className="text-sm text-cf-muted">
          Votre site est en ligne :
        </p>
        <a
          href={successUrl ?? "#"}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 block break-all text-sm text-cf-gold underline"
        >
          {successUrl}
        </a>
      </Modal>
    </div>
  );
}

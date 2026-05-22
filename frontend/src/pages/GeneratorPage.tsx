import { useCallback, useEffect, useState } from "react";
import { API_PREFIX } from "@shared/constants";
import type { ComplexityLevel, CoreMindRunResponse, ProjectType } from "@shared/types";
import { useBackendHealth } from "@/context/BackendHealthContext";
import { CodeHighlight } from "@/components/CodeHighlight";
import { CodeOutputActions } from "@/components/CodeOutputActions";
import { GenerationHistoryPanel } from "@/components/GenerationHistoryPanel";
import { CreateDemoModal } from "@/components/CreateDemoModal";
import { GeneratorPreviewModal } from "@/components/GeneratorPreviewModal";
import { apiErrorMessage } from "@/lib/api-errors";
import { apiRequest } from "@/lib/api-client";
import {
  createClientDemo,
  type CreateDemoResponse,
  type DemoDuration,
} from "@/lib/demos-api";
import {
  copyTextToClipboard,
  downloadProjectZip,
  zipFilenameFromPrompt,
} from "@/lib/generation-export";
import {
  listGenerationHistory,
  removeGenerationFromHistory,
  saveGenerationToHistory,
  clearGenerationHistory,
  type GenerationHistoryEntry,
} from "@/lib/generation-history";
import { normalizeRunResponse } from "@/lib/normalize-run-response";
import { openCodePreview } from "@/lib/preview";
import { projectTitleFromPrompt } from "@/lib/project-title";
import { PROJECT_TYPE_OPTIONS } from "@/lib/project-types";

type FlowPhase = "idle" | "running" | "done" | "error";

const COMPLEXITY_STYLES: Record<ComplexityLevel, string> = {
  faible: "text-green-400 border-green-400/40 bg-green-400/10",
  moyenne: "text-amber-400 border-amber-400/40 bg-amber-400/10",
  elevee: "text-red-400 border-red-400/40 bg-red-400/10",
};

const EXAMPLE_PROMPT =
  "Crée un site vitrine pour un restaurant italien : menu, réservation en ligne, galerie photos, ambiance sombre et néon discret.";

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function formatCost(usd: number): string {
  if (usd < 0.01) return `~$${usd.toFixed(4)}`;
  return `~$${usd.toFixed(3)}`;
}

function isElectronPreviewAvailable(): boolean {
  return typeof window.cyberforge?.preview?.open === "function";
}

interface GeneratorPageProps {
  onOpenProjects?: () => void;
}

/**
 * Page Générateur — flow complet CoreMindAI.
 */
export function GeneratorPage({ onOpenProjects }: GeneratorPageProps) {
  const { status: backendStatus } = useBackendHealth();
  const [prompt, setPrompt] = useState("");
  const [projectType, setProjectType] = useState<ProjectType>("site_web");
  const [phase, setPhase] = useState<FlowPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [result, setResult] = useState<CoreMindRunResponse | null>(null);
  const [activeFile, setActiveFile] = useState(0);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [copyLabel, setCopyLabel] = useState("Copier le code");
  const [history, setHistory] = useState<GenerationHistoryEntry[]>([]);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [cloudSaved, setCloudSaved] = useState(false);
  const [demoModalOpen, setDemoModalOpen] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);
  const [demoCreated, setDemoCreated] = useState<CreateDemoResponse | null>(null);

  const refreshHistory = useCallback(() => {
    setHistory(listGenerationHistory());
  }, []);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  useEffect(() => {
    if (backendStatus === "offline" && phase === "running") {
      setPhase("error");
      setError(
        "Connexion au backend perdue. Attendez la reconnexion (bandeau orange) puis réessayez.",
      );
    }
  }, [backendStatus, phase]);

  const files =
    result && (result.generation.files?.length ?? 0) > 0
      ? result.generation.files
      : result?.generation.code
        ? [{ path: "src/App.tsx", content: result.generation.code }]
        : [];

  useEffect(() => {
    if (files.length > 0 && activeFile >= files.length) {
      setActiveFile(0);
    }
  }, [activeFile, files.length]);

  const activePath = files[activeFile]?.path ?? "output";
  const displayedCode =
    files[activeFile]?.content ?? result?.generation.code ?? "";

  const isRunning = phase === "running";
  const hasOutput = files.length > 0 && displayedCode.length > 0;

  async function handleGenerate(event?: React.SyntheticEvent) {
    event?.preventDefault();
    const trimmed = prompt.trim();
    if (trimmed.length < 3) {
      setError("Décrivez votre projet en au moins 3 caractères.");
      return;
    }

    setPhase("running");
    setError(null);
    setActionError(null);
    setResult(null);
    setPreviewHtml(null);

    try {
      const response = await apiRequest<CoreMindRunResponse>({
        method: "POST",
        path: `${API_PREFIX}/agents/coremind/run`,
        body: { prompt: trimmed, project_type: projectType },
      });

      if (!response.ok || !response.data) {
        setPhase("error");
        setError(
          apiErrorMessage(
            response,
            "Backend injoignable ou clés LLM manquantes — configurez-les dans Paramètres.",
          ),
        );
        return;
      }

      const entry = saveGenerationToHistory(trimmed, projectType, response.data);
      setLastSavedId(entry.id);
      setCloudSaved(Boolean(response.data.persistence?.project_id));
      refreshHistory();
      setResult(response.data);
      setActiveFile(0);
      setPhase("done");
    } catch (err) {
      setPhase("error");
      setError(
        err instanceof Error
          ? err.message
          : "Erreur inattendue pendant la génération.",
      );
    }
  }

  async function handlePreview() {
    if (!hasOutput) return;
    setActionError(null);
    try {
      const serverPreview = result?.preview_html?.trim();
      if (serverPreview) {
        setPreviewHtml(serverPreview);
        return;
      }
      await openCodePreview(files, {
        title: "Prévisualisation CyberForge",
        onIframe: (html) => setPreviewHtml(html),
      });
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Impossible d'ouvrir l'aperçu visuel.",
      );
    }
  }

  async function handleCopy() {
    if (!displayedCode) return;
    setActionError(null);
    try {
      await copyTextToClipboard(displayedCode);
      setCopyLabel("Copié !");
      window.setTimeout(() => setCopyLabel("Copier le code"), 2000);
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Échec de la copie dans le presse-papiers.",
      );
    }
  }

  function handleExportZip() {
    if (!hasOutput) return;
    setActionError(null);
    try {
      const name = zipFilenameFromPrompt(prompt || "projet");
      downloadProjectZip(files, name);
    } catch (err) {
      setActionError(
        err instanceof Error ? err.message : "Échec de l'export ZIP.",
      );
    }
  }

  function handleRestoreEntry(entry: GenerationHistoryEntry) {
    try {
      const normalized = normalizeRunResponse(entry.result);
      if (!normalized) {
        setActionError(
          "Entrée d'historique invalide ou incomplète — supprimez-la et relancez une génération.",
        );
        return;
      }
      const safeType = PROJECT_TYPE_OPTIONS.some((o) => o.id === entry.projectType)
        ? entry.projectType
        : "site_web";
      setPrompt(entry.prompt);
      setProjectType(safeType);
      setActiveFile(0);
      setResult(normalized);
      setPhase("done");
      setError(null);
      setActionError(null);
      setPreviewHtml(null);
    } catch (err) {
      console.error("[CyberForge] Restaurer", err);
      setActionError(
        err instanceof Error
          ? err.message
          : "Impossible de restaurer cette entrée.",
      );
    }
  }

  function handleRemoveHistory(id: string) {
    removeGenerationFromHistory(id);
    refreshHistory();
    if (lastSavedId === id) setLastSavedId(null);
  }

  function handleClearHistory() {
    clearGenerationHistory();
    refreshHistory();
    setLastSavedId(null);
  }

  function openDemoModal() {
    setDemoCreated(null);
    setDemoError(null);
    setDemoModalOpen(true);
  }

  function closeDemoModal() {
    setDemoModalOpen(false);
    setDemoBusy(false);
    setDemoError(null);
    setDemoCreated(null);
  }

  async function handleCreateDemo(duration: DemoDuration) {
    if (!result || !hasOutput) return;
    setDemoBusy(true);
    setDemoError(null);
    const response = await createClientDemo({
      duration,
      title: projectTitleFromPrompt(prompt),
      files: files.map((f) => ({ path: f.path, content: f.content })),
      stack: result.generation.stack,
      summary: result.generation.summary,
      project_type: result.analysis.project_type,
      code: result.generation.code,
      generation_id: result.persistence?.generation_id ?? null,
    });
    setDemoBusy(false);
    if (!response.ok || !response.data) {
      setDemoError(
        apiErrorMessage(
          response,
          "Impossible de créer la démo (vérifiez Supabase et le backend).",
        ),
      );
      return;
    }
    setDemoCreated(response.data);
  }

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <header>
        <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.35em] text-cyber-violet">
          // coremind_generator_v1
        </p>
        <h1 className="text-2xl font-bold text-cyber-neon md:text-3xl">
          Générateur
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-cyber-muted">
          Un prompt, un type de projet : CoreMindAI analyse la complexité, choisit
          le modèle le moins cher et enregistre chaque génération dans l'historique
          local.
          {isElectronPreviewAvailable()
            ? " L'aperçu visuel s'ouvre dans une fenêtre Electron (maquette HTML)."
            : " L'aperçu visuel s'affiche en maquette HTML dans une iframe."}
        </p>
      </header>

      <section className="cyber-panel overflow-hidden border-cyber-borderGlow p-0">
        <form
          onSubmit={(e) => void handleGenerate(e)}
          className="space-y-6 p-5"
          noValidate
        >
          <div>
            <span className="mb-2 block text-xs font-medium uppercase tracking-wider text-cyber-violet">
              Type de projet
            </span>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {PROJECT_TYPE_OPTIONS.map((option) => (
              <button
                key={option.id}
                type="button"
                disabled={isRunning}
                onClick={() => setProjectType(option.id)}
                className={`cyber-type-pill ${
                  projectType === option.id ? "cyber-type-pill-active" : ""
                }`}
              >
                <span className="block text-sm font-semibold text-cyber-text">
                  {option.label}
                </span>
                <span className="mt-0.5 block text-[10px] text-cyber-muted">
                  {option.description}
                </span>
              </button>
            ))}
            </div>
          </div>

          <label className="block">
            <span className="mb-2 flex items-center justify-between text-xs font-medium uppercase tracking-wider text-cyber-muted">
              <span>Prompt</span>
              <span className="font-mono text-[10px] text-cyber-violet">
                {prompt.trim().length} car.
              </span>
            </span>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={6}
              placeholder={EXAMPLE_PROMPT}
              className="cyber-prompt-field"
              disabled={isRunning}
            />
          </label>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={isRunning || prompt.trim().length < 3}
              className={`cyber-generate-btn ${isRunning ? "cyber-generate-btn-loading" : ""}`}
              onClick={() => void handleGenerate()}
            >
              <span className="relative z-10 flex items-center gap-2">
                {isRunning ? (
                  <>
                    <span
                      className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-cyber-bg border-t-transparent"
                      aria-hidden
                    />
                    Génération…
                  </>
                ) : (
                  "Générer"
                )}
              </span>
            </button>
            <button
              type="button"
              className="rounded-md border border-cyber-border px-3 py-2 text-xs text-cyber-muted hover:border-cyber-accent hover:text-cyber-text"
              onClick={() => {
                setPrompt(EXAMPLE_PROMPT);
                setProjectType("site_web");
              }}
              disabled={isRunning}
            >
              Exemple restaurant
            </button>
            {result ? (
              <button
                type="button"
                className="rounded-md border border-cyber-border px-3 py-2 text-xs text-cyber-muted hover:border-cyber-violet"
                onClick={() => {
                  setResult(null);
                  setError(null);
                  setActionError(null);
                  setPhase("idle");
                  setPreviewHtml(null);
                }}
              >
                Nouveau projet
              </button>
            ) : null}
          </div>

          {error ? (
            <p className="rounded border border-red-400/40 bg-red-400/10 px-3 py-2 text-xs text-red-400">
              {error}
            </p>
          ) : null}
        </form>
      </section>

      {result ? (
        <>
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <MetricTile
              label="Modèle utilisé"
              value={result.metrics.model}
              sub={result.metrics.provider}
              highlight
            />
            <MetricTile
              label="Coût estimé"
              value={formatCost(result.metrics.estimated_cost_usd)}
              sub="indicatif · tokens approx."
            />
            <MetricTile
              label="Complexité"
              value={`${result.metrics.complexity} · ${result.metrics.complexity_score}/10`}
              className={
                COMPLEXITY_STYLES[result.metrics.complexity] ??
                COMPLEXITY_STYLES.moyenne
              }
            />
            <MetricTile
              label="Temps"
              value={formatDuration(result.metrics.duration_ms)}
              sub="génération seule"
            />
          </section>

          <section className="cyber-panel space-y-3 p-5">
            <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-cyber-violet">
              Analyse
            </h2>
            <p className="text-sm text-cyber-text">{result.analysis.summary}</p>
            <p className="text-xs text-cyber-muted">
              Type détecté : {result.analysis.project_type_label}
              {result.metrics.project_type_selected
                ? ` · Sélection : ${result.metrics.project_type_selected}`
                : ""}
              {lastSavedId ? " · Historique local" : ""}
              {cloudSaved ? " · Supabase" : ""}
            </p>
            {cloudSaved && onOpenProjects ? (
              <button
                type="button"
                onClick={onOpenProjects}
                className="text-xs text-cyber-accent underline hover:text-cyber-neon"
              >
                Voir dans Projets →
              </button>
            ) : null}
          </section>

          <section className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <CodeOutputActions
                disabled={!hasOutput}
                copyLabel={copyLabel}
                onPreview={() => void handlePreview()}
                onCopy={() => void handleCopy()}
                onExportZip={handleExportZip}
              />
              <button
                type="button"
                className="cyber-action-btn cyber-action-btn-primary"
                disabled={!hasOutput}
                onClick={openDemoModal}
              >
                Créer une démo client
              </button>
            </div>

            {actionError ? (
              <p className="rounded border border-amber-400/40 bg-amber-400/10 px-3 py-2 text-xs text-amber-300">
                {actionError}
              </p>
            ) : null}

            {files.length > 1 ? (
              <div className="flex flex-wrap gap-2">
                {files.map((file, index) => (
                  <button
                    key={file.path}
                    type="button"
                    onClick={() => setActiveFile(index)}
                    className={`rounded border px-2 py-1 font-mono text-[10px] ${
                      index === activeFile
                        ? "border-cyber-accent bg-cyber-accent/10 text-cyber-neon"
                        : "border-cyber-border text-cyber-muted"
                    }`}
                  >
                    {file.path}
                  </button>
                ))}
              </div>
            ) : null}

            <CodeHighlight code={displayedCode} filePath={activePath} />

            {result.generation.summary ? (
              <p className="text-xs text-cyber-muted">{result.generation.summary}</p>
            ) : null}
          </section>
        </>
      ) : null}

      {isRunning ? (
        <section className="cyber-panel border-cyber-accent/30 p-6 text-center">
          <p className="text-sm text-cyber-neon animate-pulse">
            CoreMindAI analyse, sélectionne le modèle optimal et génère votre code…
          </p>
        </section>
      ) : null}

      <GenerationHistoryPanel
        entries={history}
        onRestore={handleRestoreEntry}
        onRemove={handleRemoveHistory}
        onClear={handleClearHistory}
      />

      {previewHtml ? (
        <GeneratorPreviewModal
          html={previewHtml}
          onClose={() => setPreviewHtml(null)}
        />
      ) : null}

      <CreateDemoModal
        open={demoModalOpen}
        busy={demoBusy}
        created={demoCreated}
        error={demoError}
        onClose={closeDemoModal}
        onCreate={(duration) => void handleCreateDemo(duration)}
      />
    </div>
  );
}

function MetricTile({
  label,
  value,
  sub,
  highlight = false,
  className = "",
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
  className?: string;
}) {
  return (
    <div
      className={`cyber-metric-tile ${highlight ? "cyber-metric-tile-highlight" : ""} ${className}`}
    >
      <p className="text-[10px] uppercase tracking-wider text-cyber-muted">{label}</p>
      <p className="mt-1 font-mono text-sm font-bold text-cyber-text">{value}</p>
      {sub ? <p className="mt-0.5 text-[10px] text-cyber-muted">{sub}</p> : null}
    </div>
  );
}

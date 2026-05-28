import { useCallback, useEffect, useState } from "react";
import type { ComplexityLevel, GenerationMode, PipelineStepEvent } from "@shared/types";
import { useBackendHealth } from "@/context/BackendHealthContext";
import { useGeneratorSession } from "@/context/GeneratorSessionContext";
import { usePipelineActivity } from "@/context/PipelineActivityContext";
import { CodeHighlight } from "@/components/CodeHighlight";
import { CodeOutputActions } from "@/components/CodeOutputActions";
import { CustomizePanel, cloneCustomization } from "@/components/CustomizePanel";
import { GenerationHistoryPanel } from "@/components/GenerationHistoryPanel";
import { CreateDemoModal } from "@/components/CreateDemoModal";
import { GeneratorPreviewModal } from "@/components/GeneratorPreviewModal";
import { PipelineProgress, initialPipelineSteps } from "@/components/PipelineProgress";
import { VisionUIPreview } from "@/components/VisionUIPreview";
import { TestPilotValidationBadge } from "@/components/TestPilotValidationBadge";
import { ExportProductionCard } from "@/components/ExportProductionCard";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  pipelineStreamErrorMessage,
  streamCoremindRun,
} from "@/lib/pipeline-stream";
import {
  createClientDemo,
  type CreateDemoResponse,
  type DemoDuration,
} from "@/lib/demos-api";
import { previewUrlClone } from "@/lib/url-clone-api";
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
import {
  customizationFromSeed,
  mergeCustomizationIntoSeed,
  type DemoCustomization,
} from "@/lib/demo-customization";
import { fetchTaskflowPreviewHtml } from "@/lib/preview-html-api";
import { normalizeRunResponse } from "@/lib/normalize-run-response";
import { projectTitleFromPrompt } from "@/lib/project-title";
import { PROJECT_TYPE_OPTIONS } from "@/lib/project-types";
import { fetchClientBranding } from "@/lib/clients-api";
import {
  clearSelectedClientId,
  getSelectedClientId,
} from "@/lib/selected-client";

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

  useEffect(() => {
    const id = getSelectedClientId();
    setLinkedClientId(id);
    if (!id) {
      setLinkedClientLabel(null);
      setLinkedClientPerso(false);
      return;
    }
    void fetchClientBranding(id).then((response) => {
      if (response.ok && response.data) {
        const label = response.data.company?.trim() || response.data.name;
        setLinkedClientLabel(label);
        setLinkedClientPerso(response.data.kind === "perso");
      }
    });
  }, []);
  const {
    prompt,
    projectType,
    generationMode,
    phase,
    error,
    actionError,
    result,
    activeFile,
    previewHtml,
    livePreviewHtml,
    customizeOpen,
    customization,
    baselineCustomization,
    lastSavedId,
    cloudSaved,
    pipelineSteps,
    visionScreenshotUrl,
    visionPreviewSource,
    visionMessage,
    validationStatus,
    validationSummary,
    testpilotPassed,
    productionUrl,
    exportProvider,
    unlockUrl,
    demoPassword,
    githubExportUrl,
    patch,
    applyPipelineStep,
  } = useGeneratorSession();
  const [copyLabel, setCopyLabel] = useState("Copier le code");
  const [history, setHistory] = useState<GenerationHistoryEntry[]>([]);
  const [demoModalOpen, setDemoModalOpen] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);
  const [demoCreated, setDemoCreated] = useState<CreateDemoResponse | null>(null);
  const [urlCloneUrl, setUrlCloneUrl] = useState("");
  const [urlClonePrompt, setUrlClonePrompt] = useState("");
  const [urlCloneBusy, setUrlCloneBusy] = useState(false);
  const [urlCloneError, setUrlCloneError] = useState<string | null>(null);
  const [linkedClientId, setLinkedClientId] = useState<string | null>(() =>
    getSelectedClientId(),
  );
  const [linkedClientLabel, setLinkedClientLabel] = useState<string | null>(null);
  const [linkedClientPerso, setLinkedClientPerso] = useState(false);
  const [previewRefreshing, setPreviewRefreshing] = useState(false);
  const [customizeSaveBusy, setCustomizeSaveBusy] = useState(false);
  const { dispatchPipelineEvent } = usePipelineActivity();

  const refreshHistory = useCallback(() => {
    setHistory(listGenerationHistory());
  }, []);

  useEffect(() => {
    refreshHistory();
  }, [refreshHistory]);

  useEffect(() => {
    if (backendStatus === "offline" && phase === "running") {
      patch({
        phase: "error",
        error:
          "Connexion au backend perdue. Attendez la reconnexion (bandeau orange) puis réessayez.",
      });
    }
  }, [backendStatus, phase, patch]);

  const files =
    result && (result.generation.files?.length ?? 0) > 0
      ? result.generation.files
      : result?.generation.code
        ? [{ path: "src/App.tsx", content: result.generation.code }]
        : [];

  useEffect(() => {
    if (files.length > 0 && activeFile >= files.length) {
      patch({ activeFile: 0 });
    }
  }, [activeFile, files.length, patch]);

  const activePath = files[activeFile]?.path ?? "output";
  const displayedCode =
    files[activeFile]?.content ?? result?.generation.code ?? "";

  const isRunning = phase === "running";
  const hasOutput = files.length > 0 && displayedCode.length > 0;

  function resolvePreviewHtml(
    run: typeof result,
  ): string | null {
    if (livePreviewHtml?.includes("saas-shell")) return livePreviewHtml;
    const fromServer = run?.preview_html?.trim();
    if (fromServer?.includes("saas-shell")) return fromServer;
    const code = run?.generation.code?.trim();
    if (code?.includes("saas-shell")) return code;
    return fromServer || null;
  }

  async function handleUrlClonePreview() {
    const url = urlCloneUrl.trim();
    if (!url || url.length < 8) return;
    setUrlCloneBusy(true);
    setUrlCloneError(null);
    const response = await previewUrlClone({
      url,
      improved_prompt: urlClonePrompt.trim() || null,
    });
    setUrlCloneBusy(false);
    if (!response.ok || !response.data) {
      setUrlCloneError(apiErrorMessage(response, "Analyse URL impossible."));
      return;
    }
    patch({ previewHtml: response.data.html });
  }

  const effectiveDemoSeed = useCallback(() => {
    if (!result?.generation.demo_seed) return null;
    if (!customization) return result.generation.demo_seed;
    return mergeCustomizationIntoSeed(
      result.generation.demo_seed,
      customization,
    );
  }, [result, customization]);

  useEffect(() => {
    if (!customizeOpen || !customization || !result?.generation.demo_seed) {
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      void (async () => {
        setPreviewRefreshing(true);
        const seed = mergeCustomizationIntoSeed(
          result.generation.demo_seed,
          customization,
        );
        const html = await fetchTaskflowPreviewHtml(seed, {
          prompt: prompt.trim(),
          project_type_label: result.analysis.project_type_label,
        });
        if (!cancelled && html) {
          patch({ livePreviewHtml: html });
        }
        if (!cancelled) setPreviewRefreshing(false);
      })();
    }, 400);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [customizeOpen, customization, result, prompt, patch]);

  const refreshPreviewFromSeed = useCallback(
    async (seed: ReturnType<typeof mergeCustomizationIntoSeed>) => {
      if (!result) return null;
      const html = await fetchTaskflowPreviewHtml(seed, {
        prompt: prompt.trim(),
        project_type_label: result.analysis.project_type_label,
      });
      if (html) {
        patch({ livePreviewHtml: html });
      }
      return html;
    },
    [result, prompt, patch],
  );

  async function handleCustomizationSave() {
    if (!result?.generation.demo_seed || !customization) return;
    setCustomizeSaveBusy(true);
    patch({ actionError: null });
    try {
      const seed = mergeCustomizationIntoSeed(
        result.generation.demo_seed,
        customization,
      );
      const html = await refreshPreviewFromSeed(seed);
      patch({
        result: {
          ...result,
          generation: {
            ...result.generation,
            demo_seed: seed,
            ...(html
              ? {
                  code: html,
                  files: [{ path: "index.html", content: html }],
                }
              : {}),
          },
          ...(html ? { preview_html: html } : {}),
        },
      });
    } catch (err) {
      patch({
        actionError:
          err instanceof Error ? err.message : "Échec de la sauvegarde.",
      });
    } finally {
      setCustomizeSaveBusy(false);
    }
  }

  function handleCustomizationReset() {
    if (!baselineCustomization) return;
    patch({
      customization: cloneCustomization(baselineCustomization),
    });
  }

  async function handleGenerate(event?: React.SyntheticEvent) {
    event?.preventDefault();
    const trimmed = prompt.trim();
    if (trimmed.length < 3) {
      patch({ error: "Décrivez votre projet en au moins 3 caractères." });
      return;
    }

    patch({
      phase: "running",
      error: null,
      actionError: null,
      result: null,
      previewHtml: null,
      customizeOpen: false,
      customization: null,
      livePreviewHtml: null,
      pipelineSteps: initialPipelineSteps(),
      visionScreenshotUrl: null,
      visionPreviewSource: null,
      visionMessage: null,
      validationStatus: null,
      validationSummary: null,
      testpilotPassed: null,
      productionUrl: null,
      exportProvider: null,
      unlockUrl: null,
      demoPassword: null,
      githubExportUrl: null,
    });

    const onStep = (event: PipelineStepEvent) => {
      applyPipelineStep(event);
      dispatchPipelineEvent(event);
      if (event.type === "step_done" && event.agent === "testpilot") {
        const status =
          event.validation_status === "validated" ||
          event.validation_status === "corrected"
            ? event.validation_status
            : null;
        patch({
          validationStatus: status,
          validationSummary: event.message ?? null,
          testpilotPassed: event.ok ?? null,
        });
      }
      if (event.type === "step_done" && event.agent === "export") {
        patch({
          productionUrl: event.production_url ?? null,
          exportProvider: event.export_provider ?? null,
          unlockUrl: event.unlock_url ?? null,
        });
      }
      if (event.type === "step_done" && event.agent === "visionui") {
        const localHtml = event.vision_local_html?.trim();
        patch({
          visionScreenshotUrl: event.vision_screenshot_url ?? null,
          visionPreviewSource: event.vision_preview_source ?? "local",
          visionMessage: event.message ?? null,
          ...(localHtml ? { livePreviewHtml: localHtml } : {}),
        });
      }
    };

    try {
      const response = await streamCoremindRun(
        { prompt: trimmed, project_type: projectType, generation_mode: generationMode },
        { onStep },
      );

      if (!response.ok || !response.data) {
        patch({
          phase: "error",
          error: pipelineStreamErrorMessage(
            response,
            "Backend injoignable ou clés LLM manquantes — configurez-les dans Paramètres.",
          ),
        });
        return;
      }

      const normalized = normalizeRunResponse(response.data);
      if (!normalized) {
        patch({
          phase: "error",
          error: "Réponse backend invalide (génération vide).",
        });
        return;
      }
      const entry = saveGenerationToHistory(trimmed, projectType, normalized);
      refreshHistory();
      const custom = customizationFromSeed(
        normalized.generation.demo_seed,
        projectTitleFromPrompt(trimmed),
      );
      const serverPreview = normalized.preview_html?.trim();
      patch({
        lastSavedId: entry.id,
        cloudSaved: Boolean(normalized.persistence?.project_id),
        result: normalized,
        baselineCustomization: cloneCustomization(custom),
        customization: custom,
        customizeOpen: true,
        activeFile: 0,
        phase: "done",
        ...(serverPreview?.includes("saas-shell")
          ? { previewHtml: serverPreview, livePreviewHtml: serverPreview }
          : {}),
        visionScreenshotUrl: normalized.vision_screenshot_url ?? null,
        visionPreviewSource: normalized.vision_preview_source ?? null,
        visionMessage: null,
        validationStatus: normalized.validation_status ?? null,
        validationSummary: normalized.testpilot_summary ?? null,
        testpilotPassed: normalized.testpilot_passed ?? null,
        productionUrl: normalized.production_url ?? null,
        exportProvider: normalized.export_provider ?? null,
        unlockUrl: normalized.unlock_url ?? null,
        demoPassword: normalized.demo_password ?? null,
        githubExportUrl: normalized.github_export_url ?? null,
      });
    } catch (err) {
      patch({
        phase: "error",
        error:
          err instanceof Error
            ? err.message
            : "Erreur inattendue pendant la génération.",
      });
    }
  }

  async function handlePreview() {
    if (!hasOutput) return;
    patch({ actionError: null });
    const html = resolvePreviewHtml(result);
    if (!html) {
      patch({
        actionError:
          "Aperçu indisponible — relancez une génération pour reconstruire l’aperçu TaskFlow.",
      });
      return;
    }
    patch({ previewHtml: html });
  }

  async function handleCopy() {
    if (!displayedCode) return;
    patch({ actionError: null });
    try {
      await copyTextToClipboard(displayedCode);
      setCopyLabel("Copié !");
      window.setTimeout(() => setCopyLabel("Copier le code"), 2000);
    } catch (err) {
      patch({
        actionError:
          err instanceof Error ? err.message : "Échec de la copie dans le presse-papiers.",
      });
    }
  }

  function handleExportZip() {
    if (!hasOutput) return;
    patch({ actionError: null });
    try {
      const name = zipFilenameFromPrompt(prompt || "projet");
      downloadProjectZip(files, name);
    } catch (err) {
      patch({
        actionError:
          err instanceof Error ? err.message : "Échec de l'export ZIP.",
      });
    }
  }

  function handleRestoreEntry(entry: GenerationHistoryEntry) {
    try {
      const normalized = normalizeRunResponse(entry.result);
      if (!normalized) {
        patch({
          actionError:
            "Entrée d'historique invalide ou incomplète — supprimez-la et relancez une génération.",
        });
        return;
      }
      const safeType = PROJECT_TYPE_OPTIONS.some((o) => o.id === entry.projectType)
        ? entry.projectType
        : "site_web";
      const restoredCustom = customizationFromSeed(
        normalized.generation.demo_seed,
        projectTitleFromPrompt(entry.prompt),
      );
      const restored = normalized.preview_html?.trim();
      patch({
        prompt: entry.prompt,
        projectType: safeType,
        activeFile: 0,
        result: normalized,
        phase: "done",
        error: null,
        actionError: null,
        baselineCustomization: cloneCustomization(restoredCustom),
        customization: restoredCustom,
        customizeOpen: true,
        previewHtml: restored?.includes("saas-shell") ? restored : null,
        livePreviewHtml: restored?.includes("saas-shell") ? restored : null,
      });
    } catch (err) {
      console.error("[CyberForge] Restaurer", err);
      patch({
        actionError:
          err instanceof Error
            ? err.message
            : "Impossible de restaurer cette entrée.",
      });
    }
  }

  function handleRemoveHistory(id: string) {
    removeGenerationFromHistory(id);
    refreshHistory();
    if (lastSavedId === id) patch({ lastSavedId: null });
  }

  function handleClearHistory() {
    clearGenerationHistory();
    refreshHistory();
    patch({ lastSavedId: null });
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
      files: [{ path: "index.html", content: result.generation.code }],
      stack: result.generation.stack,
      summary: result.generation.summary,
      project_type: result.analysis.project_type,
      code: result.generation.code,
      generation_id: result.persistence?.generation_id ?? null,
      prompt: prompt.trim(),
      demo_seed: effectiveDemoSeed() ?? result.generation.demo_seed ?? null,
      client_id: linkedClientId,
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
        {linkedClientId && linkedClientLabel ? (
          <p className="mt-2 inline-flex flex-wrap items-center gap-2 rounded-lg border border-cyber-violet/30 bg-cyber-violet/10 px-3 py-2 text-xs text-cyber-neon">
            Démo pour {linkedClientPerso ? "la fiche perso" : "le client"} :{" "}
            <strong>{linkedClientLabel}</strong>
            {linkedClientPerso ? (
              <span className="rounded-full border border-fuchsia-400/40 bg-fuchsia-400/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-fuchsia-300">
                Perso
              </span>
            ) : null}
            <button
              type="button"
              className="text-cyber-muted underline hover:text-cyber-text"
              onClick={() => {
                clearSelectedClientId();
                setLinkedClientId(null);
                setLinkedClientLabel(null);
                setLinkedClientPerso(false);
              }}
            >
              Détacher
            </button>
          </p>
        ) : null}
        <p className="mt-2 max-w-2xl text-sm text-cyber-muted">
          Un prompt, un type de projet : le pipeline LangGraph enchaîne ArchitectAI,
          les huit agents du pipeline (dont ExportAI pour le déploiement en production),
          avec progression en temps réel.
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
                onClick={() => patch({ projectType: option.id })}
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

          <div>
            <span className="mb-2 block text-xs font-medium uppercase tracking-wider text-cyber-violet">
              Mode de génération
            </span>
            <div className="flex gap-2">
              {(
                [
                  {
                    id: "client_demo" as GenerationMode,
                    label: "Démo client",
                    description: "HTML premium déployé sur Cloudflare",
                  },
                  {
                    id: "real_app" as GenerationMode,
                    label: "Vraie app",
                    description: "React/Next.js déployable (Railway / Vercel)",
                  },
                ] as const
              ).map((mode) => (
                <button
                  key={mode.id}
                  type="button"
                  disabled={isRunning}
                  onClick={() => patch({ generationMode: mode.id })}
                  className={`cyber-type-pill ${generationMode === mode.id ? "cyber-type-pill-active" : ""}`}
                >
                  <span className="block text-sm font-semibold text-cyber-text">
                    {mode.label}
                  </span>
                  <span className="mt-0.5 block text-[10px] text-cyber-muted">
                    {mode.description}
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
              onChange={(e) => patch({ prompt: e.target.value })}
              rows={6}
              placeholder={EXAMPLE_PROMPT}
              className="cyber-prompt-field"
              disabled={isRunning}
            />
          </label>

          <section className="rounded-lg border border-cyber-border bg-cyber-bg/40 p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-cyber-violet">
              URL Clone (beta) · Démo HTML interne
            </p>
            <p className="mt-2 text-xs text-cyber-muted">
              Colle une URL concurrente → extraction (Tavily) → génération d&apos;une landing premium améliorée (preview).
            </p>
            <div className="mt-3 grid gap-2">
              <input
                value={urlCloneUrl}
                onChange={(e) => setUrlCloneUrl(e.target.value)}
                placeholder="https://exemple.com"
                className="cyber-prompt-field h-10 py-2"
                disabled={isRunning || urlCloneBusy}
              />
              <textarea
                value={urlClonePrompt}
                onChange={(e) => setUrlClonePrompt(e.target.value)}
                rows={3}
                placeholder="Optionnel: améliore le copy, ajoute preuve sociale, CTA clair, sections pricing…"
                className="cyber-prompt-field"
                disabled={isRunning || urlCloneBusy}
              />
              {urlCloneError ? (
                <p className="rounded border border-red-400/30 bg-red-400/10 px-3 py-2 text-xs text-red-300">
                  {urlCloneError}
                </p>
              ) : null}
              <div className="flex justify-end">
                <button
                  type="button"
                  className="cyber-action-btn cyber-action-btn-primary"
                  disabled={isRunning || urlCloneBusy || urlCloneUrl.trim().length < 8}
                  onClick={() => void handleUrlClonePreview()}
                >
                  {urlCloneBusy ? "Analyse…" : "Prévisualiser le clone"}
                </button>
              </div>
            </div>
          </section>

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
                patch({ prompt: EXAMPLE_PROMPT, projectType: "site_web" });
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
                  patch({
                    result: null,
                    error: null,
                    actionError: null,
                    phase: "idle",
                    previewHtml: null,
                    livePreviewHtml: null,
                    customizeOpen: false,
                    customization: null,
                  });
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
          <ExportProductionCard
            productionUrl={productionUrl ?? result.production_url}
            exportProvider={exportProvider ?? result.export_provider}
            unlockUrl={unlockUrl ?? result.unlock_url}
            demoPassword={demoPassword ?? result.demo_password}
            githubUrl={githubExportUrl ?? result.github_export_url}
          />

          {(validationStatus || result.validation_status) ? (
            <TestPilotValidationBadge
              status={validationStatus ?? result.validation_status}
              summary={validationSummary ?? result.testpilot_summary}
              passed={testpilotPassed ?? result.testpilot_passed}
            />
          ) : null}

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
                className={`cyber-action-btn ${customizeOpen ? "border-cyber-accent text-cyber-neon" : ""}`}
                disabled={!hasOutput}
                onClick={() => patch({ customizeOpen: !customizeOpen })}
              >
                Personnaliser
              </button>
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

            {customizeOpen && customization ? (
              <CustomizePanel
                value={customization}
                onChange={(next) => patch({ customization: next })}
                previewHtml={livePreviewHtml ?? previewHtml}
                previewLoading={previewRefreshing}
                onSave={() => void handleCustomizationSave()}
                onReset={handleCustomizationReset}
                saveBusy={customizeSaveBusy}
                onOpenFullPreview={() => {
                  const html = livePreviewHtml ?? previewHtml;
                  if (html) patch({ previewHtml: html });
                }}
              />
            ) : null}

            {files.length > 1 ? (
              <div className="flex flex-wrap gap-2">
                {files.map((file, index) => (
                  <button
                    key={file.path}
                    type="button"
                    onClick={() => patch({ activeFile: index })}
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
        <section className="cyber-panel border-cyber-accent/30 space-y-4 p-5">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyber-violet">
            Pipeline LangGraph
          </p>
          <PipelineProgress steps={pipelineSteps} />
        </section>
      ) : null}

      {isRunning && productionUrl ? (
        <ExportProductionCard
          productionUrl={productionUrl}
          exportProvider={exportProvider}
          unlockUrl={unlockUrl}
          demoPassword={demoPassword}
          githubUrl={githubExportUrl}
        />
      ) : null}

      {isRunning && validationStatus ? (
        <TestPilotValidationBadge
          status={validationStatus}
          summary={validationSummary}
          passed={testpilotPassed}
        />
      ) : null}

      {(isRunning || result) &&
      (visionScreenshotUrl || livePreviewHtml || previewHtml) ? (
        <VisionUIPreview
          screenshotUrl={visionScreenshotUrl}
          previewSource={visionPreviewSource}
          html={livePreviewHtml ?? previewHtml ?? result?.preview_html ?? null}
          message={visionMessage ?? undefined}
        />
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
          onClose={() => patch({ previewHtml: null })}
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

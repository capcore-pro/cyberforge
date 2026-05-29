import { useCallback, useEffect, useMemo, useState } from "react";
import type { PipelineStepEvent } from "@shared/types";
import { useBackendHealth } from "@/context/BackendHealthContext";
import { useGeneratorSession } from "@/context/GeneratorSessionContext";
import { usePipelineActivity } from "@/context/PipelineActivityContext";
import { CodeHighlight } from "@/components/CodeHighlight";
import { CodeOutputActions } from "@/components/CodeOutputActions";
import { CustomizePanel, cloneCustomization } from "@/components/CustomizePanel";
import { CreateDemoModal } from "@/components/CreateDemoModal";
import { GeneratorPreviewModal } from "@/components/GeneratorPreviewModal";
import { PipelineProgress, initialPipelineSteps } from "@/components/PipelineProgress";
import {
  PricingWidget,
  type PricingLiveData,
} from "@/components/PricingWidget";
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
import {
  copyTextToClipboard,
  downloadProjectZip,
  zipFilenameFromPrompt,
} from "@/lib/generation-export";
import {
  saveGenerationToHistory,
  type GenerationHistoryEntry,
} from "@/lib/generation-history";
import {
  customizationFromSeed,
  mergeCustomizationIntoSeed,
} from "@/lib/demo-customization";
import { fetchTaskflowPreviewHtml } from "@/lib/preview-html-api";
import { normalizeRunResponse } from "@/lib/normalize-run-response";
import { projectTitleFromPrompt } from "@/lib/project-title";
import { fetchClientBranding } from "@/lib/clients-api";
import {
  clearSelectedClientId,
  getSelectedClientId,
} from "@/lib/selected-client";
import { fetchProjectCosts } from "@/lib/costs-api";
import { architectPlanFromPipelineEvent } from "@/lib/pricing-sse";
import {
  GENERATOR_KINDS,
  getGeneratorKind,
  inferDeployModeFromSession,
  inferKindFromSession,
  resolveGenerationMode,
  syncSessionFromKind,
  type DeployMode,
  type GeneratorKindId,
} from "@/lib/generator-kinds";

const DESCRIPTION_PLACEHOLDER =
  "Décrivez votre projet… (ex : site vitrine pour une boulangerie artisanale à Nantes, ton chaleureux, couleurs chaudes)";

interface GeneratorPageProps {
  onOpenProjects?: () => void;
}

function StepHeading({ step, title }: { step: number; title: string }) {
  return (
    <div className="mb-5 flex items-center gap-3">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-cf-gold/50 bg-cf-active text-sm font-semibold text-cf-gold">
        {step}
      </span>
      <h2 className="text-lg font-medium text-cf-text">{title}</h2>
    </div>
  );
}

/**
 * Page Générateur — parcours en 3 étapes (type, description, génération).
 */
export function GeneratorPage({ onOpenProjects }: GeneratorPageProps) {
  const { status: backendStatus } = useBackendHealth();
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

  const [selectedKind, setSelectedKind] = useState<GeneratorKindId>(() =>
    inferKindFromSession(projectType, generationMode, prompt),
  );
  const [deployMode, setDeployMode] = useState<DeployMode>(() =>
    inferDeployModeFromSession(generationMode),
  );
  const [showSourceCode, setShowSourceCode] = useState(false);
  const [copyLabel, setCopyLabel] = useState("Copier le code");
  const [demoModalOpen, setDemoModalOpen] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);
  const [demoCreated, setDemoCreated] = useState<CreateDemoResponse | null>(null);
  const [linkedClientId, setLinkedClientId] = useState<string | null>(() =>
    getSelectedClientId(),
  );
  const [linkedClientLabel, setLinkedClientLabel] = useState<string | null>(null);
  const [linkedClientPerso, setLinkedClientPerso] = useState(false);
  const [previewRefreshing, setPreviewRefreshing] = useState(false);
  const [customizeSaveBusy, setCustomizeSaveBusy] = useState(false);
  const [runProjectId, setRunProjectId] = useState<string | null>(null);
  const [pricingLive, setPricingLive] = useState<PricingLiveData | null>(null);
  const { dispatchPipelineEvent } = usePipelineActivity();

  const kindOption = useMemo(
    () => getGeneratorKind(selectedKind),
    [selectedKind],
  );

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

  useEffect(() => {
    const synced = syncSessionFromKind(selectedKind, deployMode);
    patch(synced);
  }, [selectedKind, deployMode, patch]);

  useEffect(() => {
    if (phase !== "running" || !runProjectId) return;
    let cancelled = false;

    const poll = async () => {
      const response = await fetchProjectCosts(runProjectId);
      if (cancelled || !response.ok || !response.data) return;
      const d = response.data;
      setPricingLive((prev) => ({
        architectPlan: d.architect_plan ?? prev?.architectPlan ?? null,
        totalEur: d.total_eur,
        byService: d.by_service,
        marginMultiplier: d.margin_multiplier,
        updatedAt: d.updated_at,
      }));
    };

    void poll();
    const intervalId = window.setInterval(() => void poll(), 1500);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [phase, runProjectId]);

  useEffect(() => {
    if (backendStatus === "offline" && phase === "running") {
      patch({
        phase: "error",
        error:
          "Connexion au serveur perdue. Attendez la reconnexion puis réessayez.",
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
  const showGenerationBlock = isRunning || phase === "done" || phase === "error";

  function resolvePreviewHtml(run: typeof result): string | null {
    if (livePreviewHtml?.includes("saas-shell")) return livePreviewHtml;
    const fromServer = run?.preview_html?.trim();
    if (fromServer?.includes("saas-shell")) return fromServer;
    const code = run?.generation.code?.trim();
    if (code?.includes("saas-shell")) return code;
    return fromServer || null;
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
    if (!customizeOpen || !customization || !result?.generation.demo_seed) return;
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
        if (!cancelled && html) patch({ livePreviewHtml: html });
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
      if (html) patch({ livePreviewHtml: html });
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
              ? { code: html, files: [{ path: "index.html", content: html }] }
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
    patch({ customization: cloneCustomization(baselineCustomization) });
  }

  function selectKind(kind: GeneratorKindId) {
    if (isRunning) return;
    setSelectedKind(kind);
    const option = getGeneratorKind(kind);
    if (!prompt.trim() && option.defaultDescription) {
      patch({ prompt: option.defaultDescription });
    }
  }

  function selectDeployMode(mode: DeployMode) {
    if (isRunning) return;
    setDeployMode(mode);
    patch({ generationMode: resolveGenerationMode(selectedKind, mode) });
  }

  async function handleGenerate(event?: React.SyntheticEvent) {
    event?.preventDefault();
    const trimmed = prompt.trim();
    if (trimmed.length < 3) {
      patch({ error: "Décrivez votre projet en au moins 3 caractères." });
      return;
    }

    const sessionProjectId = crypto.randomUUID();
    setRunProjectId(sessionProjectId);
    setPricingLive(null);

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
      if (event.type === "step_done" && event.agent === "architect") {
        const plan = architectPlanFromPipelineEvent(event);
        if (plan) {
          setPricingLive((prev) => ({
            architectPlan: plan,
            totalEur: prev?.totalEur ?? 0,
            byService: prev?.byService ?? {},
            marginMultiplier: prev?.marginMultiplier ?? null,
            updatedAt: prev?.updatedAt ?? null,
          }));
        }
      }
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

    const synced = syncSessionFromKind(selectedKind, deployMode);

    try {
      const response = await streamCoremindRun(
        {
          prompt: trimmed,
          project_type: synced.projectType,
          generation_mode: synced.generationMode,
          project_id: sessionProjectId,
        },
        { onStep },
      );

      if (!response.ok || !response.data) {
        patch({
          phase: "error",
          error: pipelineStreamErrorMessage(
            response,
            "Serveur injoignable ou configuration incomplète — vérifiez les Paramètres.",
          ),
        });
        return;
      }

      const normalized = normalizeRunResponse(response.data);
      if (!normalized) {
        patch({
          phase: "error",
          error: "Réponse invalide (génération vide).",
        });
        return;
      }

      const entry = saveGenerationToHistory(trimmed, synced.projectType, normalized);
      const custom = customizationFromSeed(
        normalized.generation.demo_seed,
        projectTitleFromPrompt(trimmed),
      );
      const serverPreview = normalized.preview_html?.trim();
      const persistedId = normalized.persistence?.project_id;
      if (persistedId) setRunProjectId(persistedId);

      void fetchProjectCosts(persistedId ?? sessionProjectId).then((costsResp) => {
        if (costsResp.ok && costsResp.data) {
          const d = costsResp.data;
          setPricingLive((prev) => ({
            architectPlan: d.architect_plan ?? prev?.architectPlan ?? null,
            totalEur: d.total_eur,
            byService: d.by_service,
            marginMultiplier: d.margin_multiplier,
            updatedAt: d.updated_at,
          }));
        }
      });

      patch({
        lastSavedId: entry.id,
        cloudSaved: Boolean(persistedId),
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
          "Aperçu indisponible — relancez une génération pour reconstruire l’aperçu.",
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
          err instanceof Error ? err.message : "Échec de la copie.",
      });
    }
  }

  function handleExportZip() {
    if (!hasOutput) return;
    patch({ actionError: null });
    try {
      downloadProjectZip(files, zipFilenameFromPrompt(prompt || "projet"));
    } catch (err) {
      patch({
        actionError:
          err instanceof Error ? err.message : "Échec de l'export ZIP.",
      });
    }
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
          "Impossible de créer la démo — vérifiez la configuration.",
        ),
      );
      return;
    }
    setDemoCreated(response.data);
  }

  function resetForNewProject() {
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
    setShowSourceCode(false);
    setPricingLive(null);
    setRunProjectId(null);
  }

  return (
    <div className="mx-auto max-w-6xl space-y-10 pb-10">
      <header>
        <p className="cf-section-label mb-2">Création de projet</p>
        <h1 className="cf-page-title">Générateur</h1>
        {linkedClientId && linkedClientLabel ? (
          <p className="mt-3 inline-flex flex-wrap items-center gap-2 rounded-control border border-cf-gold/30 bg-cf-active px-3 py-2 text-xs text-cf-gold">
            Projet pour {linkedClientPerso ? "la fiche perso" : "le client"} :{" "}
            <strong className="text-cf-text">{linkedClientLabel}</strong>
            <button
              type="button"
              className="text-cf-muted underline hover:text-cf-text"
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
      </header>

      {/* Étape 1 — Type */}
      <section className="rounded-card border border-cf-border-input bg-cf-card p-6 shadow-card">
        <StepHeading step={1} title="Choix du type de projet" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {GENERATOR_KINDS.map((kind) => {
            const selected = selectedKind === kind.id;
            return (
              <button
                key={kind.id}
                type="button"
                disabled={isRunning}
                onClick={() => selectKind(kind.id)}
                className={`flex min-h-[140px] flex-col items-start rounded-card border p-5 text-left transition ${
                  selected
                    ? "border-cf-gold bg-cf-active shadow-gold"
                    : "border-cf-border-input bg-cf-secondary hover:border-cf-gold/40"
                } disabled:cursor-not-allowed disabled:opacity-60`}
              >
                <span
                  className={`mb-3 text-2xl ${selected ? "text-cf-gold" : "text-cf-muted"}`}
                  aria-hidden
                >
                  {kind.icon}
                </span>
                <span className="text-base font-medium text-cf-text">{kind.title}</span>
                <span className="mt-2 text-sm leading-relaxed text-cf-muted">
                  {kind.description}
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {/* Étape 2 — Description */}
      <section className="rounded-card border border-cf-border-input bg-cf-card p-6 shadow-card">
        <StepHeading step={2} title="Description du projet" />

        <label className="block">
          <span className="mb-2 flex items-center justify-between text-xs text-cf-label">
            <span>Votre description</span>
            <span className="tabular-nums text-cf-muted">{prompt.trim().length} car.</span>
          </span>
          <textarea
            value={prompt}
            onChange={(e) => patch({ prompt: e.target.value, error: null })}
            rows={7}
            placeholder={DESCRIPTION_PLACEHOLDER}
            disabled={isRunning}
            className="w-full resize-y rounded-control border border-cf-border-input bg-cf-secondary px-4 py-3 text-sm leading-relaxed text-cf-text placeholder:text-cf-muted focus:border-cf-gold/50 focus:outline-none disabled:opacity-60"
          />
        </label>

        <div className="mt-4 rounded-control border border-cf-border-input bg-cf-secondary/60 p-4">
          <p className="text-xs font-medium text-cf-gold">
            Exemples pour un projet « {kindOption.title} »
          </p>
          <ul className="mt-2 space-y-2">
            {kindOption.examples.map((example) => (
              <li key={example} className="flex gap-2 text-sm text-cf-body">
                <span className="text-cf-gold" aria-hidden>
                  ·
                </span>
                <button
                  type="button"
                  disabled={isRunning}
                  onClick={() => patch({ prompt: example, error: null })}
                  className="text-left hover:text-cf-gold disabled:opacity-60"
                >
                  {example}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-6">
          <p className="mb-3 text-xs font-medium uppercase tracking-wide text-cf-label">
            Mode de déploiement
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              disabled={isRunning}
              onClick={() => selectDeployMode("demo")}
              className={`rounded-card border p-4 text-left transition ${
                deployMode === "demo"
                  ? "border-cf-gold bg-cf-active"
                  : "border-cf-border-input bg-cf-secondary hover:border-cf-gold/40"
              }`}
            >
              <span className="block text-sm font-medium text-cf-text">Mode démo</span>
              <span className="mt-1 block text-xs text-cf-muted">
                Aperçu HTML rapide hébergé sur Cloudflare
              </span>
            </button>
            <button
              type="button"
              disabled={isRunning}
              onClick={() => selectDeployMode("real")}
              className={`rounded-card border p-4 text-left transition ${
                deployMode === "real"
                  ? "border-cf-gold bg-cf-active"
                  : "border-cf-border-input bg-cf-secondary hover:border-cf-gold/40"
              }`}
            >
              <span className="block text-sm font-medium text-cf-text">Vraie app</span>
              <span className="mt-1 block text-xs text-cf-muted">
                Application déployée (Railway / Vercel)
              </span>
            </button>
          </div>
        </div>
      </section>

      {/* Étape 3 — Génération */}
      <section className="rounded-card border border-cf-border-input bg-cf-card p-6 shadow-card">
        <StepHeading step={3} title="Génération" />

        <form onSubmit={(e) => void handleGenerate(e)} noValidate>
          <button
            type="submit"
            disabled={isRunning || prompt.trim().length < 3}
            className={`inline-flex min-w-[240px] items-center justify-center gap-2 rounded-control border border-cf-gold bg-cf-gold px-10 py-4 text-base font-semibold text-cf-main transition hover:bg-cf-gold-hover disabled:cursor-not-allowed disabled:opacity-50 ${
              isRunning ? "opacity-80" : ""
            }`}
          >
            {isRunning ? (
              <>
                <span
                  className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-cf-main border-t-transparent"
                  aria-hidden
                />
                Génération en cours…
              </>
            ) : (
              "Générer mon projet"
            )}
          </button>

          {error ? (
            <p className="mt-4 rounded-control border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
              {error}
            </p>
          ) : null}
        </form>

        {showGenerationBlock ? (
          <div className="mt-8 space-y-6 border-t border-cf-border-input pt-8">
            {isRunning ? (
              <div>
                <p className="mb-3 text-sm text-cf-muted">Progression en temps réel</p>
                <PipelineProgress steps={pipelineSteps} friendly />
              </div>
            ) : null}

            {runProjectId && (isRunning || pricingLive) ? (
              <PricingWidget
                mode="live"
                projectId={runProjectId}
                liveData={pricingLive}
              />
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
              <div>
                <p className="mb-3 text-sm font-medium text-cf-text">Aperçu visuel</p>
                <VisionUIPreview
                  screenshotUrl={visionScreenshotUrl}
                  previewSource={visionPreviewSource}
                  html={livePreviewHtml ?? previewHtml ?? result?.preview_html ?? null}
                  message={visionMessage ?? undefined}
                />
              </div>
            ) : null}

            {result ? (
              <div className="space-y-5">
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

                <div className="rounded-control border border-cf-border-input bg-cf-secondary/40 p-4">
                  <p className="text-sm text-cf-text">{result.analysis.summary}</p>
                  {cloudSaved && onOpenProjects ? (
                    <button
                      type="button"
                      onClick={onOpenProjects}
                      className="mt-3 text-sm text-cf-gold hover:text-cf-gold-hover hover:underline"
                    >
                      Voir dans Projets →
                    </button>
                  ) : null}
                </div>

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
                    className={`rounded-control border px-3 py-2 text-xs transition ${
                      customizeOpen
                        ? "border-cf-gold text-cf-gold"
                        : "border-cf-border-input text-cf-muted hover:text-cf-text"
                    }`}
                    disabled={!hasOutput}
                    onClick={() => patch({ customizeOpen: !customizeOpen })}
                  >
                    Personnaliser
                  </button>
                  <button
                    type="button"
                    className="rounded-control border border-cf-gold/50 bg-cf-active px-3 py-2 text-xs text-cf-gold hover:border-cf-gold"
                    disabled={!hasOutput}
                    onClick={openDemoModal}
                  >
                    Créer une démo client
                  </button>
                  <button
                    type="button"
                    className="rounded-control border border-cf-border-input px-3 py-2 text-xs text-cf-muted hover:text-cf-text"
                    onClick={resetForNewProject}
                  >
                    Nouveau projet
                  </button>
                </div>

                {actionError ? (
                  <p className="rounded-control border border-cf-alert/40 bg-cf-alert/10 px-4 py-3 text-xs text-cf-alert">
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

                {hasOutput ? (
                  <div className="rounded-control border border-cf-border-input">
                    <button
                      type="button"
                      onClick={() => setShowSourceCode((v) => !v)}
                      className="flex w-full items-center justify-between px-4 py-3 text-left text-xs text-cf-muted hover:text-cf-text"
                    >
                      <span>Code source généré</span>
                      <span>{showSourceCode ? "Masquer" : "Afficher"}</span>
                    </button>
                    {showSourceCode ? (
                      <div className="border-t border-cf-border-input p-2">
                        {files.length > 1 ? (
                          <div className="mb-2 flex flex-wrap gap-2 px-2 pt-2">
                            {files.map((file, index) => (
                              <button
                                key={file.path}
                                type="button"
                                onClick={() => patch({ activeFile: index })}
                                className={`rounded border px-2 py-1 font-mono text-[10px] ${
                                  index === activeFile
                                    ? "border-cf-gold bg-cf-active text-cf-gold"
                                    : "border-cf-border-input text-cf-muted"
                                }`}
                              >
                                {file.path}
                              </button>
                            ))}
                          </div>
                        ) : null}
                        <CodeHighlight code={displayedCode} filePath={activePath} />
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}
      </section>

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

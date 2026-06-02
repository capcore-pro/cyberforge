import { useCallback, useEffect, useMemo, useState } from "react";
import type { PipelineStepEvent } from "@shared/types";
import { useBackendHealth } from "@/context/BackendHealthContext";
import { useGeneratorSession } from "@/context/GeneratorSessionContext";
import { usePipelineActivity } from "@/context/PipelineActivityContext";
import { CodeHighlight } from "@/components/CodeHighlight";
import { CodeOutputActions } from "@/components/CodeOutputActions";
import { CustomizePanel, cloneCustomization } from "@/components/CustomizePanel";
import { BackButton } from "@/components/BackButton";
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
import { isOpenHandsEnabled } from "@/lib/openhands-preferences";
import { isPlaywrightEnabled } from "@/lib/playwright-preferences";
import { isLighthouseEnabled } from "@/lib/lighthouse-preferences";
import { isResearchEnabled } from "@/lib/research-preferences";
import { isStitchEnabled } from "@/lib/stitch-preferences";
import { savePlaywrightReport } from "@/lib/playwright-reports";
import { saveLighthouseReport } from "@/lib/lighthouse-reports";
import { PlaywrightScoreBadge } from "@/components/PlaywrightScoreBadge";
import { LighthouseScorePanel } from "@/components/LighthouseScorePanel";
import { DataPaymentPanel } from "@/components/DataPaymentPanel";
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
import {
  pickPreviewHtml,
} from "@/lib/cyberforge-preview";
import { normalizeRunResponse } from "@/lib/normalize-run-response";
import { projectTitleFromPrompt } from "@/lib/project-title";
import { fetchClientBranding, listClients, type ClientRecord } from "@/lib/clients-api";
import { updateProject } from "@/lib/projects-api";
import {
  clearSelectedClientId,
  getSelectedClientId,
  setSelectedClientId,
} from "@/lib/selected-client";
import { fetchProjectCosts } from "@/lib/costs-api";
import { createPersonalProject, USAGE_LABELS, type PersonalUsage } from "@/lib/personal-projects-api";
import { PersoBadge } from "@/components/PersoBadge";
import { architectPlanFromPipelineEvent } from "@/lib/pricing-sse";
import {
  buildGeneratorPipelinePrompt,
  GENERATOR_KINDS,
  getGeneratorKind,
  inferDeployModeFromSession,
  inferKindFromSession,
  kindToToolboxSecteur,
  resolveGenerationMode,
  syncSessionFromKind,
  type DeployMode,
  type GeneratorKindId,
} from "@/lib/generator-kinds";
import {
  cloneFirecrawlInspiration,
  type CloneInspirationResult,
  type ScrapeSectionOut,
} from "@/lib/firecrawl-api";
import { fetchToolboxSecteurs, type SectorData } from "@/lib/toolbox-api";
import {
  computeProjectEstimation,
  formatEur,
} from "@/lib/generator-estimation";

type ProjectOwnerMode = "client" | "perso";

const DESCRIPTION_PLACEHOLDER =
  "Décrivez votre projet… (ex : site vitrine pour une boulangerie artisanale à Nantes, ton chaleureux, couleurs chaudes)";

const SECTION_TYPE_LABELS: Record<string, string> = {
  hero: "hero",
  about: "à propos",
  services: "services",
  pricing: "tarifs",
  contact: "contact",
  testimonials: "témoignages",
  faq: "FAQ",
  other: "autre",
};

const SECTOR_LABELS: Record<string, string> = {
  restauration: "Restauration",
  nautisme: "Nautisme",
  immobilier: "Immobilier",
  sante: "Santé",
  artisanat: "Artisanat",
  beaute: "Beauté",
  sport: "Sport",
  technologie: "Technologie",
  education: "Éducation",
  commerce: "Commerce",
};

function formatStructureSummary(sections: ScrapeSectionOut[]): string {
  const labels = sections.map(
    (s) => SECTION_TYPE_LABELS[s.type] ?? s.type,
  );
  return [...new Set(labels)].join(" + ");
}

function buildPromptFromInspiration(
  result: CloneInspirationResult,
  structureSummary: string,
): string {
  const colors = Object.entries(result.palette)
    .slice(0, 3)
    .map(([key, value]) => `${key} ${value}`)
    .join(", ");
  return [
    `Projet inspiré de ${result.url} pour ${result.nom_client}.`,
    structureSummary ? `Structure cible : ${structureSummary}.` : "",
    colors ? `Palette : ${colors}.` : "",
    "Reproduire le rythme visuel et l'ordre des sections avec une exécution premium CapCore.",
  ]
    .filter(Boolean)
    .join(" ");
}

interface GeneratorPageProps {
  onOpenProjects?: () => void;
  onOpenPerso?: () => void;
  showBackToProjects?: boolean;
  showBackToPerso?: boolean;
  personalMode?: boolean;
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
export function GeneratorPage({
  onOpenProjects,
  onOpenPerso,
  showBackToProjects = false,
  showBackToPerso = false,
  personalMode = false,
}: GeneratorPageProps) {
  const { status: backendStatus } = useBackendHealth();
  const {
    prompt,
    projectName,
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
    playwrightReport,
    lighthouseReport,
    productionUrl,
    exportProvider,
    artifactDownloadUrl,
    unlockUrl,
    demoPassword,
    githubExportUrl,
    personalMode: sessionPersonalMode,
    personalUsage,
    personalPriceEur,
    personalCommercialDescription,
    personalDraftTitle,
    database_schema,
    auth_schema,
    payment_config,
    patch,
    applyPipelineStep,
  } = useGeneratorSession();

  const isPersonal = personalMode || sessionPersonalMode;

  const [projectOwnerMode, setProjectOwnerMode] = useState<ProjectOwnerMode>(() =>
    personalMode || sessionPersonalMode ? "perso" : "client",
  );
  const [clientOptions, setClientOptions] = useState<ClientRecord[]>([]);
  const [clientsLoading, setClientsLoading] = useState(false);
  const [inlinePersoUsage, setInlinePersoUsage] = useState<PersonalUsage>(
    personalUsage ?? "personal",
  );
  const [inlinePersoPrice, setInlinePersoPrice] = useState(
    personalPriceEur != null ? String(personalPriceEur) : "",
  );
  const [inlinePersoDescription, setInlinePersoDescription] = useState(
    personalCommercialDescription ?? "",
  );

  const isPersonalFlow = projectOwnerMode === "perso" || isPersonal;

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
    personalMode ? null : getSelectedClientId(),
  );
  const [linkedClientLabel, setLinkedClientLabel] = useState<string | null>(null);
  const [linkedClientPerso, setLinkedClientPerso] = useState(false);
  const [previewRefreshing, setPreviewRefreshing] = useState(false);
  const [customizeSaveBusy, setCustomizeSaveBusy] = useState(false);
  const [runProjectId, setRunProjectId] = useState<string | null>(null);
  const [pricingLive, setPricingLive] = useState<PricingLiveData | null>(null);
  const [inspirationUrl, setInspirationUrl] = useState("");
  const [inspirationSecteur, setInspirationSecteur] = useState(() =>
    kindToToolboxSecteur(selectedKind),
  );
  const [toolboxSecteurs, setToolboxSecteurs] = useState<SectorData[]>([]);
  const [inspirationAnalyzing, setInspirationAnalyzing] = useState(false);
  const [inspirationError, setInspirationError] = useState<string | null>(null);
  const [inspirationStructureSummary, setInspirationStructureSummary] = useState<
    string | null
  >(null);
  const [inspirationBrief, setInspirationBrief] = useState<string | null>(null);
  const { dispatchPipelineEvent } = usePipelineActivity();

  const kindOption = useMemo(
    () => getGeneratorKind(selectedKind),
    [selectedKind],
  );

  const isExtensionPreview = useMemo(() => {
    if (selectedKind === "extension") return true;
    if (projectType === "extension_navigateur") return true;
    return result?.analysis?.project_type === "extension_navigateur";
  }, [selectedKind, projectType, result?.analysis?.project_type]);

  const estimation = useMemo(
    () => computeProjectEstimation(selectedKind, prompt),
    [selectedKind, prompt],
  );

  const loadClientOptions = useCallback(() => {
    if (clientOptions.length > 0 || clientsLoading) return;
    setClientsLoading(true);
    void listClients("client").then((res) => {
      setClientsLoading(false);
      if (res.ok && res.data) setClientOptions(res.data);
    });
  }, [clientOptions.length, clientsLoading]);

  function selectProjectOwner(mode: ProjectOwnerMode) {
    if (isRunning) return;
    setProjectOwnerMode(mode);
    if (mode === "perso") {
      clearSelectedClientId();
      setLinkedClientId(null);
      setLinkedClientLabel(null);
      setLinkedClientPerso(false);
      patch({
        personalMode: true,
        personalUsage: inlinePersoUsage,
        personalPriceEur:
          inlinePersoUsage === "personal"
            ? null
            : Number.parseFloat(inlinePersoPrice) || null,
        personalCommercialDescription:
          inlinePersoUsage === "personal" ? "" : inlinePersoDescription,
      });
    } else {
      patch({ personalMode: false });
    }
  }

  function handleClientSelect(clientId: string) {
    if (!clientId) {
      clearSelectedClientId();
      setLinkedClientId(null);
      setLinkedClientLabel(null);
      setLinkedClientPerso(false);
      return;
    }
    setSelectedClientId(clientId);
    setLinkedClientId(clientId);
    void fetchClientBranding(clientId).then((response) => {
      if (response.ok && response.data) {
        const label = response.data.company?.trim() || response.data.name;
        setLinkedClientLabel(label);
        setLinkedClientPerso(response.data.kind === "perso");
      }
    });
  }

  useEffect(() => {
    if (isPersonal) return;
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
  }, [isPersonal]);

  useEffect(() => {
    if (!personalMode) return;
    const raw = sessionStorage.getItem("cyberforge.personalProjectDraft");
    if (!raw) {
      patch({ personalMode: true });
      return;
    }
    try {
      const draft = JSON.parse(raw) as {
        usage: PersonalUsage;
        priceEur: number | null;
        commercialDescription: string;
        title: string;
      };
      sessionStorage.removeItem("cyberforge.personalProjectDraft");
      patch({
        personalMode: true,
        personalUsage: draft.usage,
        personalPriceEur: draft.priceEur,
        personalCommercialDescription: draft.commercialDescription,
        personalDraftTitle: draft.title,
        projectName: draft.title,
      });
      clearSelectedClientId();
      setLinkedClientId(null);
      setLinkedClientLabel(null);
    } catch {
      patch({ personalMode: true });
    }
  }, [personalMode, patch]);

  useEffect(() => {
    const synced = syncSessionFromKind(selectedKind, deployMode);
    patch(synced);
  }, [selectedKind, deployMode, patch]);

  const loadToolboxSecteurs = useCallback(() => {
    if (toolboxSecteurs.length > 0) return;
    void fetchToolboxSecteurs().then((res) => {
      if (res.ok && res.data?.secteurs.length) {
        setToolboxSecteurs(res.data.secteurs);
      }
    });
  }, [toolboxSecteurs.length]);

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
    return pickPreviewHtml(
      livePreviewHtml,
      run?.preview_html,
      run?.generation.code,
    );
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
    setInspirationSecteur(kindToToolboxSecteur(kind));
    const option = getGeneratorKind(kind);
    if (!prompt.trim() && option.defaultDescription) {
      patch({ prompt: option.defaultDescription });
    }
  }

  async function handleAnalyzeInspiration() {
    const trimmedUrl = inspirationUrl.trim();
    if (!trimmedUrl) {
      setInspirationError("Indiquez l'URL du site d'inspiration.");
      return;
    }
    setInspirationAnalyzing(true);
    setInspirationError(null);
    setInspirationStructureSummary(null);

    const nomClient =
      linkedClientLabel?.trim() ||
      projectTitleFromPrompt(prompt) ||
      "Mon projet";

    const response = await cloneFirecrawlInspiration({
      url: trimmedUrl,
      secteur: inspirationSecteur,
      nom_client: nomClient,
    });
    setInspirationAnalyzing(false);

    if (!response.ok || !response.data) {
      setInspirationError(
        apiErrorMessage(response, "Analyse du site d'inspiration impossible."),
      );
      return;
    }

    const data = response.data;
    const summary = formatStructureSummary(data.sections);
    setInspirationStructureSummary(summary || null);
    setInspirationBrief(data.brief_builder);

    if (!prompt.trim()) {
      patch({
        prompt: buildPromptFromInspiration(
          data,
          summary ? summary : "sections détectées",
        ),
      });
    }
  }

  function selectDeployMode(mode: DeployMode) {
    if (isRunning) return;
    setDeployMode(mode);
    patch({ generationMode: resolveGenerationMode(selectedKind, mode) });
  }

  async function handleGenerate(event?: React.SyntheticEvent) {
    event?.preventDefault();
    const trimmed = buildGeneratorPipelinePrompt(selectedKind, prompt.trim());
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
      playwrightReport: null,
      lighthouseReport: null,
      productionUrl: null,
      exportProvider: null,
      artifactDownloadUrl: null,
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
      if (event.type === "step_done" && event.agent === "playwright") {
        patch({
          playwrightReport: {
            passed: event.playwright_passed ?? [],
            failed: event.playwright_failed ?? [],
            score: event.playwright_score ?? 0,
            ok: (event.playwright_score ?? 0) >= 70,
          },
        });
      }
      if (event.type === "step_done" && event.agent === "lighthouse") {
        const global = event.lighthouse_score_global ?? 0;
        patch({
          lighthouseReport: {
            performance: event.lighthouse_performance ?? 0,
            seo: event.lighthouse_seo ?? 0,
            accessibility: event.lighthouse_accessibility ?? 0,
            best_practices: event.lighthouse_best_practices ?? 0,
            score_global: global,
            ok: global >= 70,
            recommendations: event.lighthouse_recommendations ?? [],
          },
        });
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
      if (
        event.type === "step_done" &&
        (event.agent === "builder" || event.agent === "extension_build")
      ) {
        const built = pickPreviewHtml(
          typeof event.preview_html === "string" ? event.preview_html : null,
        );
        if (built) {
          patch({ livePreviewHtml: built, visionPreviewSource: "local" });
        }
      }
      if (event.type === "step_done" && event.agent === "export") {
        patch({
          productionUrl: event.production_url ?? null,
          exportProvider: event.export_provider ?? null,
          artifactDownloadUrl: event.artifact_download_url ?? null,
          unlockUrl: event.unlock_url ?? null,
        });
      }
      if (event.type === "step_done" && event.agent === "visionui") {
        const localHtml = event.vision_local_html?.trim();
        const resolved = pickPreviewHtml(localHtml);
        patch({
          visionScreenshotUrl: event.vision_screenshot_url ?? null,
          visionPreviewSource: resolved
            ? "local"
            : (event.vision_preview_source ?? "local"),
          visionMessage: event.message ?? null,
          ...(resolved ? { livePreviewHtml: resolved } : {}),
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
          inspiration_brief: inspirationBrief?.trim() || null,
          personal_project: isPersonalFlow,
          pages_project_slug:
            projectName.trim() ||
            personalDraftTitle.trim() ||
            null,
          project_title:
            projectName.trim() ||
            personalDraftTitle.trim() ||
            projectTitleFromPrompt(trimmed),
          openhands_enabled: isOpenHandsEnabled(),
          playwright_enabled: isPlaywrightEnabled(),
          lighthouse_enabled: isLighthouseEnabled(),
          research_enabled: isResearchEnabled(),
          stitch_enabled: isStitchEnabled(),
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
      const resolvedPreview = pickPreviewHtml(
        serverPreview,
        normalized.generation.code,
      );
      const persistedId = normalized.persistence?.project_id;
      if (persistedId) {
        setRunProjectId(persistedId);
        const customTitle = projectName.trim();
        if (customTitle) {
          void updateProject(persistedId, { title: customTitle });
        }
      }

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
        ...(resolvedPreview
          ? { previewHtml: resolvedPreview, livePreviewHtml: resolvedPreview }
          : {}),
        visionScreenshotUrl: normalized.vision_screenshot_url ?? null,
        visionPreviewSource: normalized.vision_preview_source ?? null,
        visionMessage: null,
        validationStatus: normalized.validation_status ?? null,
        validationSummary: normalized.testpilot_summary ?? null,
        testpilotPassed: normalized.testpilot_passed ?? null,
        playwrightReport: normalized.playwright_report ?? null,
        lighthouseReport: normalized.lighthouse_report ?? null,
        productionUrl: normalized.production_url ?? null,
        exportProvider: normalized.export_provider ?? null,
        artifactDownloadUrl: normalized.artifact_download_url ?? null,
        unlockUrl: normalized.unlock_url ?? null,
        demoPassword: normalized.demo_password ?? null,
        githubExportUrl: normalized.github_export_url ?? null,
      });

      const pwReport = normalized.playwright_report;
      const reportKey = persistedId ?? sessionProjectId;
      if (pwReport && reportKey) {
        savePlaywrightReport(reportKey, pwReport);
      }

      const lhReport = normalized.lighthouse_report;
      if (lhReport && reportKey) {
        saveLighthouseReport(reportKey, lhReport);
      }

      if ((projectOwnerMode === "perso" || isPersonal) && persistedId) {
        const usage = personalUsage ?? inlinePersoUsage;
        const price =
          personalPriceEur ??
          (inlinePersoUsage === "personal"
            ? null
            : Number.parseFloat(inlinePersoPrice) || null);
        const commercial =
          personalCommercialDescription.trim() ||
          inlinePersoDescription.trim() ||
          null;
        void createPersonalProject({
          title:
            projectName.trim() ||
            personalDraftTitle.trim() ||
            projectTitleFromPrompt(trimmed),
          usage_type: usage,
          price_eur: price,
          commercial_description: commercial,
          project_key: `supabase:${persistedId}`,
          supabase_project_id: persistedId,
          ...(normalized.production_url
            ? {
                production_url: normalized.production_url,
                pages_project_slug:
                  projectName.trim() ||
                  personalDraftTitle.trim() ||
                  null,
              }
            : {}),
        });
      }
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
      title: projectName.trim() || projectTitleFromPrompt(prompt),
      files: [{ path: "index.html", content: result.generation.code }],
      stack: result.generation.stack,
      summary: result.generation.summary,
      project_type: result.analysis.project_type,
      code: result.generation.code,
      generation_id: result.persistence?.generation_id ?? null,
      prompt: prompt.trim(),
      demo_seed: effectiveDemoSeed() ?? result.generation.demo_seed ?? null,
      ...(isPersonalFlow ? {} : { client_id: linkedClientId }),
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
      {showBackToPerso && onOpenPerso ? (
        <div className="sticky top-0 z-20 -mx-1 border-b border-fuchsia-500/20 bg-cf-main/95 py-3 backdrop-blur-sm">
          <BackButton onClick={onOpenPerso} label="Retour vers Projets Perso" />
        </div>
      ) : null}
      {showBackToProjects && onOpenProjects ? (
        <div className="sticky top-0 z-20 -mx-1 border-b border-cf-border-input/40 bg-cf-main/95 py-3 backdrop-blur-sm">
          <BackButton onClick={onOpenProjects} label="Retour vers Projets" />
        </div>
      ) : null}
      <header>
        <p className="cf-section-label mb-2">Création de projet</p>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="cf-page-title">Générateur</h1>
          {isPersonalFlow ? <PersoBadge /> : null}
        </div>
        {isPersonalFlow ? (
          <p className="mt-3 inline-flex flex-wrap items-center gap-2 rounded-control border border-fuchsia-400/30 bg-fuchsia-500/10 px-3 py-2 text-xs text-fuchsia-100">
            Projet perso · {USAGE_LABELS[personalUsage ?? inlinePersoUsage]}
            {(personalPriceEur ?? (inlinePersoPrice ? Number.parseFloat(inlinePersoPrice) : null)) !=
            null
              ? ` · ${personalPriceEur ?? inlinePersoPrice} €`
              : ""}
          </p>
        ) : null}
        {!isPersonalFlow && linkedClientId && linkedClientLabel ? (
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

        <div className="mb-6 grid gap-4 sm:grid-cols-2">
          <button
            type="button"
            disabled={isRunning}
            onClick={() => selectProjectOwner("client")}
            className={`flex min-h-[120px] flex-col items-start rounded-card border p-5 text-left transition ${
              projectOwnerMode === "client"
                ? "border-cf-gold bg-cf-active shadow-gold"
                : "border-cf-border-input bg-cf-secondary hover:border-cf-gold/40"
            } disabled:cursor-not-allowed disabled:opacity-60`}
          >
            <span className="text-base font-medium text-cf-text">Projet Client</span>
            <span className="mt-2 text-sm leading-relaxed text-cf-muted">
              Je crée pour un client, je facture — client affilié et estimation prix marché.
            </span>
          </button>
          <button
            type="button"
            disabled={isRunning}
            onClick={() => selectProjectOwner("perso")}
            className={`flex min-h-[120px] flex-col items-start rounded-card border p-5 text-left transition ${
              projectOwnerMode === "perso"
                ? "border-fuchsia-400/60 bg-fuchsia-500/10 shadow-gold"
                : "border-cf-border-input bg-cf-secondary hover:border-fuchsia-400/30"
            } disabled:cursor-not-allowed disabled:opacity-60`}
          >
            <span className="text-base font-medium text-cf-text">Projet Perso</span>
            <span className="mt-2 text-sm leading-relaxed text-cf-muted">
              Je crée pour moi — usage interne, vente one-shot ou abonnement.
            </span>
          </button>
        </div>

        {projectOwnerMode === "client" ? (
          <div className="mb-6 rounded-control border border-cf-border-input bg-cf-secondary/60 p-4">
            <label className="block space-y-1">
              <span className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
                Client affilié
              </span>
              <select
                value={linkedClientId ?? ""}
                onFocus={loadClientOptions}
                onChange={(e) => handleClientSelect(e.target.value)}
                disabled={isRunning}
                className="w-full rounded-control border border-cf-border-input bg-cf-main px-3 py-2.5 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none disabled:opacity-60"
              >
                <option value="">— Sélectionner un client —</option>
                {clientOptions.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.company?.trim() || c.name}
                  </option>
                ))}
              </select>
            </label>
            {clientsLoading ? (
              <p className="mt-2 text-xs text-cf-muted">Chargement des clients…</p>
            ) : null}
            <p className="mt-3 text-xs text-cf-muted">
              Estimation prix marché ({kindOption.title}) :{" "}
              <strong className="text-cf-gold">
                {formatEur(estimation.marketPriceMin)} –{" "}
                {formatEur(estimation.marketPriceMax)}
              </strong>
            </p>
          </div>
        ) : (
          <div className="mb-6 space-y-4 rounded-control border border-fuchsia-400/25 bg-fuchsia-500/5 p-4">
            <fieldset className="space-y-2">
              <legend className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
                Usage
              </legend>
              {(["personal", "one_shot", "subscription"] as PersonalUsage[]).map((usage) => (
                <label key={usage} className="flex cursor-pointer items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="inline-perso-usage"
                    checked={inlinePersoUsage === usage}
                    disabled={isRunning}
                    onChange={() => {
                      setInlinePersoUsage(usage);
                      patch({
                        personalMode: true,
                        personalUsage: usage,
                        personalPriceEur:
                          usage === "personal"
                            ? null
                            : Number.parseFloat(inlinePersoPrice) || null,
                      });
                    }}
                  />
                  {USAGE_LABELS[usage]}
                </label>
              ))}
            </fieldset>
            {inlinePersoUsage !== "personal" ? (
              <>
                <label className="block space-y-1">
                  <span className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
                    Prix (€)
                  </span>
                  <input
                    type="number"
                    min={0}
                    value={inlinePersoPrice}
                    disabled={isRunning}
                    onChange={(e) => {
                      setInlinePersoPrice(e.target.value);
                      patch({
                        personalPriceEur: Number.parseFloat(e.target.value) || null,
                      });
                    }}
                    className="w-full rounded-control border border-cf-border-input bg-cf-main px-3 py-2 text-sm text-cf-text"
                    placeholder={inlinePersoUsage === "subscription" ? "9.99 / mois" : "49"}
                  />
                </label>
                <label className="block space-y-1">
                  <span className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
                    Description commerciale
                  </span>
                  <textarea
                    rows={2}
                    value={inlinePersoDescription}
                    disabled={isRunning}
                    onChange={(e) => {
                      setInlinePersoDescription(e.target.value);
                      patch({ personalCommercialDescription: e.target.value });
                    }}
                    className="w-full resize-y rounded-control border border-cf-border-input bg-cf-main px-3 py-2 text-sm text-cf-text"
                    placeholder="Ce que l'acheteur obtient…"
                  />
                </label>
              </>
            ) : null}
          </div>
        )}

        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-cf-label">
          Type technique
        </p>
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

        <label className="mb-4 block">
          <span className="mb-2 block text-xs text-cf-label">Nom du projet</span>
          <input
            type="text"
            value={projectName}
            onChange={(e) => patch({ projectName: e.target.value })}
            disabled={isRunning}
            placeholder="Ex : Site boulangerie Dupont"
            className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-4 py-2.5 text-sm text-cf-text placeholder:text-cf-muted focus:border-cf-gold/50 focus:outline-none disabled:opacity-60"
          />
        </label>

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

        <div className="mt-5 rounded-control border border-cf-gold/25 bg-cf-active/40 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-cf-gold">
            Estimation
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-cf-label">Complexité</p>
              <p className="mt-1 text-sm font-medium text-cf-text">
                {estimation.complexityLabel}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-cf-label">Coût API</p>
              <p className="mt-1 text-sm font-medium text-cf-text">
                ~{formatEur(estimation.apiCostEur)} en API
              </p>
            </div>
            <div className="sm:col-span-2">
              <p className="text-[10px] uppercase tracking-wider text-cf-label">Hébergement</p>
              <p className="mt-1 text-sm text-cf-text">
                {estimation.hosting.providers.length > 0
                  ? estimation.hosting.providers.join(" + ")
                  : "Aucun"}
                {estimation.hosting.monthlyEur === 0
                  ? " · gratuit"
                  : estimation.hosting.monthlyEur != null
                    ? ` · ~${formatEur(estimation.hosting.monthlyEur)}/mois`
                    : ""}
              </p>
              <p className="mt-1 text-xs text-cf-muted">{estimation.hosting.note}</p>
            </div>
            {projectOwnerMode === "client" ? (
              <div className="sm:col-span-2">
                <p className="text-[10px] uppercase tracking-wider text-cf-label">
                  Prix marché indicatif
                </p>
                <p className="mt-1 text-sm text-cf-gold">
                  {formatEur(estimation.marketPriceMin)} –{" "}
                  {formatEur(estimation.marketPriceMax)}
                </p>
              </div>
            ) : null}
          </div>
        </div>

        <div className="mt-5 rounded-control border border-cf-border-input bg-cf-secondary/60 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-cf-label">
            Site d&apos;inspiration (optionnel)
          </p>
          <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-end">
            <label className="block min-w-0 flex-1">
              <span className="sr-only">URL du site d&apos;inspiration</span>
              <input
                type="url"
                value={inspirationUrl}
                onChange={(e) => {
                  setInspirationUrl(e.target.value);
                  setInspirationError(null);
                }}
                onFocus={loadToolboxSecteurs}
                placeholder="https://site-inspiration.fr"
                disabled={isRunning || inspirationAnalyzing}
                className="w-full rounded-control border border-cf-border-input bg-cf-main px-4 py-2.5 text-sm text-cf-text placeholder:text-cf-muted focus:border-cf-gold/50 focus:outline-none disabled:opacity-60"
              />
            </label>
            {toolboxSecteurs.length > 0 ? (
              <label className="block shrink-0">
                <span className="mb-1 block text-[10px] text-cf-muted">Secteur</span>
                <select
                  value={inspirationSecteur}
                  onChange={(e) => setInspirationSecteur(e.target.value)}
                  disabled={isRunning || inspirationAnalyzing}
                  className="rounded-control border border-cf-border-input bg-cf-main px-3 py-2.5 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none disabled:opacity-60"
                >
                  {toolboxSecteurs.map((s) => (
                    <option key={s.nom} value={s.nom}>
                      {SECTOR_LABELS[s.nom] ?? s.nom}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <button
              type="button"
              disabled={isRunning || inspirationAnalyzing || !inspirationUrl.trim()}
              onClick={() => void handleAnalyzeInspiration()}
              className="shrink-0 whitespace-nowrap rounded-control border border-cf-gold/50 bg-cf-secondary px-4 py-2.5 text-sm font-medium text-cf-gold transition hover:border-cf-gold hover:bg-cf-active disabled:cursor-not-allowed disabled:opacity-60"
            >
              {inspirationAnalyzing ? "Analyse…" : "Analyser"}
            </button>
          </div>

          {inspirationAnalyzing ? (
            <div
              className="mt-4 flex items-center gap-3 rounded-control border border-cf-gold/25 bg-cf-active px-3 py-3"
              role="status"
            >
              <span
                className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-cf-gold border-t-transparent"
                aria-hidden
              />
              <p className="text-sm text-cf-muted">
                Scraping Firecrawl et préparation du brief…
              </p>
            </div>
          ) : null}

          {inspirationError ? (
            <p className="mt-3 text-sm text-red-300">{inspirationError}</p>
          ) : null}

          {inspirationStructureSummary ? (
            <p className="mt-3 text-sm text-cf-text">
              <span className="font-medium text-cf-gold">Structure détectée :</span>{" "}
              {inspirationStructureSummary}
              {inspirationBrief ? (
                <span className="mt-1 block text-xs text-cf-muted">
                  Brief transmis à ArchitectAI au lancement de la génération.
                </span>
              ) : null}
            </p>
          ) : null}
        </div>

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
                {isPersonalFlow
                  ? "Projet Cloudflare Pages dédié (*.pages.dev)"
                  : "Application déployée (Railway / Vercel)"}
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

            {isRunning && (productionUrl || artifactDownloadUrl) ? (
              <ExportProductionCard
                productionUrl={productionUrl}
                exportProvider={exportProvider}
                artifactDownloadUrl={artifactDownloadUrl}
                unlockUrl={unlockUrl}
                demoPassword={demoPassword}
                githubUrl={githubExportUrl}
                onInternalPreview={() => {
                  const html = resolvePreviewHtml(result);
                  if (html) patch({ previewHtml: html });
                }}
                internalPreviewReady={Boolean(resolvePreviewHtml(result))}
              />
            ) : null}

            {isRunning && validationStatus ? (
              <TestPilotValidationBadge
                status={validationStatus}
                summary={validationSummary}
                passed={testpilotPassed}
              />
            ) : null}

            {isRunning && playwrightReport ? (
              <PlaywrightScoreBadge report={playwrightReport} showDetails />
            ) : null}

            {isRunning && lighthouseReport ? (
              <LighthouseScorePanel report={lighthouseReport} />
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
                  extensionPopup={isExtensionPreview}
                />
              </div>
            ) : null}

            <DataPaymentPanel
              databaseSchema={database_schema}
              authSchema={auth_schema}
              paymentConfig={payment_config}
            />

            {result ? (
              <div className="space-y-5">
                <ExportProductionCard
                  productionUrl={productionUrl ?? result.production_url}
                  exportProvider={exportProvider ?? result.export_provider}
                  artifactDownloadUrl={
                    artifactDownloadUrl ?? result.artifact_download_url
                  }
                  unlockUrl={unlockUrl ?? result.unlock_url}
                  demoPassword={demoPassword ?? result.demo_password}
                  githubUrl={githubExportUrl ?? result.github_export_url}
                  onInternalPreview={() => {
                    const html = resolvePreviewHtml(result);
                    if (html) patch({ previewHtml: html });
                  }}
                  internalPreviewReady={Boolean(resolvePreviewHtml(result))}
                />

                {(validationStatus || result.validation_status) ? (
                  <TestPilotValidationBadge
                    status={validationStatus ?? result.validation_status}
                    summary={validationSummary ?? result.testpilot_summary}
                    passed={testpilotPassed ?? result.testpilot_passed}
                  />
                ) : null}

                {(playwrightReport ?? result.playwright_report) ? (
                  <PlaywrightScoreBadge
                    report={playwrightReport ?? result.playwright_report}
                    showDetails
                  />
                ) : null}

                {(lighthouseReport ?? result.lighthouse_report) ? (
                  <LighthouseScorePanel
                    report={lighthouseReport ?? result.lighthouse_report}
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
                  <>
                    <BackButton
                      className="mb-3"
                      onClick={() => patch({ customizeOpen: false })}
                    />
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
                  </>
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

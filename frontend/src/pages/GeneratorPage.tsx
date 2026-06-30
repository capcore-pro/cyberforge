import { useCallback, useEffect, useMemo, useState } from "react";
import type { PipelineStepEvent } from "@shared/types";
import { useBackendHealth } from "@/context/BackendHealthContext";
import { useGeneratorSession } from "@/context/GeneratorSessionContext";
import { usePipelineActivity } from "@/context/PipelineActivityContext";
import { cloneCustomization } from "@/components/CustomizePanel";
import { BackButton } from "@/components/BackButton";
import { GeneratorPreviewModal } from "@/components/GeneratorPreviewModal";
import { initialPipelineSteps } from "@/components/PipelineProgress";
import { GeneratorPipelineProgress } from "@/components/generator/GeneratorPipelineProgress";
import { GeneratorResultCard } from "@/components/generator/GeneratorResultCard";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  pipelineStreamErrorMessage,
  streamCoremindRun,
  type AgentRetryEvent,
} from "@/lib/pipeline-stream";
import { isOpenHandsEnabled } from "@/lib/openhands-preferences";
import { isPlaywrightEnabled } from "@/lib/playwright-preferences";
import { isLighthouseEnabled } from "@/lib/lighthouse-preferences";
import { isResearchEnabled } from "@/lib/research-preferences";
import { savePlaywrightReport } from "@/lib/playwright-reports";
import { saveLighthouseReport } from "@/lib/lighthouse-reports";
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
import { ClientPickerDropdown } from "@/components/generator/ClientPickerDropdown";
import {
  fetchClientBranding,
  fetchClientDetail,
  listClients,
  type ClientRecord,
} from "@/lib/clients-api";
import { StripePublishableKeyField } from "@/components/StripePublishableKeyField";
import { updateProject } from "@/lib/projects-api";
import { downloadDesktopPackage } from "@/lib/editor-api";
import {
  clearSelectedClientId,
  getSelectedClientId,
  setSelectedClientId,
} from "@/lib/selected-client";
import { createPersonalProject, USAGE_LABELS, type PersonalUsage } from "@/lib/personal-projects-api";
import { PersoBadge } from "@/components/PersoBadge";
import {
  buildGeneratorPipelinePrompt,
  GENERATOR_KINDS,
  GENERATOR_KIND_VISUAL,
  getGeneratorKind,
  inferDeployModeFromSession,
  inferKindFromSession,
  persistGeneratorKind,
  INSPIRATION_SECTOR_OPTIONS,
  kindToToolboxSecteur,
  resolveGenerationMode,
  syncSessionFromKind,
  type DeployMode,
  type GeneratorKindId,
} from "@/lib/generator-kinds";
import {
  cloneInspiration,
  scrapeInspiration,
  type CloneInspirationResult,
  type InspirationSectionOut,
  type ScrapeInspirationResult,
} from "@/lib/inspiration-api";
import {
  computeProjectEstimation,
  formatEur,
  type ComplexityTier,
} from "@/lib/generator-estimation";
import { PromptGeneratorPanel } from "@/components/PromptGeneratorPanel";
import {
  buildGeneratorDetailsPrompt,
  detailsFromPreset,
  EMPTY_GENERATOR_DETAILS,
  findSectorPresetForHint,
  getSectorPreset,
  listSectorsForKind,
  type GeneratorDetailsForm,
  type SectorPreset,
  type SectorPresetId,
} from "@/lib/sector-presets";

type ProjectOwnerMode = "client" | "perso";
type WizardStep = "type" | "sector" | "details";

const GLASS_CARD =
  "rounded-card border border-white/10 bg-white/5 backdrop-blur-xl transition-all duration-200";
const GLASS_CARD_INTERACTIVE = `${GLASS_CARD} hover:border-[#d4a843] hover:shadow-[0_0_24px_rgba(212,168,67,0.12)] hover:scale-[1.02] focus:outline-none focus-visible:ring-1 focus-visible:ring-[#d4a843]/40 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:scale-100`;
const GLASS_CARD_SELECTED =
  "border-[#d4a843] bg-[#d4a843]/10 shadow-[0_0_24px_rgba(212,168,67,0.15)] ring-1 ring-[#d4a843]/25";

const PREMIUM_INPUT =
  "w-full rounded-control border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white placeholder:text-white/30 focus:border-[#d4a843] focus:outline-none transition-all duration-200 disabled:opacity-60";
const PREMIUM_TEXTAREA = `${PREMIUM_INPUT} resize-y py-3 leading-relaxed`;

function complexityBadgeClass(tier: ComplexityTier): string {
  switch (tier) {
    case "simple":
      return "border-green-400/40 bg-green-500/15 text-green-300";
    case "medium":
      return "border-emerald-400/35 bg-emerald-500/12 text-emerald-200";
    case "complex":
      return "border-orange-400/40 bg-orange-500/15 text-orange-300";
    case "advanced":
      return "border-red-400/40 bg-red-500/15 text-red-300";
    default:
      return "border-white/20 bg-white/10 text-white/70";
  }
}

function ColorPickerField({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-center gap-3 rounded-control border border-white/10 bg-white/5 p-2 transition-all duration-200 focus-within:border-[#d4a843]">
      <label className="relative shrink-0 cursor-pointer">
        <span
          className="block h-10 w-10 rounded-full border-2 border-white/20 shadow-inner"
          style={{ backgroundColor: value }}
          aria-hidden
        />
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="absolute inset-0 cursor-pointer opacity-0 disabled:cursor-not-allowed"
        />
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="min-w-0 flex-1 border-0 bg-transparent font-mono text-sm text-white placeholder:text-white/30 focus:outline-none disabled:opacity-60"
      />
    </div>
  );
}

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

function formatStructureSummary(sections: InspirationSectionOut[]): string {
  const labels = sections.map(
    (s) => SECTION_TYPE_LABELS[s.type] ?? s.type,
  );
  return [...new Set(labels)].join(" + ");
}

type GenerateLaunchOverrides = {
  prompt?: string;
  projectName?: string;
};

interface GeneratorPageProps {
  onOpenProjects?: () => void;
  onOpenPerso?: () => void;
  showBackToProjects?: boolean;
  showBackToPerso?: boolean;
  personalMode?: boolean;
}

function StepHeading({ step, title }: { step: number; title: string }) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-cf-gold/50 bg-cf-active text-sm font-semibold text-cf-gold">
        {step}
      </span>
      <h2 className="text-lg font-medium text-cf-text">{title}</h2>
    </div>
  );
}

function WizardBreadcrumb({ active }: { active: WizardStep }) {
  const steps: { id: WizardStep; label: string }[] = [
    { id: "type", label: "Type" },
    { id: "sector", label: "Secteur" },
    { id: "details", label: "Détails" },
  ];
  const activeIndex = steps.findIndex((s) => s.id === active);
  return (
    <nav
      className="mb-4 flex flex-wrap items-center gap-2 text-sm"
      aria-label="Étapes du formulaire"
    >
      {steps.map((step, index) => {
        const done = index < activeIndex;
        const current = step.id === active;
        return (
          <span key={step.id} className="inline-flex items-center gap-2">
            {index > 0 ? (
              <span className="text-cf-muted" aria-hidden>
                →
              </span>
            ) : null}
            <span
              className={
                current
                  ? "font-medium text-cf-gold"
                  : done
                    ? "text-cf-text"
                    : "text-cf-muted"
              }
            >
              {step.label}
            </span>
          </span>
        );
      })}
    </nav>
  );
}

function FieldLabel({
  children,
  showSuggestion,
}: {
  children: React.ReactNode;
  showSuggestion?: boolean;
}) {
  return (
    <span className="mb-2 flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-white/50">
      {children}
      {showSuggestion ? (
        <span className="rounded bg-white/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-white/40">
          Suggestion
        </span>
      ) : null}
    </span>
  );
}

function parseServicesLines(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
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
    resetSession,
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
  const [wizardStep, setWizardStep] = useState<WizardStep>("type");
  const [selectedSectorId, setSelectedSectorId] = useState<SectorPresetId | null>(null);
  const [detailsForm, setDetailsForm] =
    useState<GeneratorDetailsForm>(EMPTY_GENERATOR_DETAILS);
  const [touchedFields, setTouchedFields] = useState<Set<string>>(() => new Set());
  const [servicesText, setServicesText] = useState("");
  const [deployMode, setDeployMode] = useState<DeployMode>(() => {
    const inferred = inferDeployModeFromSession(generationMode);
    return inferred === "real" ? inferred : "demo";
  });
  const [generationStartedAt, setGenerationStartedAt] = useState<number | null>(null);
  const [generationDurationMs, setGenerationDurationMs] = useState(0);
  const [agentDurations, setAgentDurations] = useState<Partial<Record<string, number>>>({});
  const [pipelineRetries, setPipelineRetries] = useState<AgentRetryEvent[]>([]);
  const [serverDurationMs, setServerDurationMs] = useState<number | null>(null);
  const [linkedClientId, setLinkedClientId] = useState<string | null>(() =>
    personalMode ? null : getSelectedClientId(),
  );
  const [linkedClientLabel, setLinkedClientLabel] = useState<string | null>(null);
  const [linkedClientPerso, setLinkedClientPerso] = useState(false);
  const [savedSupabaseProjectId, setSavedSupabaseProjectId] = useState<string | null>(null);
  const [desktopDownloadBusy, setDesktopDownloadBusy] = useState(false);
  const [desktopDownloadError, setDesktopDownloadError] = useState<string | null>(null);
  const [stripePrefilledFromClient, setStripePrefilledFromClient] = useState(false);
  const [previewRefreshing, setPreviewRefreshing] = useState(false);
  const [customizeSaveBusy, setCustomizeSaveBusy] = useState(false);
  const [inspirationUrl, setInspirationUrl] = useState("");
  const [inspirationSecteur, setInspirationSecteur] = useState(() =>
    kindToToolboxSecteur(selectedKind),
  );
  const [inspirationAnalyzing, setInspirationAnalyzing] = useState(false);
  const [cloneInspirationBusy, setCloneInspirationBusy] = useState(false);
  const [cloneStatusMessage, setCloneStatusMessage] = useState<string | null>(null);
  const [backClientId, setBackClientId] = useState<string | null>(null);
  const [inspirationScrapeMeta, setInspirationScrapeMeta] =
    useState<ScrapeInspirationResult | null>(null);
  const [inspirationError, setInspirationError] = useState<string | null>(null);
  const [inspirationStructureSummary, setInspirationStructureSummary] = useState<
    string | null
  >(null);
  const [inspirationBrief, setInspirationBrief] = useState<string | null>(null);
  const [inspirationFirecrawl, setInspirationFirecrawl] =
    useState<CloneInspirationResult | null>(null);
  const { dispatchPipelineEvent } = usePipelineActivity();

  const kindOption = useMemo(
    () => getGeneratorKind(selectedKind),
    [selectedKind],
  );

  const sectorPreset = useMemo(
    () => getSectorPreset(selectedSectorId),
    [selectedSectorId],
  );

  useEffect(() => {
    const backId = sessionStorage.getItem("generator_back_client_id");
    if (backId) {
      setBackClientId(backId);
      sessionStorage.removeItem("generator_back_client_id");
    }
  }, []);

  const sectorOptions = useMemo(
    () => listSectorsForKind(selectedKind),
    [selectedKind],
  );

  useEffect(() => {
    if (
      selectedSectorId &&
      !sectorOptions.some((preset) => preset.id === selectedSectorId)
    ) {
      setSelectedSectorId(null);
    }
  }, [selectedSectorId, sectorOptions]);

  const builtPipelinePrompt = useMemo(
    () =>
      buildGeneratorDetailsPrompt(
        selectedKind,
        detailsForm,
        projectName,
        sectorPreset?.label ?? "",
        sectorPreset,
      ),
    [selectedKind, detailsForm, projectName, sectorPreset],
  );

  const isExtensionPreview = useMemo(() => {
    if (selectedKind === "extension") return true;
    if (projectType === "extension_navigateur") return true;
    return result?.analysis?.project_type === "extension_navigateur";
  }, [selectedKind, projectType, result?.analysis?.project_type]);

  const estimation = useMemo(
    () =>
      computeProjectEstimation(
        selectedKind,
        wizardStep === "details" ? builtPipelinePrompt : prompt,
      ),
    [selectedKind, wizardStep, builtPipelinePrompt, prompt],
  );

  const canGenerate =
    projectName.trim().length > 0 &&
    (wizardStep === "details" ? builtPipelinePrompt.trim().length >= 3 : prompt.trim().length >= 3);

  const syncPromptFromDetails = useCallback(
    (
      nextDetails: GeneratorDetailsForm,
      sectorId: SectorPresetId | null,
      clientName: string,
    ) => {
      const preset = getSectorPreset(sectorId);
      patch({
        prompt: buildGeneratorDetailsPrompt(
          selectedKind,
          nextDetails,
          clientName,
          preset?.label ?? "",
        ),
        error: null,
      });
    },
    [selectedKind, patch],
  );

  function markTouched(field: string) {
    setTouchedFields((prev) => {
      if (prev.has(field)) return prev;
      const next = new Set(prev);
      next.add(field);
      return next;
    });
  }

  function updateDetails(
    partial: Partial<GeneratorDetailsForm>,
    touchedKey?: string,
  ) {
    if (touchedKey) markTouched(touchedKey);
    setDetailsForm((prev) => {
      const next = { ...prev, ...partial };
      syncPromptFromDetails(next, selectedSectorId, projectName);
      return next;
    });
  }

  function applySectorPreset(preset: SectorPreset) {
    const next = detailsFromPreset(preset);
    setSelectedSectorId(preset.id);
    setDetailsForm(next);
    setServicesText(next.services.join("\n"));
    setTouchedFields(new Set());
    setWizardStep("details");
    syncPromptFromDetails(next, preset.id, projectName);
    setInspirationSecteur(preset.sector.split("/")[0]?.trim() || inspirationSecteur);
  }

  const loadClientOptions = useCallback(() => {
    if (clientsLoading) return;
    setClientsLoading(true);
    void listClients("client").then((res) => {
      setClientsLoading(false);
      if (res.ok && res.data) setClientOptions(res.data);
    });
  }, [clientsLoading]);

  const handleClientCreated = useCallback((client: ClientRecord) => {
    setClientOptions((prev) => {
      if (prev.some((c) => c.id === client.id)) return prev;
      return [client, ...prev];
    });
    const label = client.company?.trim() || client.name;
    setLinkedClientLabel(label);
    setLinkedClientPerso(client.kind === "perso");
  }, []);

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

  function applyClientStripeKey(clientStripeKey: string | null | undefined) {
    if (touchedFields.has("stripe_publishable_key")) return;
    const key = (clientStripeKey ?? "").trim();
    setDetailsForm((prev) => {
      const next = { ...prev, stripe_publishable_key: key };
      syncPromptFromDetails(next, selectedSectorId, projectName);
      return next;
    });
    setStripePrefilledFromClient(!!key);
  }

  function handleClientSelect(clientId: string) {
    if (!clientId) {
      clearSelectedClientId();
      setLinkedClientId(null);
      setLinkedClientLabel(null);
      setLinkedClientPerso(false);
      setStripePrefilledFromClient(false);
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
    void fetchClientDetail(clientId).then((response) => {
      if (response.ok && response.data) {
        applyClientStripeKey(response.data.stripe_publishable_key);
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
    void fetchClientDetail(id).then((response) => {
      if (response.ok && response.data) {
        applyClientStripeKey(response.data.stripe_publishable_key);
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
    const synced = syncSessionFromKind(selectedKind, deployMode, isPersonalFlow);
    patch(synced);
  }, [selectedKind, deployMode, isPersonalFlow, patch]);

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

  useEffect(() => {
    if (showGenerationBlock) {
      document
        .getElementById("generator-step-4")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [showGenerationBlock]);

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
    persistGeneratorKind(kind);
    setSelectedKind(kind);
    setSelectedSectorId(null);
    setDetailsForm(EMPTY_GENERATOR_DETAILS);
    setServicesText("");
    setTouchedFields(new Set());
    setInspirationSecteur(kindToToolboxSecteur(kind));
    setWizardStep("sector");
    const synced = syncSessionFromKind(kind, deployMode, isPersonalFlow);
    patch({ ...synced, prompt: "", error: null });
  }

  function wizardBack() {
    if (isRunning) return;
    if (wizardStep === "details") {
      setWizardStep("sector");
      return;
    }
    if (wizardStep === "sector") {
      setWizardStep("type");
      setSelectedSectorId(null);
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
    setInspirationScrapeMeta(null);
    setCloneStatusMessage(null);

    const response = await scrapeInspiration({ url: trimmedUrl });
    setInspirationAnalyzing(false);

    if (!response.ok || !response.data) {
      setInspirationError(
        apiErrorMessage(response, "Analyse du site d'inspiration impossible."),
      );
      return;
    }

    const data = response.data;
    setInspirationScrapeMeta(data);

    const partial: Partial<GeneratorDetailsForm> = {};
    if (!detailsForm.description.trim() && data.description?.trim()) {
      partial.description = data.description.trim();
    }
    if (!detailsForm.couleur_primaire.trim() && data.primary_color?.trim()) {
      partial.couleur_primaire = data.primary_color.trim();
    }
    if (Object.keys(partial).length > 0) {
      updateDetails(partial);
    }
    if (wizardStep !== "details") {
      setWizardStep("details");
    }
  }

  function applyCloneToForm(data: CloneInspirationResult) {
    const preset = findSectorPresetForHint(
      data.sector_label || data.secteur,
      selectedKind,
    );
    if (preset) {
      setSelectedSectorId(preset.id);
      setInspirationSecteur(preset.sector.split("/")[0]?.trim() || data.secteur);
    } else {
      setInspirationSecteur(data.secteur);
    }

    const nextDetails: GeneratorDetailsForm = {
      description: data.description,
      services: data.services.length > 0 ? data.services : [],
      couleur_primaire: data.couleur_primaire,
      couleur_secondaire: data.couleur_secondaire,
      ville: data.ville,
      phone: data.phone,
      email: data.email,
      address: data.address,
      stripe_publishable_key: detailsForm.stripe_publishable_key,
    };
    setDetailsForm(nextDetails);
    setServicesText(nextDetails.services.join("\n"));
    setTouchedFields(new Set());
    setWizardStep("details");

    const clientName = data.company_name.trim() || data.client_name.trim();
    if (clientName) {
      patch({ projectName: clientName, error: null });
    }
    syncPromptFromDetails(nextDetails, preset?.id ?? selectedSectorId, clientName || projectName);

    const summary = formatStructureSummary(data.sections);
    setInspirationStructureSummary(summary || null);
    setInspirationBrief(data.brief_builder);
    setInspirationFirecrawl(data);
  }

  async function handleCloneInspiration() {
    const trimmedUrl = inspirationUrl.trim();
    if (!trimmedUrl) {
      setInspirationError("Indiquez l'URL du site à cloner.");
      return;
    }
    const clientName = projectName.trim();
    if (!clientName) {
      setInspirationError("Indiquez le nom du client avant de cloner le site.");
      return;
    }

    setCloneInspirationBusy(true);
    setInspirationAnalyzing(false);
    setInspirationError(null);
    setCloneStatusMessage(
      "Analyse en cours… CyberForge va recréer ce site en mieux.",
    );

    const response = await cloneInspiration({
      url: trimmedUrl,
      project_type: selectedKind,
      client_name: clientName,
    });
    setCloneInspirationBusy(false);

    if (!response.ok || !response.data) {
      setCloneStatusMessage(null);
      setInspirationError(
        apiErrorMessage(response, "Clone du site d'inspiration impossible."),
      );
      return;
    }

    applyCloneToForm(response.data);
    setCloneStatusMessage(null);

    const preset = findSectorPresetForHint(
      response.data.sector_label || response.data.secteur,
      selectedKind,
    );
    const launchDetails: GeneratorDetailsForm = {
      description: response.data.description,
      services:
        response.data.services.length > 0 ? response.data.services : [],
      couleur_primaire: response.data.couleur_primaire,
      couleur_secondaire: response.data.couleur_secondaire,
      ville: response.data.ville,
      phone: response.data.phone,
      email: response.data.email,
      address: response.data.address,
      stripe_publishable_key: detailsForm.stripe_publishable_key,
    };
    const launchPrompt = buildGeneratorDetailsPrompt(
      selectedKind,
      launchDetails,
      response.data.company_name.trim() || clientName,
      preset?.label ?? response.data.secteur,
    );

    void handleGenerate(undefined, {
      prompt: launchPrompt,
      projectName: response.data.company_name.trim() || clientName,
    });
  }

  function selectDeployMode(mode: DeployMode) {
    if (isRunning) return;
    setDeployMode(mode);
    patch({ generationMode: resolveGenerationMode(selectedKind, mode, isPersonalFlow) });
  }

  async function handleGenerate(
    event?: React.SyntheticEvent,
    overrides?: GenerateLaunchOverrides,
  ) {
    event?.preventDefault();
    const effectiveProjectName = overrides?.projectName?.trim() || projectName.trim();
    if (!effectiveProjectName) {
      patch({ error: "Indiquez le nom du client pour lancer la génération." });
      return;
    }
    const trimmed =
      overrides?.prompt?.trim() ||
      (wizardStep === "details"
        ? builtPipelinePrompt.trim()
        : buildGeneratorPipelinePrompt(selectedKind, prompt.trim()));
    if (trimmed.length < 3) {
      patch({
        error:
          "Complétez la description du projet (au moins quelques caractères utiles).",
      });
      return;
    }
    patch({ prompt: trimmed });

    const startedAt = Date.now();
    setGenerationStartedAt(startedAt);
    setGenerationDurationMs(0);
    setAgentDurations({});
    setPipelineRetries([]);
    setServerDurationMs(null);

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

    const synced = syncSessionFromKind(selectedKind, deployMode, isPersonalFlow);

    try {
      const response = await streamCoremindRun(
        {
          prompt: trimmed,
          project_type: synced.projectType,
          generation_mode: synced.generationMode,
          inspiration_brief: inspirationBrief?.trim() || null,
          firecrawl_result: inspirationFirecrawl
            ? {
                url: inspirationFirecrawl.url,
                secteur: inspirationFirecrawl.secteur,
                palette: inspirationFirecrawl.palette,
                couleurs: inspirationFirecrawl.palette,
              }
            : null,
          personal_project: isPersonalFlow,
          pages_project_slug:
            effectiveProjectName ||
            personalDraftTitle.trim() ||
            null,
          project_title:
            effectiveProjectName ||
            personalDraftTitle.trim() ||
            projectTitleFromPrompt(trimmed),
          openhands_enabled: isOpenHandsEnabled(),
          playwright_enabled: isPlaywrightEnabled(),
          lighthouse_enabled: isLighthouseEnabled(),
          research_enabled: isResearchEnabled(),
          stripe_publishable_key:
            selectedKind === "ecommerce" && detailsForm.stripe_publishable_key.trim()
              ? detailsForm.stripe_publishable_key.trim()
              : null,
        },
        {
          onStep,
          onAgentRetry: (event) => {
            setPipelineRetries((prev) => [...prev, event]);
          },
          onAgentDuration: (agent, durationMs) => {
            setAgentDurations((prev) => ({ ...prev, [agent]: durationMs }));
          },
          onServerDuration: (durationMs) => {
            setServerDurationMs(durationMs);
            setGenerationDurationMs(durationMs);
          },
        },
      );

      if (!response.ok || !response.data) {
        setGenerationDurationMs(Date.now() - startedAt);
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
        setGenerationDurationMs(Date.now() - startedAt);
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
      setSavedSupabaseProjectId(persistedId ?? null);
      if (persistedId) {
        if (effectiveProjectName) {
          void updateProject(persistedId, { title: effectiveProjectName });
        }
      }

      setGenerationDurationMs(Date.now() - startedAt);

      patch({
        lastSavedId: entry.id,
        cloudSaved: Boolean(persistedId),
        result: normalized,
        baselineCustomization: cloneCustomization(custom),
        customization: custom,
        customizeOpen: false,
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
      const reportKey = persistedId ?? entry.id;
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
      setGenerationDurationMs(Date.now() - startedAt);
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

  function resetForNewProject() {
    if (isRunning) return;
    resetSession();
    persistGeneratorKind("vitrine");
    setSelectedKind("vitrine");
    setWizardStep("type");
    setSelectedSectorId(null);
    setDetailsForm(EMPTY_GENERATOR_DETAILS);
    setServicesText("");
    setTouchedFields(new Set());
    setDeployMode("demo");
    setGenerationStartedAt(null);
    setGenerationDurationMs(0);
    setInspirationUrl("");
    setInspirationError(null);
    setInspirationScrapeMeta(null);
    setInspirationStructureSummary(null);
    setInspirationBrief(null);
    setInspirationFirecrawl(null);
    setCloneStatusMessage(null);
  }

  return (
    <div className="mx-auto max-w-6xl scroll-smooth space-y-6 pb-8">
      {backClientId ? (
        <button
          type="button"
          onClick={() => {
            sessionStorage.setItem("open_client_id", backClientId);
            window.location.hash = "#/clients";
          }}
          className="mb-4 flex items-center gap-2 text-sm text-cf-muted transition-colors hover:text-cf-text"
        >
          ← Retour à la fiche client
        </button>
      ) : null}
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
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
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
        </div>
        <button
          type="button"
          disabled={isRunning}
          onClick={resetForNewProject}
          className="shrink-0 rounded-control border border-[#d4a843] bg-transparent px-4 py-2 text-sm font-medium text-[#d4a843] transition-all duration-200 hover:bg-[#d4a843]/10 disabled:cursor-not-allowed disabled:opacity-50"
        >
          ＋ Nouveau projet
        </button>
      </header>

      {wizardStep !== "type" ? (
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            disabled={isRunning}
            onClick={wizardBack}
            className="rounded-control border border-cf-border-input bg-cf-secondary px-4 py-2 text-sm text-cf-text transition hover:border-cf-gold/40 disabled:opacity-60"
          >
            ← Retour
          </button>
          {wizardStep === "sector" && kindOption ? (
            <p className="text-sm text-cf-muted">
              Type : <span className="text-cf-text">{kindOption.title}</span>
            </p>
          ) : null}
          {wizardStep === "details" && sectorPreset ? (
            <p className="text-sm text-cf-muted">
              {kindOption.title} ·{" "}
              <span className="text-cf-text">
                {sectorPreset.emoji} {sectorPreset.label}
              </span>
            </p>
          ) : null}
        </div>
      ) : null}

      {/* Étape 1 — Type */}
      {wizardStep === "type" ? (
      <section className={`${GLASS_CARD} p-5`}>
        <WizardBreadcrumb active="type" />
        <StepHeading step={1} title="Choix du type de projet" />

        <div className="mb-4 grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            disabled={isRunning}
            onClick={() => selectProjectOwner("client")}
            className={`flex min-h-[104px] flex-col items-start p-4 text-left ${GLASS_CARD_INTERACTIVE} ${
              projectOwnerMode === "client" ? GLASS_CARD_SELECTED : ""
            }`}
          >
            <span className="text-base font-semibold text-cf-text">Projet Client</span>
            <span className="mt-1.5 text-sm leading-snug text-cf-muted">
              Client facturable, affiliation et prix marché.
            </span>
          </button>
          <button
            type="button"
            disabled={isRunning}
            onClick={() => selectProjectOwner("perso")}
            className={`flex min-h-[104px] flex-col items-start p-4 text-left ${GLASS_CARD_INTERACTIVE} ${
              projectOwnerMode === "perso" ? GLASS_CARD_SELECTED : ""
            }`}
          >
            <span className="text-base font-semibold text-cf-text">Projet Perso</span>
            <span className="mt-1.5 text-sm leading-snug text-cf-muted">
              Usage perso ou revente — sans client affilié.
            </span>
          </button>
        </div>

        {projectOwnerMode === "client" ? (
          <div className={`relative z-20 mb-4 space-y-3 ${GLASS_CARD} p-4`}>
            <label className="relative block space-y-2">
              <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cf-label">
                Client affilié
              </span>
              <ClientPickerDropdown
                clients={clientOptions}
                loading={clientsLoading}
                value={linkedClientId}
                disabled={isRunning}
                onOpen={loadClientOptions}
                onSelect={handleClientSelect}
                onClientCreated={handleClientCreated}
              />
            </label>
            <p className="text-xs text-cf-muted">
              Estimation prix marché ({kindOption.title}) :{" "}
              <strong className="text-cf-gold">
                {formatEur(estimation.marketPriceMin)} –{" "}
                {formatEur(estimation.marketPriceMax)}
              </strong>
            </p>
          </div>
        ) : (
          <div className={`mb-4 space-y-3 ${GLASS_CARD} p-4`}>
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

        <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-cf-label">
          Type technique
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {GENERATOR_KINDS.map((kind) => {
            const selected = selectedKind === kind.id;
            const visual = GENERATOR_KIND_VISUAL[kind.id];
            return (
              <button
                key={kind.id}
                type="button"
                disabled={isRunning}
                onClick={() => selectKind(kind.id)}
                className={`flex min-h-[128px] flex-col items-start p-4 text-left ${GLASS_CARD_INTERACTIVE} ${
                  selected ? `${GLASS_CARD_SELECTED} ring-2 ${visual.ringClass}` : ""
                }`}
              >
                <span
                  className={`mb-2 text-2xl ${selected ? visual.colorClass : "text-cf-muted"}`}
                  aria-hidden
                >
                  {visual.emoji}
                </span>
                <span className="text-base font-semibold text-cf-text">{kind.title}</span>
                <span className="mt-1.5 text-sm leading-snug text-cf-muted">
                  {visual.shortDescription}
                </span>
              </button>
            );
          })}
        </div>
      </section>
      ) : null}

      {/* Étape 2 — Secteur */}
      {wizardStep === "sector" ? (
        <section key={`sector-step-${selectedKind}`} className={`${GLASS_CARD} p-5`}>
          <WizardBreadcrumb active="sector" />
          <StepHeading step={2} title="Choix du secteur" />
          <p className="mb-4 text-sm text-cf-muted">
            Projet « {kindOption.title} » — pré-remplit le formulaire (modifiable ensuite).
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {listSectorsForKind(selectedKind).map((preset) => {
              const selected = selectedSectorId === preset.id;
              return (
                <button
                  key={preset.id}
                  type="button"
                  disabled={isRunning}
                  onClick={() => applySectorPreset(preset)}
                  className={`flex min-h-[120px] flex-col items-start p-4 text-left ${GLASS_CARD_INTERACTIVE} ${
                    selected ? GLASS_CARD_SELECTED : ""
                  }`}
                >
                  <span className="mb-2 text-2xl" aria-hidden>
                    {preset.emoji}
                  </span>
                  <span className="text-base font-medium text-cf-text">{preset.label}</span>
                  <span className="mt-1.5 line-clamp-2 text-sm leading-snug text-cf-muted">
                    {preset.description}
                  </span>
                </button>
              );
            })}
          </div>
        </section>
      ) : null}

      {/* Étape 3 — Détails */}
      {wizardStep === "details" ? (
      <section className={`${GLASS_CARD} p-5`}>
        <WizardBreadcrumb active="details" />
        <StepHeading step={3} title="Détails du projet" />

        <label className="mb-4 block">
          <FieldLabel>Nom du client</FieldLabel>
          <input
            type="text"
            value={projectName}
            onChange={(e) => {
              const name = e.target.value;
              patch({ projectName: name, error: null });
              syncPromptFromDetails(detailsForm, selectedSectorId, name);
            }}
            disabled={isRunning}
            placeholder="Ex : Camping Les Pins"
            className={PREMIUM_INPUT}
          />
        </label>

        <label className="mb-4 block">
          <FieldLabel showSuggestion={!touchedFields.has("description")}>
            Description
          </FieldLabel>
          <textarea
            value={detailsForm.description}
            onChange={(e) => updateDetails({ description: e.target.value }, "description")}
            rows={4}
            disabled={isRunning}
            className={PREMIUM_TEXTAREA}
          />
        </label>

        <label className="mb-4 block">
          <FieldLabel showSuggestion={!touchedFields.has("services")}>
            Services (un par ligne)
          </FieldLabel>
          <textarea
            value={servicesText}
            onChange={(e) => {
              const text = e.target.value;
              setServicesText(text);
              updateDetails({ services: parseServicesLines(text) }, "services");
            }}
            rows={5}
            disabled={isRunning}
            placeholder={"Mobil-homes\nChalets\nPiscine"}
            className={PREMIUM_TEXTAREA}
          />
        </label>

        <div className="mb-4 grid gap-4 sm:grid-cols-2">
          <label className="block">
            <FieldLabel showSuggestion={!touchedFields.has("couleur_primaire")}>
              Couleur primaire
            </FieldLabel>
            <ColorPickerField
              value={detailsForm.couleur_primaire}
              onChange={(v) => updateDetails({ couleur_primaire: v }, "couleur_primaire")}
              disabled={isRunning}
            />
          </label>
          <label className="block">
            <FieldLabel showSuggestion={!touchedFields.has("couleur_secondaire")}>
              Couleur secondaire
            </FieldLabel>
            <ColorPickerField
              value={detailsForm.couleur_secondaire}
              onChange={(v) =>
                updateDetails({ couleur_secondaire: v }, "couleur_secondaire")
              }
              disabled={isRunning}
            />
          </label>
        </div>

        <div className="mb-4 grid gap-4 sm:grid-cols-2">
          <label className="block">
            <FieldLabel>Ville</FieldLabel>
            <input
              type="text"
              value={detailsForm.ville}
              onChange={(e) => updateDetails({ ville: e.target.value }, "ville")}
              disabled={isRunning}
              placeholder="Ex : Annecy"
              className={PREMIUM_INPUT}
            />
          </label>
          <label className="block">
            <FieldLabel>Téléphone</FieldLabel>
            <input
              type="tel"
              value={detailsForm.phone}
              onChange={(e) => updateDetails({ phone: e.target.value }, "phone")}
              disabled={isRunning}
              placeholder="06 …"
              className={PREMIUM_INPUT}
            />
          </label>
          <label className="block sm:col-span-2">
            <FieldLabel>Email</FieldLabel>
            <input
              type="email"
              value={detailsForm.email}
              onChange={(e) => updateDetails({ email: e.target.value }, "email")}
              disabled={isRunning}
              placeholder="contact@…"
              className={PREMIUM_INPUT}
            />
          </label>
          <label className="block sm:col-span-2">
            <FieldLabel>Adresse</FieldLabel>
            <input
              type="text"
              value={detailsForm.address}
              onChange={(e) => updateDetails({ address: e.target.value }, "address")}
              disabled={isRunning}
              placeholder="Rue, code postal…"
              className={PREMIUM_INPUT}
            />
          </label>
        </div>

        {selectedKind === "ecommerce" ? (
          <div className="mb-4 rounded-control border border-white/10 bg-white/[0.03] p-4">
            <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/45">
              Paiement Stripe
            </h3>
            <StripePublishableKeyField
              value={detailsForm.stripe_publishable_key}
              onChange={(value) => {
                setStripePrefilledFromClient(false);
                updateDetails({ stripe_publishable_key: value }, "stripe_publishable_key");
              }}
              disabled={isRunning}
              fromClientBadge={stripePrefilledFromClient && !!detailsForm.stripe_publishable_key.trim()}
            />
            <p className="mt-2 text-xs text-white/40">
              Laissez vide pour conserver un panier local sans paiement en ligne.
            </p>
          </div>
        ) : null}

        <PromptGeneratorPanel
          disabled={isRunning}
          selectedKind={selectedKind}
          onSelectKind={(kind) => {
            selectKind(kind);
          }}
          onPromptGenerated={(generated) => {
            patch({ prompt: generated, error: null });
            markTouched("description");
          }}
        />

        <details className="mt-4 rounded-control border border-cf-border-input bg-cf-secondary/40 p-3">
          <summary className="cursor-pointer text-xs font-medium text-cf-muted">
            Aperçu du prompt envoyé ({builtPipelinePrompt.trim().length} car.)
          </summary>
          <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap text-xs text-cf-body">
            {builtPipelinePrompt.trim() || "—"}
          </pre>
        </details>

        <div className={`mt-5 ${GLASS_CARD} p-4`}>
          <p className="text-xs font-semibold uppercase tracking-wide text-[#d4a843]">
            Estimation
          </p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="flex items-start gap-3">
              <span className="text-lg" aria-hidden>
                📊
              </span>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-white/50">
                  Complexité
                </p>
                <span
                  className={`mt-1.5 inline-flex rounded-full border px-2.5 py-0.5 text-xs font-medium ${complexityBadgeClass(estimation.complexityTier)}`}
                >
                  {estimation.complexityLabel}
                </span>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-lg" aria-hidden>
                ⚡
              </span>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-white/50">
                  Coût API
                </p>
                <p className="mt-1 text-sm font-medium text-white">
                  ~{formatEur(estimation.apiCostEur)}
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 sm:col-span-2">
              <span className="text-lg" aria-hidden>
                ☁️
              </span>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-white/50">
                  Hébergement
                </p>
                <p className="mt-1 text-sm text-white">
                  {estimation.hosting.providers.length > 0
                    ? estimation.hosting.providers.join(" + ")
                    : "Aucun"}
                  {estimation.hosting.monthlyEur === 0
                    ? " · gratuit"
                    : estimation.hosting.monthlyEur != null
                      ? ` · ~${formatEur(estimation.hosting.monthlyEur)}/mois`
                      : ""}
                </p>
                <p className="mt-0.5 text-xs text-white/45">{estimation.hosting.note}</p>
              </div>
            </div>
            {projectOwnerMode === "client" ? (
              <div className="flex items-start gap-3 sm:col-span-2">
                <span className="text-lg" aria-hidden>
                  💰
                </span>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-white/50">
                    Prix marché indicatif
                  </p>
                  <p className="mt-1 text-base font-semibold text-[#d4a843]">
                    {formatEur(estimation.marketPriceMin)} –{" "}
                    {formatEur(estimation.marketPriceMax)}
                  </p>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <div className={`mt-5 ${GLASS_CARD} p-4`}>
          <p className="text-xs font-semibold uppercase tracking-wide text-white/50">
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
                placeholder="https://site-inspiration.fr"
                disabled={isRunning || inspirationAnalyzing || cloneInspirationBusy}
                className={PREMIUM_INPUT}
              />
            </label>
            <label className="block shrink-0">
              <span className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-white/50">
                Secteur
              </span>
              <select
                value={inspirationSecteur}
                onChange={(e) => setInspirationSecteur(e.target.value)}
                disabled={isRunning || inspirationAnalyzing || cloneInspirationBusy}
                className={`${PREMIUM_INPUT} py-2.5`}
              >
                {INSPIRATION_SECTOR_OPTIONS.map((s) => (
                  <option key={s.nom} value={s.nom}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              disabled={
                isRunning ||
                inspirationAnalyzing ||
                cloneInspirationBusy ||
                !inspirationUrl.trim()
              }
              onClick={() => void handleAnalyzeInspiration()}
              className="shrink-0 whitespace-nowrap rounded-control border border-cf-gold/50 bg-cf-secondary px-4 py-2.5 text-sm font-medium text-cf-gold transition hover:border-cf-gold hover:bg-cf-active disabled:cursor-not-allowed disabled:opacity-60"
            >
              {inspirationAnalyzing ? "Analyse…" : "Analyser"}
            </button>
            <button
              type="button"
              disabled={
                isRunning ||
                inspirationAnalyzing ||
                cloneInspirationBusy ||
                !inspirationUrl.trim() ||
                !projectName.trim()
              }
              title={
                !projectName.trim()
                  ? "Renseignez le nom du client pour cloner"
                  : undefined
              }
              onClick={() => void handleCloneInspiration()}
              className="shrink-0 whitespace-nowrap rounded-control border border-cf-border-input bg-cf-secondary px-4 py-2.5 text-sm font-medium text-cf-text transition hover:border-cf-gold/40 hover:text-cf-gold disabled:cursor-not-allowed disabled:opacity-60"
            >
              {cloneInspirationBusy ? "Clone…" : "🔄 Cloner ce site"}
            </button>
          </div>

          {inspirationAnalyzing || cloneInspirationBusy ? (
            <div
              className="mt-4 flex items-center gap-3 rounded-control border border-cf-gold/25 bg-cf-active px-3 py-3"
              role="status"
            >
              <span
                className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-cf-gold border-t-transparent"
                aria-hidden
              />
              <p className="text-sm text-cf-muted">
                {cloneStatusMessage ??
                  "Scraping Firecrawl et extraction des couleurs…"}
              </p>
            </div>
          ) : null}

          {inspirationScrapeMeta ? (
            <div className="mt-3 rounded-control border border-cf-border-input bg-cf-main/50 px-3 py-2 text-sm text-cf-text">
              {inspirationScrapeMeta.title ? (
                <p>
                  <span className="font-medium text-cf-gold">Titre :</span>{" "}
                  {inspirationScrapeMeta.title}
                </p>
              ) : null}
              {inspirationScrapeMeta.description ? (
                <p className="mt-1 text-cf-muted">{inspirationScrapeMeta.description}</p>
              ) : null}
              {inspirationScrapeMeta.primary_color ? (
                <p className="mt-1 flex items-center gap-2">
                  <span className="font-medium text-cf-gold">Couleur :</span>
                  <span
                    className="inline-block h-4 w-4 rounded border border-cf-border-input"
                    style={{ backgroundColor: inspirationScrapeMeta.primary_color }}
                    aria-hidden
                  />
                  {inspirationScrapeMeta.primary_color}
                </p>
              ) : null}
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

        <div className="mt-5">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-white/50">
            Mode de déploiement
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {(
              [
                {
                  mode: "demo" as DeployMode,
                  icon: "🚀",
                  title: "Mode démo",
                  description:
                    "Démo Cloudflare instantanée — idéal pour présenter au client.",
                },
                {
                  mode: "real" as DeployMode,
                  icon: "🏭",
                  title: "Vraie app",
                  description: isPersonalFlow
                    ? "Projet Cloudflare Pages dédié (*.pages.dev)."
                    : "Déploiement production Railway / Vercel.",
                },
              ] as const
            ).map((option) => {
              const selected = deployMode === option.mode;
              return (
                <button
                  key={option.mode}
                  type="button"
                  disabled={isRunning}
                  onClick={() => selectDeployMode(option.mode)}
                  className={[
                    "relative flex min-h-[96px] flex-col items-start rounded-card p-4 text-left transition-all duration-200",
                    selected
                      ? "border-2 border-[#d4a843] bg-[#d4a843]/15 shadow-[0_0_24px_rgba(212,168,67,0.15)]"
                      : "border border-white/10 bg-white/5 opacity-70 hover:border-[#d4a843]/30 hover:opacity-90",
                    "disabled:cursor-not-allowed disabled:opacity-60",
                  ].join(" ")}
                >
                  {selected ? (
                    <span
                      className="absolute right-3 top-3 text-sm text-[#d4a843]"
                      aria-hidden
                    >
                      ✅
                    </span>
                  ) : null}
                  <span
                    className={[
                      "transition-all duration-200",
                      selected ? "text-3xl drop-shadow-[0_0_8px_rgba(212,168,67,0.45)]" : "text-xl",
                    ].join(" ")}
                    aria-hidden
                  >
                    {option.icon}
                  </span>
                  <span
                    className={[
                      "mt-2 block text-sm font-medium",
                      selected ? "text-[#d4a843]" : "text-cf-text",
                    ].join(" ")}
                  >
                    {option.title}
                  </span>
                  <span className="mt-1 block text-xs leading-snug text-cf-muted">
                    {option.description}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <form
          onSubmit={(e) => void handleGenerate(e)}
          noValidate
          className="mt-6 flex flex-col items-center"
        >
          <button
            type="submit"
            disabled={isRunning || !canGenerate}
            className="inline-flex min-w-[280px] items-center justify-center gap-2 rounded-control border border-[#d4a843] bg-[#d4a843] px-10 py-4 text-base font-semibold text-[#0a0a0a] transition-all duration-200 hover:scale-[1.02] hover:shadow-[0_0_32px_rgba(212,168,67,0.4)] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
          >
            {isRunning ? (
              <>
                <span
                  className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-[#0a0a0a] border-t-transparent"
                  aria-hidden
                />
                Génération en cours…
              </>
            ) : (
              "⚡ Générer mon projet"
            )}
          </button>
          {error && !showGenerationBlock ? (
            <p className="mt-4 w-full rounded-control border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
              {error}
            </p>
          ) : null}
          {!projectName.trim() ? (
            <p className="mt-3 text-xs text-cf-muted">
              Renseignez le nom du client pour activer la génération.
            </p>
          ) : null}
        </form>
      </section>
      ) : null}

      {/* Génération */}
      {showGenerationBlock ? (
      <section id="generator-step-4" className={`${GLASS_CARD} p-5`}>
        <StepHeading step={4} title="Génération" />

        {isRunning ? (
          <GeneratorPipelineProgress
            steps={pipelineSteps}
            startedAt={generationStartedAt}
            agentDurations={agentDurations}
            retries={pipelineRetries}
            serverDurationMs={serverDurationMs}
          />
        ) : null}

        {phase === "error" && error ? (
          <p className="rounded-control border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
            {error}
          </p>
        ) : null}

        {result && phase === "done" ? (
          <GeneratorResultCard
            projectName={projectName.trim() || projectTitleFromPrompt(prompt)}
            kindTitle={kindOption.title}
            sectorLabel={
              sectorPreset
                ? `${sectorPreset.emoji} ${sectorPreset.label}`
                : "—"
            }
            demoUrl={productionUrl ?? result.production_url ?? null}
            previewHtml={
              livePreviewHtml ??
              previewHtml ??
              result.preview_html ??
              result.generation.code ??
              null
            }
            costEur={
              result.metrics.estimated_cost_usd > 0
                ? result.metrics.estimated_cost_usd * 0.92
                : estimation.apiCostEur
            }
            durationMs={
              generationDurationMs > 0
                ? generationDurationMs
                : result.metrics.duration_ms
            }
            showProjectsLink={cloudSaved && Boolean(onOpenProjects)}
            isDesktop={selectedKind === "desktop"}
            desktopProjectId={savedSupabaseProjectId}
            onDownloadDesktop={
              savedSupabaseProjectId
                ? () => {
                    setDesktopDownloadError(null);
                    setDesktopDownloadBusy(true);
                    void downloadDesktopPackage(
                      savedSupabaseProjectId,
                      projectName.trim() || projectTitleFromPrompt(prompt),
                    )
                      .catch((err) => {
                        setDesktopDownloadError(
                          err instanceof Error
                            ? err.message
                            : "Téléchargement impossible.",
                        );
                      })
                      .finally(() => setDesktopDownloadBusy(false));
                  }
                : undefined
            }
            onOpenDemo={() => {
              const url = productionUrl ?? result.production_url;
              if (url) {
                window.open(url, "_blank", "noopener,noreferrer");
                return;
              }
              void handlePreview();
            }}
            onOpenProjects={onOpenProjects}
            onNewGeneration={resetForNewProject}
          />
        ) : null}
        {desktopDownloadError ? (
          <p className="mt-2 text-sm text-red-300">{desktopDownloadError}</p>
        ) : null}
        {desktopDownloadBusy ? (
          <p className="mt-2 text-sm text-cf-muted">Préparation du package Electron…</p>
        ) : null}
      </section>
      ) : null}

      {previewHtml ? (
        <GeneratorPreviewModal
          html={previewHtml}
          onClose={() => patch({ previewHtml: null })}
        />
      ) : null}

    </div>
  );
}

import { useState } from "react";
import type { CoreMindRunResponse, PipelineStepEvent } from "@shared/types";
import { GeneratorPipelineProgress } from "@/components/generator/GeneratorPipelineProgress";
import { GeneratorResultCard } from "@/components/generator/GeneratorResultCard";
import {
  applyPipelineStepEvent,
  initialPipelineSteps,
  type PipelineStepState,
} from "@/components/PipelineProgress";
import { pickPreviewHtml } from "@/lib/cyberforge-preview";
import { normalizeRunResponse } from "@/lib/normalize-run-response";
import {
  pipelineStreamErrorMessage,
  streamCoremindRun,
  type AgentRetryEvent,
} from "@/lib/pipeline-stream";
import {
  buildBrief,
  resolveProjectTypeFromKind,
  resolveStudioGenerationMode,
  slugifyProjectName,
} from "@/lib/studio-brief";
import {
  buildStudioVideoDraft,
  STUDIO_VIDEO_DRAFT_KEY,
} from "@/lib/studio-video-draft";
import type { AppPage } from "@/lib/navigation";
import type { DeployMode } from "@/lib/generator-kinds";
import type { StudioProjectKind, StudioSection } from "@/lib/studio-types";
import { getGeneratorKind } from "@/lib/generator-kinds";

interface GeneratorBridgeProps {
  projectType: StudioProjectKind | null;
  sector: string | null;
  sections: StudioSection[];
  projectName: string;
  deployMode: DeployMode;
  isPersonal: boolean;
  isGenerating: boolean;
  onGeneratingChange: (v: boolean) => void;
  generationResult: CoreMindRunResponse | null;
  onGenerationResult: (result: CoreMindRunResponse | null) => void;
  onError: (message: string | null) => void;
  onNavigate?: (page: AppPage) => void;
}

export function GeneratorBridge({
  projectType,
  sector,
  sections,
  projectName,
  deployMode,
  isPersonal,
  isGenerating,
  onGeneratingChange,
  generationResult,
  onGenerationResult,
  onError,
  onNavigate,
}: GeneratorBridgeProps) {
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStepState[]>(
    initialPipelineSteps(),
  );
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [agentDurations, setAgentDurations] = useState<
    Partial<Record<string, number>>
  >({});
  const [retries, setRetries] = useState<AgentRetryEvent[]>([]);
  const [serverDurationMs, setServerDurationMs] = useState<number | null>(null);
  const [durationMs, setDurationMs] = useState(0);

  const canGenerate =
    Boolean(projectType) &&
    sections.length > 0 &&
    projectName.trim().length > 0 &&
    !isGenerating;

  function applyStep(event: PipelineStepEvent) {
    setPipelineSteps((prev) => applyPipelineStepEvent(prev, event));
  }

  async function handleGenerate() {
    if (!canGenerate || !projectType) return;

    if (projectType === "video") {
      const draft = buildStudioVideoDraft(
        projectName.trim(),
        sector,
        sections,
      );
      sessionStorage.setItem(STUDIO_VIDEO_DRAFT_KEY, JSON.stringify(draft));
      onNavigate?.("video_builder");
      return;
    }

    const started = Date.now();
    setStartedAt(started);
    setDurationMs(0);
    setAgentDurations({});
    setRetries([]);
    setServerDurationMs(null);
    setPipelineSteps(initialPipelineSteps());
    onGeneratingChange(true);
    onError(null);
    onGenerationResult(null);

    const prompt = buildBrief(sections, projectType, sector, projectName.trim());
    const generationMode = resolveStudioGenerationMode(
      projectType,
      deployMode,
      isPersonal,
    );
    const project_type = resolveProjectTypeFromKind(projectType);

    try {
      const response = await streamCoremindRun(
        {
          prompt,
          project_type,
          generation_mode: generationMode,
          personal_project: isPersonal,
          pages_project_slug: isPersonal
            ? slugifyProjectName(projectName)
            : null,
          project_title: projectName.trim(),
          openhands_enabled: false,
          playwright_enabled: false,
          lighthouse_enabled: false,
          research_enabled: false,
        },
        {
          onStep: applyStep,
          onAgentRetry: (event) => {
            setRetries((prev) => [...prev, event]);
          },
          onAgentDuration: (agent, ms) => {
            setAgentDurations((prev) => ({ ...prev, [agent]: ms }));
          },
          onServerDuration: (ms) => {
            setServerDurationMs(ms);
            setDurationMs(ms);
          },
        },
      );

      if (!response.ok || !response.data) {
        setDurationMs(Date.now() - started);
        onError(
          pipelineStreamErrorMessage(
            response,
            "Génération impossible — vérifiez le backend.",
          ),
        );
        return;
      }

      const normalized = normalizeRunResponse(response.data);
      if (!normalized) {
        onError("Réponse invalide (génération vide).");
        return;
      }

      setDurationMs(Date.now() - started);
      onGenerationResult(normalized);
    } catch (err) {
      setDurationMs(Date.now() - started);
      onError(
        err instanceof Error ? err.message : "Erreur inattendue pendant la génération.",
      );
    } finally {
      onGeneratingChange(false);
    }
  }

  const kindTitle =
    projectType === "video"
      ? "Vidéo Kling"
      : getGeneratorKind(projectType).title;

  const previewHtml = generationResult
    ? pickPreviewHtml(
        generationResult.preview_html,
        generationResult.generation?.code,
      )
    : null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          disabled={!canGenerate}
          onClick={() => void handleGenerate()}
          className={[
            "rounded-control px-5 py-2.5 text-sm font-semibold transition",
            canGenerate
              ? "border border-cf-cyan/40 bg-cf-cyan/15 text-cf-cyan shadow-glow-cyan hover:bg-cf-cyan/25"
              : "border border-white/10 bg-white/5 text-cf-muted cursor-not-allowed",
          ].join(" ")}
        >
          {isGenerating
            ? "Génération en cours…"
            : projectType === "video"
              ? "🎬 Ouvrir le Video Builder"
              : "⚡ Générer le projet"}
        </button>
        {!projectName.trim() ? (
          <span className="text-xs text-cf-muted">Nom du projet requis</span>
        ) : sections.length === 0 ? (
          <span className="text-xs text-cf-muted">Ajoutez au moins une section</span>
        ) : null}
      </div>

      {isGenerating || generationResult ? (
        <GeneratorPipelineProgress
          steps={pipelineSteps}
          startedAt={startedAt}
          agentDurations={agentDurations}
          retries={retries}
          serverDurationMs={serverDurationMs}
        />
      ) : null}

      {generationResult ? (
        <GeneratorResultCard
          projectName={projectName}
          kindTitle={kindTitle}
          sectorLabel={sector ?? "—"}
          demoUrl={generationResult.production_url ?? null}
          previewHtml={previewHtml}
          costEur={
            generationResult.metrics?.estimated_cost_usd != null &&
            generationResult.metrics.estimated_cost_usd > 0
              ? generationResult.metrics.estimated_cost_usd * 0.92
              : null
          }
          durationMs={durationMs}
          showProjectsLink={false}
          isDesktop={projectType === "desktop"}
          onOpenDemo={() => {
            const url = generationResult.production_url;
            if (url) void window.cyberforge?.openExternal?.(url);
          }}
          onNewGeneration={() => {
            onGenerationResult(null);
            setPipelineSteps(initialPipelineSteps());
          }}
        />
      ) : null}
    </div>
  );
}

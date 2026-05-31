import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type {
  CoreMindRunResponse,
  GenerationMode,
  ProjectType,
  ValidationStatus,
  VisionPreviewSource,
  PlaywrightReportSummary,
  LighthouseReportSummary,
} from "@shared/types";
import type { PersonalUsage } from "@/lib/personal-projects-api";
import {
  applyPipelineStepEvent,
  initialPipelineSteps,
  type PipelineStepState,
} from "@/components/PipelineProgress";
import type { PipelineStepEvent } from "@shared/types";
import type { DemoCustomization } from "@/lib/demo-customization";

export type GeneratorFlowPhase = "idle" | "running" | "done" | "error";

export interface GeneratorSessionState {
  prompt: string;
  projectName: string;
  projectType: ProjectType;
  generationMode: GenerationMode;
  phase: GeneratorFlowPhase;
  error: string | null;
  actionError: string | null;
  result: CoreMindRunResponse | null;
  activeFile: number;
  previewHtml: string | null;
  livePreviewHtml: string | null;
  customizeOpen: boolean;
  customization: DemoCustomization | null;
  baselineCustomization: DemoCustomization | null;
  lastSavedId: string | null;
  cloudSaved: boolean;
  pipelineSteps: PipelineStepState[];
  visionScreenshotUrl: string | null;
  visionPreviewSource: VisionPreviewSource | null;
  visionMessage: string | null;
  validationStatus: ValidationStatus | null;
  validationSummary: string | null;
  testpilotPassed: boolean | null;
  playwrightReport: PlaywrightReportSummary | null;
  lighthouseReport: LighthouseReportSummary | null;
  productionUrl: string | null;
  exportProvider: string | null;
  unlockUrl: string | null;
  demoPassword: string | null;
  githubExportUrl: string | null;
  personalMode: boolean;
  personalUsage: PersonalUsage;
  personalPriceEur: number | null;
  personalCommercialDescription: string;
  personalDraftTitle: string;
}

const initialSession = (): GeneratorSessionState => ({
  prompt: "",
  projectName: "",
  projectType: "site_web",
  generationMode: "client_demo",
  phase: "idle",
  error: null,
  actionError: null,
  result: null,
  activeFile: 0,
  previewHtml: null,
  livePreviewHtml: null,
  customizeOpen: false,
  customization: null,
  baselineCustomization: null,
  lastSavedId: null,
  cloudSaved: false,
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
  unlockUrl: null,
  demoPassword: null,
  githubExportUrl: null,
  personalMode: false,
  personalUsage: "personal",
  personalPriceEur: null,
  personalCommercialDescription: "",
  personalDraftTitle: "",
});

interface GeneratorSessionContextValue extends GeneratorSessionState {
  patch: (partial: Partial<GeneratorSessionState>) => void;
  applyPipelineStep: (event: PipelineStepEvent) => void;
  resetSession: () => void;
}

const GeneratorSessionContext =
  createContext<GeneratorSessionContextValue | null>(null);

export function GeneratorSessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<GeneratorSessionState>(initialSession);

  const patch = useCallback((partial: Partial<GeneratorSessionState>) => {
    setSession((prev) => ({ ...prev, ...partial }));
  }, []);

  const resetSession = useCallback(() => {
    setSession(initialSession());
  }, []);

  const applyPipelineStep = useCallback((event: PipelineStepEvent) => {
    setSession((prev) => ({
      ...prev,
      pipelineSteps: applyPipelineStepEvent(prev.pipelineSteps, event),
    }));
  }, []);

  const value = useMemo(
    () => ({
      ...session,
      patch,
      applyPipelineStep,
      resetSession,
    }),
    [session, patch, applyPipelineStep, resetSession],
  );

  return (
    <GeneratorSessionContext.Provider value={value}>
      {children}
    </GeneratorSessionContext.Provider>
  );
}

export function useGeneratorSession(): GeneratorSessionContextValue {
  const ctx = useContext(GeneratorSessionContext);
  if (!ctx) {
    throw new Error(
      "useGeneratorSession doit être utilisé dans GeneratorSessionProvider",
    );
  }
  return ctx;
}

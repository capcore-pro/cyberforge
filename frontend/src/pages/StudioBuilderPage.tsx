import { useMemo, useState } from "react";
import type { CoreMindRunResponse } from "@shared/types";
import { ProjectTypeSelector } from "@/components/studio/ProjectTypeSelector";
import { SectorSelector } from "@/components/studio/SectorSelector";
import { SectionLibrary } from "@/components/studio/SectionLibrary";
import { SectionBuilder } from "@/components/studio/SectionBuilder";
import { AnimationPicker } from "@/components/studio/AnimationPicker";
import { GeneratorBridge } from "@/components/studio/GeneratorBridge";
import type { DeployMode } from "@/lib/generator-kinds";
import type { AppPage } from "@/lib/navigation";
import {
  createStudioSection,
  type StudioProjectKind,
  type StudioSection,
  type StudioSectionType,
  type StudioStep,
} from "@/lib/studio-types";

interface StudioBuilderPageProps {
  onNavigate?: (page: AppPage) => void;
}

export function StudioBuilderPage({ onNavigate }: StudioBuilderPageProps) {
  const [step, setStep] = useState<StudioStep>("type");
  const [projectType, setProjectType] = useState<StudioProjectKind | null>(null);
  const [sector, setSector] = useState<string | null>(null);
  const [sections, setSections] = useState<StudioSection[]>([]);
  const [activeSectionId, setActiveSectionId] = useState<string | null>(null);
  const [projectName, setProjectName] = useState("");
  const [deployMode, setDeployMode] = useState<DeployMode>("demo");
  const [isPersonal, setIsPersonal] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationResult, setGenerationResult] =
    useState<CoreMindRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const activeSection = useMemo(
    () => sections.find((s) => s.id === activeSectionId) ?? null,
    [sections, activeSectionId],
  );

  const assistContext = useMemo(() => {
    const parts = [
      projectName && `Projet : ${projectName}`,
      projectType && `Type : ${projectType}`,
      sector && `Secteur : ${sector}`,
    ].filter(Boolean);
    return parts.join(" · ");
  }, [projectName, projectType, sector]);

  function handleSelectType(kind: StudioProjectKind) {
    setProjectType(kind);
    setSector(null);
    setSections([]);
    setActiveSectionId(null);
    setGenerationResult(null);
    setStep("sector");
  }

  function handleSelectSector(sectorId: string) {
    setSector(sectorId);
    setStep("build");
  }

  function handleAddSection(type: StudioSectionType) {
    if (sections.some((s) => s.type === type)) return;
    const next = createStudioSection(type, sections.length);
    setSections((prev) => [...prev, next]);
    setActiveSectionId(next.id);
  }

  function updateSectionField(
    sectionId: string,
    fieldKey: string,
    value: string,
    fromAI?: boolean,
  ) {
    setSections((prev) =>
      prev.map((s) =>
        s.id === sectionId
          ? {
              ...s,
              fields: { ...s.fields, [fieldKey]: value },
              ...(fromAI ? { aiGenerated: true } : {}),
            }
          : s,
      ),
    );
  }

  function handleSectionFieldsChange(
    sectionId: string,
    fields: Record<string, string>,
    options?: { imageUrl?: string; fromAI?: boolean },
  ) {
    setSections((prev) =>
      prev.map((s) =>
        s.id === sectionId
          ? {
              ...s,
              fields,
              ...(options?.imageUrl !== undefined
                ? { imageUrl: options.imageUrl }
                : {}),
              ...(options?.fromAI ? { aiGenerated: true } : {}),
            }
          : s,
      ),
    );
  }

  function handleAnimationChange(animationClass: string) {
    if (!activeSectionId) return;
    setSections((prev) =>
      prev.map((s) =>
        s.id === activeSectionId ? { ...s, animationClass } : s,
      ),
    );
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] min-h-[640px] flex-col font-sans">
      <style>{`
        @keyframes studio-fade-in { from { opacity: 0; } to { opacity: 1; } }
        @keyframes studio-slide-up { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes studio-zoom-in { from { opacity: 0; transform: scale(0.92); } to { opacity: 1; transform: scale(1); } }
        .animate-fade-in { animation: studio-fade-in 0.6s ease both; }
        .animate-slide-up { animation: studio-slide-up 0.5s ease both; }
        .animate-zoom-in { animation: studio-zoom-in 0.45s ease both; }
        .animate-parallax { background: linear-gradient(135deg, rgba(0,212,255,0.08), transparent); }
        .animate-count-up { letter-spacing: 0.05em; }
        .animate-glitch { text-shadow: 1px 0 #00d4ff, -1px 0 #7c3aed; }
      `}</style>

      <header className="shrink-0 border-b border-[rgba(0,212,255,0.1)] px-1 pb-4">
        <p className="font-mono text-xs text-cf-cyan">// studio builder</p>
        <h1 className="mt-1 text-2xl font-semibold text-cf-text">✦ Créer un projet</h1>
        <p className="mt-1 text-sm text-cf-muted">
          Composez votre site section par section, assisté par l&apos;IA.
        </p>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto py-4">
        {step === "type" ? (
          <ProjectTypeSelector
            value={projectType}
            onSelect={handleSelectType}
            disabled={isGenerating}
          />
        ) : null}

        {step === "sector" && projectType ? (
          <div className="space-y-4">
            <button
              type="button"
              className="text-sm text-cf-cyan hover:text-white"
              onClick={() => setStep("type")}
            >
              ← Retour au type
            </button>
            <SectorSelector
              kind={projectType}
              value={sector}
              onSelect={handleSelectSector}
              disabled={isGenerating}
            />
          </div>
        ) : null}

        {step === "build" ? (
          <div className="flex h-full min-h-[480px] flex-col gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="text-sm text-cf-cyan hover:text-white"
                onClick={() => setStep("sector")}
                disabled={isGenerating}
              >
                ← Retour au secteur
              </button>
              <label className="ml-auto flex min-w-[200px] flex-1 items-center gap-2 sm:max-w-xs">
                <span className="shrink-0 text-xs text-cf-muted">Nom</span>
                <input
                  type="text"
                  value={projectName}
                  disabled={isGenerating}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="Nom du client / projet"
                  className="w-full rounded-control border border-[rgba(0,212,255,0.15)] bg-[#0a0a12] px-3 py-2 text-sm text-cf-text"
                />
              </label>
            </div>

            <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[240px_minmax(0,1fr)_280px]">
              <div className="flex flex-col gap-4">
                <div className="mb-4 rounded-lg border border-cf-cyan-border bg-[#0a0a12] p-3">
                  <div className="mb-1 font-mono text-xs text-cf-cyan">
                    // projet en cours
                  </div>
                  <div className="text-sm font-medium text-white">
                    {projectName || "Sans titre"}
                  </div>
                  <div className="mt-1 text-xs text-cf-muted">
                    {projectType} · {sector ?? "—"}
                  </div>
                  <button
                    type="button"
                    onClick={() => setStep("type")}
                    disabled={isGenerating}
                    className="mt-2 block text-xs text-cf-cyan hover:underline"
                  >
                    ← Modifier
                  </button>
                </div>
                <SectionLibrary
                  projectType={projectType}
                  sections={sections}
                  onAdd={handleAddSection}
                  activeSectionId={activeSectionId}
                  onSelectSection={setActiveSectionId}
                  disabled={isGenerating}
                />
              </div>

              <SectionBuilder
                section={activeSection}
                context={assistContext}
                onChange={handleSectionFieldsChange}
                disabled={isGenerating}
              />

              <aside className="flex flex-col gap-4 rounded-[10px] border border-[rgba(0,212,255,0.1)] bg-[#0a0a12] p-4">
                <p className="font-mono text-xs text-cf-cyan">// assistance IA</p>
                <p className="text-xs text-cf-muted">
                  Utilisez ✦ IA sur chaque champ ou ✦ FLUX pour les visuels.
                </p>
                <AnimationPicker
                  value={activeSection?.animationClass ?? ""}
                  onChange={handleAnimationChange}
                  disabled={isGenerating || !activeSection}
                />
              </aside>
            </div>
          </div>
        ) : null}

        {error ? (
          <p className="mt-4 rounded-control border border-cf-red/30 bg-cf-red/10 px-3 py-2 text-sm text-cf-red">
            {error}
          </p>
        ) : null}
      </div>

      {step === "build" ? (
        <footer className="shrink-0 border-t border-[rgba(0,212,255,0.1)] bg-[#0a0a12] px-4 py-3">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex rounded-control border border-[rgba(0,212,255,0.15)] p-0.5">
              {(["client", "perso"] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  disabled={isGenerating}
                  onClick={() => setIsPersonal(mode === "perso")}
                  className={[
                    "rounded-control px-3 py-1.5 text-xs font-semibold capitalize",
                    (mode === "perso") === isPersonal
                      ? "bg-cf-cyan/15 text-cf-cyan"
                      : "text-cf-muted",
                  ].join(" ")}
                >
                  {mode === "client" ? "Client" : "Perso"}
                </button>
              ))}
            </div>

            <div className="flex rounded-control border border-[rgba(0,212,255,0.15)] p-0.5">
              {(["demo", "real"] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  disabled={isGenerating}
                  onClick={() => setDeployMode(mode)}
                  className={[
                    "rounded-control px-3 py-1.5 text-xs font-semibold",
                    deployMode === mode
                      ? "bg-cf-cyan/15 text-cf-cyan"
                      : "text-cf-muted",
                  ].join(" ")}
                >
                  {mode === "demo" ? "Démo" : "Vraie app"}
                </button>
              ))}
            </div>

            <div className="min-w-0 flex-1">
              <GeneratorBridge
                projectType={projectType}
                sector={sector}
                sections={sections}
                projectName={projectName}
                deployMode={deployMode}
                isPersonal={isPersonal}
                isGenerating={isGenerating}
                onGeneratingChange={setIsGenerating}
                generationResult={generationResult}
                onGenerationResult={setGenerationResult}
                onError={setError}
                onNavigate={onNavigate}
              />
            </div>
          </div>
        </footer>
      ) : null}
    </div>
  );
}

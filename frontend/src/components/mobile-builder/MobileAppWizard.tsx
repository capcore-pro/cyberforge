import { useMemo, useState } from "react";
import type { MobileAppUpsert } from "@/lib/mobile-builder-api";
import { Button } from "@/components/ui";
import { Step1AppInfo } from "./Step1AppInfo";
import { Step2Design } from "./Step2Design";
import { Step3Features } from "./Step3Features";
import { Step4Generate, type GenerateLogEntry } from "./Step4Generate";

type WizardStep = 1 | 2 | 3 | 4;

function stepLabel(step: WizardStep): string {
  if (step === 1) return "Informations";
  if (step === 2) return "Design";
  if (step === 3) return "Features";
  return "Génération";
}

function validateStep(step: WizardStep, value: MobileAppUpsert): string | null {
  if (step === 1) {
    if (value.name.trim().length < 2) return "Nom requis (min 2 caractères).";
    if (!/^[a-z0-9-]+$/.test(value.app_slug)) {
      return "Slug invalide (a-z, 0-9, tirets uniquement).";
    }
    if (!value.bundle_id.trim()) return "Bundle ID requis.";
    return null;
  }
  if (step === 2) {
    if (!/^#[0-9A-Fa-f]{6}$/.test(value.primary_color)) {
      return "Couleur primaire invalide.";
    }
    return null;
  }
  return null;
}

export function MobileAppWizard({
  appId,
  value,
  disabled,
  generating,
  generated,
  generateLogs,
  generatedFiles,
  buildLoading,
  onChange,
  onSave,
  onGenerate,
  onBuild,
}: {
  appId: string | null;
  value: MobileAppUpsert;
  disabled?: boolean;
  generating: boolean;
  generated: boolean;
  generateLogs: GenerateLogEntry[];
  generatedFiles: string[];
  buildLoading: boolean;
  onChange: (next: MobileAppUpsert) => void;
  onSave: (payload: MobileAppUpsert) => Promise<string | null>;
  onGenerate: () => void;
  onBuild: () => void;
}) {
  const [step, setStep] = useState<WizardStep>(1);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const canGoNext = useMemo(() => !validateStep(step, value), [step, value]);

  async function handleSaveAndNext() {
    setSaving(true);
    setError(null);
    try {
      const err = validateStep(1, value);
      if (err) {
        setStep(1);
        setError(err);
        return;
      }
      await onSave(value);
      goNext();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sauvegarde impossible.");
    } finally {
      setSaving(false);
    }
  }

  function goNext() {
    const err = validateStep(step, value);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    setStep((s) => (s === 4 ? 4 : ((s + 1) as WizardStep)));
  }

  function goPrev() {
    setError(null);
    setStep((s) => (s === 1 ? 1 : ((s - 1) as WizardStep)));
  }

  return (
    <div>
      <div className="mb-6 flex items-center gap-2">
        {([1, 2, 3, 4] as WizardStep[]).map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={[
                "flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold",
                step === s
                  ? "bg-cyan-500/20 text-cyan-200 ring-2 ring-cyan-500/50"
                  : step > s
                    ? "bg-emerald-500/20 text-emerald-200"
                    : "bg-white/5 text-cf-muted",
              ].join(" ")}
            >
              {s}
            </div>
            <span className="hidden text-xs text-cf-muted sm:inline">
              {stepLabel(s)}
            </span>
            {s < 4 ? <span className="text-cf-muted">→</span> : null}
          </div>
        ))}
      </div>

      {error ? (
        <p className="mb-4 rounded-card border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {step === 1 ? (
        <Step1AppInfo value={value} onChange={onChange} disabled={disabled || saving} />
      ) : null}
      {step === 2 ? (
        <Step2Design value={value} onChange={onChange} disabled={disabled || saving} />
      ) : null}
      {step === 3 ? (
        <Step3Features value={value} onChange={onChange} disabled={disabled || saving} />
      ) : null}
      {step === 4 ? (
        <Step4Generate
          appId={appId}
          generated={generated}
          generating={generating}
          logs={generateLogs}
          files={generatedFiles}
          onGenerate={onGenerate}
          onBuild={onBuild}
          buildLoading={buildLoading}
          disabled={disabled || saving}
        />
      ) : null}

      <div className="mt-6 flex justify-between gap-3">
        <Button
          variant="ghost"
          disabled={step === 1 || saving}
          onClick={goPrev}
        >
          Précédent
        </Button>
        {step < 4 ? (
          <Button
            variant="primary"
            loading={saving}
            disabled={!canGoNext || saving}
            onClick={() => void handleSaveAndNext()}
          >
            Suivant
          </Button>
        ) : (
          <Button
            variant="ghost"
            loading={saving}
            disabled={saving}
            onClick={() => void onSave(value)}
          >
            Sauvegarder
          </Button>
        )}
      </div>
    </div>
  );
}

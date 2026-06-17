import { useState } from "react";
import type { ErpProjectUpsert, ErpRecommendation, ErpType } from "@/lib/erp-builder-api";
import { Button } from "@/components/ui";
import { Step1Profile } from "./Step1Profile";
import { Step2Recommendation } from "./Step2Recommendation";
import { Step3Configure } from "./Step3Configure";
import { Step4Install, type InstallStep } from "./Step4Install";

type WizardStep = 1 | 2 | 3 | 4;

function stepTitle(step: WizardStep): string {
  if (step === 1) return "Votre profil";
  if (step === 2) return "Notre recommandation";
  if (step === 3) return "Configuration";
  return "Installation";
}

export function ErpWizard({
  projectId,
  value,
  disabled,
  recommendation,
  recommendLoading,
  showAlternatives,
  onToggleAlternatives,
  onChange,
  onSave,
  onRecommend,
  onChooseErp,
  installing,
  installSteps,
  installResult,
  onInstall,
  onOpenUrl,
}: {
  projectId: string | null;
  value: ErpProjectUpsert;
  disabled?: boolean;
  recommendation: ErpRecommendation | null;
  recommendLoading: boolean;
  showAlternatives: boolean;
  onToggleAlternatives: () => void;
  onChange: (next: ErpProjectUpsert) => void;
  onSave: (payload: ErpProjectUpsert) => Promise<string | null>;
  onRecommend: () => void;
  onChooseErp: (type: ErpType) => void;
  installing: boolean;
  installSteps: InstallStep[];
  installResult: { url: string; admin_email: string; admin_password: string } | null;
  onInstall: () => void;
  onOpenUrl: (url: string) => void;
}) {
  const [step, setStep] = useState<WizardStep>(1);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function goNext() {
    setSaving(true);
    setError(null);
    try {
      if (step === 1) {
        if (value.modules.length === 0) {
          setError("Sélectionnez au moins un besoin.");
          return;
        }
        const id = projectId ?? (await onSave(value));
        if (!id) return;
        setStep(2);
        onRecommend();
        return;
      }
      if (step === 2) {
        if (!value.erp_type && !recommendation) {
          setError("Choisissez un ERP avant de continuer.");
          return;
        }
        setStep(3);
        return;
      }
      if (step === 3) {
        if (!value.name.trim() || !value.admin_email.trim()) {
          setError("Nom et email admin requis.");
          return;
        }
        await onSave(value);
        setStep(4);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setSaving(false);
    }
  }

  function goPrev() {
    setError(null);
    setStep((s) => (s === 1 ? 1 : ((s - 1) as WizardStep)));
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-2">
        {([1, 2, 3, 4] as WizardStep[]).map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={[
                "flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold",
                step === s
                  ? "bg-cyan-500/20 text-cyan-200 ring-2 ring-cyan-500/40"
                  : step > s
                    ? "bg-emerald-500/20 text-emerald-200"
                    : "bg-white/5 text-cf-muted",
              ].join(" ")}
            >
              {s}
            </div>
            <span className="hidden text-xs text-cf-muted sm:inline">{stepTitle(s)}</span>
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
        <Step1Profile value={value} onChange={onChange} disabled={disabled || saving} />
      ) : null}
      {step === 2 ? (
        <Step2Recommendation
          recommendation={recommendation}
          loading={recommendLoading}
          showAlternatives={showAlternatives}
          onToggleAlternatives={onToggleAlternatives}
          onChoose={() => recommendation && onChooseErp(recommendation.erp_type)}
          onChooseAlt={onChooseErp}
        />
      ) : null}
      {step === 3 ? (
        <Step3Configure value={value} onChange={onChange} disabled={disabled || saving} />
      ) : null}
      {step === 4 ? (
        <Step4Install
          installing={installing}
          steps={installSteps}
          installResult={installResult}
          onInstall={onInstall}
          onOpen={onOpenUrl}
        />
      ) : null}

      <div className="mt-6 flex justify-between">
        <Button variant="ghost" disabled={step === 1 || saving} onClick={goPrev}>
          Précédent
        </Button>
        {step < 4 ? (
          <Button variant="primary" loading={saving} onClick={() => void goNext()}>
            Suivant
          </Button>
        ) : null}
      </div>
    </div>
  );
}

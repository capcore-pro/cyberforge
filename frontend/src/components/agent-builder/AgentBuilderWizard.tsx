import { useMemo, useState } from "react";
import type { CustomAgentUpsert } from "@/lib/custom-agents-api";
import { Button } from "@/components/ui";
import { Step1Configure } from "@/components/agent-builder/Step1Configure";
import { Step2Tools } from "@/components/agent-builder/Step2Tools";
import { Step3Test } from "@/components/agent-builder/Step3Test";

type WizardStep = 1 | 2 | 3;

function stepLabel(step: WizardStep): string {
  if (step === 1) return "Configurer";
  if (step === 2) return "Outils";
  return "Tester";
}

function validateStep(step: WizardStep, value: CustomAgentUpsert): string | null {
  if (step === 1) {
    if (value.name.trim().length < 2) return "Nom requis (min 2 caractères).";
    if (value.system_prompt.trim().length < 10) return "System prompt trop court.";
    if (!value.model.trim()) return "Modèle requis.";
    return null;
  }
  if (step === 2) {
    // outils optionnels
    return null;
  }
  return null;
}

export function AgentBuilderWizard({
  agentId,
  value,
  disabled,
  onChange,
  onSave,
}: {
  agentId: string | null;
  value: CustomAgentUpsert;
  disabled: boolean;
  onChange: (next: CustomAgentUpsert) => void;
  onSave: (payload: CustomAgentUpsert) => Promise<void>;
}) {
  const [step, setStep] = useState<WizardStep>(1);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const canGoNext = useMemo(() => !validateStep(step, value), [step, value]);

  async function handleSave() {
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
    setStep((s) => (s === 3 ? 3 : ((s + 1) as WizardStep)));
  }

  function goPrev() {
    setError(null);
    setStep((s) => (s === 1 ? 1 : ((s - 1) as WizardStep)));
  }

  return (
    <div>
      <div className="mb-4 rounded-card border border-white/10 bg-white/5 p-4">
        <div className="flex items-center gap-2">
          {[1, 2, 3].map((s) => {
            const st = s as WizardStep;
            const active = st === step;
            const done = st < step;
            return (
              <div key={st} className="flex items-center gap-2">
                <span
                  className={[
                    "inline-flex h-7 w-7 items-center justify-center rounded-full border text-xs font-semibold",
                    active
                      ? "border-cf-gold/40 bg-cf-gold/15 text-cf-gold"
                      : done
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                        : "border-white/10 bg-white/5 text-cf-muted",
                  ].join(" ")}
                >
                  {done ? "✓" : st}
                </span>
                <span
                  className={[
                    "text-xs font-semibold",
                    active ? "text-cf-text" : "text-cf-muted",
                  ].join(" ")}
                >
                  {stepLabel(st)}
                </span>
                {st < 3 ? (
                  <span className="mx-1 h-px w-10 bg-white/10" aria-hidden />
                ) : null}
              </div>
            );
          })}
        </div>
      </div>

      {error ? (
        <p className="mb-4 rounded-card border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {step === 1 ? (
        <Step1Configure value={value} disabled={disabled || saving} onChange={onChange} />
      ) : null}
      {step === 2 ? (
        <Step2Tools value={value} disabled={disabled || saving} onChange={onChange} />
      ) : null}
      {step === 3 ? (
        <Step3Test agentId={agentId} value={value} disabled={disabled || saving} />
      ) : null}

      <div className="mt-6 flex flex-wrap justify-between gap-2">
        <Button variant="ghost" disabled={disabled || saving || step === 1} onClick={goPrev}>
          Précédent
        </Button>
        <div className="flex flex-wrap gap-2">
          {step < 3 ? (
            <Button
              variant="primary"
              disabled={disabled || saving || !canGoNext}
              onClick={goNext}
              icon="ti ti-arrow-right"
            >
              Suivant
            </Button>
          ) : null}
          <Button
            variant="primary"
            loading={saving}
            disabled={disabled || saving}
            onClick={() => void handleSave()}
            icon="ti ti-device-floppy"
          >
            Sauvegarder
          </Button>
        </div>
      </div>
    </div>
  );
}


import type { CustomAgentUpsert } from "@/lib/custom-agents-api";

const FIELD_LABEL =
  "text-[10px] font-medium uppercase tracking-wider text-cf-label";
const INPUT =
  "mt-1 w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none disabled:opacity-60";

const MODELS: Array<{ id: string; label: string }> = [
  { id: "claude-sonnet-4-6", label: "claude-sonnet-4-6 (Sonnet)" },
  { id: "claude-haiku-4-5-20251001", label: "claude-haiku-4-5-20251001 (Haiku)" },
  { id: "mistral-small-latest", label: "mistral-small-latest (Mistral Small)" },
  { id: "mistral-large-latest", label: "mistral-large-latest (Mistral Large)" },
  { id: "qwen3", label: "qwen3 via Ollama (local)" },
  { id: "deepseek-r1", label: "deepseek-r1 via Ollama (local)" },
];

export function Step1Configure({
  value,
  disabled,
  onChange,
}: {
  value: CustomAgentUpsert;
  disabled: boolean;
  onChange: (next: CustomAgentUpsert) => void;
}) {
  return (
    <section className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <p className={FIELD_LABEL}>Nom de l&apos;agent</p>
          <input
            value={value.name}
            disabled={disabled}
            onChange={(e) => onChange({ ...value, name: e.target.value })}
            className={INPUT}
            placeholder="ex: Agent Devis Artisan"
          />
        </div>
        <div>
          <p className={FIELD_LABEL}>Description</p>
          <input
            value={value.description}
            disabled={disabled}
            onChange={(e) => onChange({ ...value, description: e.target.value })}
            className={INPUT}
            placeholder="ex: Génère des devis, facture, relances."
          />
        </div>
      </div>

      <div>
        <p className={FIELD_LABEL}>System Prompt</p>
        <textarea
          value={value.system_prompt}
          disabled={disabled}
          onChange={(e) => onChange({ ...value, system_prompt: e.target.value })}
          className={`${INPUT} min-h-[220px] resize-y`}
          placeholder={
            "Tu es un agent expert.\n" +
            "Objectif: ...\n" +
            "Contraintes: réponses courtes, en français, avec checklist."
          }
        />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="md:col-span-1">
          <p className={FIELD_LABEL}>Modèle LLM</p>
          <select
            value={value.model}
            disabled={disabled}
            onChange={(e) => onChange({ ...value, model: e.target.value })}
            className={INPUT}
          >
            {MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <p className={FIELD_LABEL}>Température ({value.temperature.toFixed(1)})</p>
          <input
            type="range"
            min={0}
            max={1}
            step={0.1}
            value={value.temperature}
            disabled={disabled}
            onChange={(e) =>
              onChange({ ...value, temperature: Number(e.target.value) })
            }
            className="mt-2 w-full"
          />
        </div>

        <div>
          <p className={FIELD_LABEL}>Max tokens ({value.max_tokens})</p>
          <input
            type="range"
            min={500}
            max={4000}
            step={100}
            value={value.max_tokens}
            disabled={disabled}
            onChange={(e) =>
              onChange({ ...value, max_tokens: Number(e.target.value) })
            }
            className="mt-2 w-full"
          />
        </div>
      </div>
    </section>
  );
}

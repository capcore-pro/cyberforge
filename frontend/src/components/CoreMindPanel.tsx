import { useState } from "react";
import { API_PREFIX } from "@shared/constants";
import type { CoreMindResponse } from "@shared/types";
import { apiRequest } from "@/lib/api-client";

const COMPLEXITY_STYLES = {
  faible: "text-green-400 border-green-400/40 bg-green-400/10",
  moyenne: "text-amber-400 border-amber-400/40 bg-amber-400/10",
  elevee: "text-red-400 border-red-400/40 bg-red-400/10",
} as const;

const TOOL_STYLES = {
  "bolt.new": "from-cyan-500/20 to-violet-500/20 text-cyber-neon",
  lovable: "from-violet-500/20 to-pink-500/20 text-cyber-violet",
  v0: "from-cyan-500/20 to-blue-500/20 text-cyber-accent",
} as const;

/**
 * Interface CoreMindAI — saisie de prompt et affichage de l'analyse structurée.
 */
export function CoreMindPanel() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CoreMindResponse | null>(null);

  async function handleAnalyze(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = prompt.trim();
    if (trimmed.length < 3) {
      setError("Décrivez votre projet en au moins 3 caractères.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const response = await apiRequest<CoreMindResponse>({
      method: "POST",
      path: `${API_PREFIX}/agents/coremind`,
      body: { prompt: trimmed },
    });

    setLoading(false);

    if (!response.ok) {
      setError(
        response.status === 0
          ? "Backend injoignable. Démarrez FastAPI puis réessayez."
          : response.data &&
              typeof response.data === "object" &&
              "detail" in response.data
            ? String((response.data as { detail: unknown }).detail)
            : `Erreur ${response.status} : ${response.statusText}`,
      );
      return;
    }

    setResult(response.data);
  }

  return (
    <section
      className="cyber-panel mb-8 overflow-hidden border-cyber-borderGlow p-0"
      aria-labelledby="coremind-heading"
    >
      <div className="border-b border-cyber-border bg-gradient-to-r from-cyber-violet/10 via-cyber-surfaceAlt to-cyber-accent/10 px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-cyber-violet">
              Agent actif
            </p>
            <h2
              id="coremind-heading"
              className="text-lg font-bold text-cyber-neon"
            >
              CoreMindAI
            </h2>
            <p className="mt-0.5 text-xs text-cyber-muted">
              Cerveau central — classification, outil et plan d&apos;action
            </p>
          </div>
          <span className="rounded border border-cyber-violet/50 bg-cyber-violet/10 px-2 py-1 font-mono text-[10px] text-cyber-violet">
            POST {API_PREFIX}/agents/coremind
          </span>
        </div>
      </div>

      <form onSubmit={(e) => void handleAnalyze(e)} className="space-y-4 p-5">
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-cyber-muted">
            Votre prompt
          </span>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            placeholder="Ex. : Je veux une application SaaS de monitoring cybersécurité avec dashboard admin, auth et API REST…"
            className="w-full resize-y rounded-md border border-cyber-border bg-cyber-bg px-3 py-2.5 text-sm text-cyber-text placeholder:text-cyber-muted/60 focus:border-cyber-accent focus:outline-none focus:ring-1 focus:ring-cyber-accent/50"
            disabled={loading}
          />
        </label>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={loading || prompt.trim().length < 3}
            className="cyber-btn disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Analyse en cours…" : "Analyser avec CoreMindAI"}
          </button>
          {result ? (
            <button
              type="button"
              className="rounded-md border border-cyber-border px-3 py-2 text-xs text-cyber-muted transition hover:border-cyber-accent hover:text-cyber-text"
              onClick={() => {
                setResult(null);
                setError(null);
              }}
            >
              Effacer
            </button>
          ) : null}
        </div>

        {error ? (
          <p className="rounded border border-red-400/40 bg-red-400/10 px-3 py-2 text-xs text-red-400">
            {error}
          </p>
        ) : null}
      </form>

      {result ? (
        <div className="space-y-4 border-t border-cyber-border bg-cyber-bg/40 p-5">
          <p className="text-sm leading-relaxed text-cyber-text">{result.summary}</p>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <ResultCard label="Type de projet" value={result.project_type_label} />
            <ResultCard
              label="Outil recommandé"
              value={result.recommended_tool}
              highlight={TOOL_STYLES[result.recommended_tool]}
            />
            <ResultCard
              label="Complexité"
              value={`${result.complexity} (${result.complexity_score}/10)`}
              highlight={COMPLEXITY_STYLES[result.complexity]}
            />
            <ResultCard label="Agent" value={result.agent_name} />
          </div>

          <div className="rounded-md border border-cyber-border bg-cyber-surface/80 p-3">
            <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Pourquoi cet outil ?
            </p>
            <p className="mt-1 text-xs leading-relaxed text-cyber-text">
              {result.tool_rationale}
            </p>
          </div>

          <div>
            <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-cyber-violet">
              Prochaines étapes
            </p>
            <ol className="space-y-2">
              {result.next_steps.map((step, index) => (
                <li
                  key={step}
                  className="flex gap-2 text-xs leading-relaxed text-cyber-muted"
                >
                  <span className="shrink-0 font-mono text-cyber-neon">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function ResultCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: string;
}) {
  return (
    <div
      className={`rounded-md border border-cyber-border px-3 py-2.5 ${
        highlight ?? "bg-cyber-bg/60"
      }`}
    >
      <p className="text-[10px] uppercase tracking-wider text-cyber-muted">{label}</p>
      <p className="mt-0.5 font-mono text-sm font-bold">{value}</p>
    </div>
  );
}

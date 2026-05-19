import { useState } from "react";
import { API_PREFIX } from "@shared/constants";
import type { CoreMindGenerateResponse, CoreMindResponse } from "@shared/types";
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

function apiErrorMessage(
  response: { status: number; statusText: string; data: unknown },
  offline: string,
): string {
  if (response.status === 0) return offline;
  if (
    response.data &&
    typeof response.data === "object" &&
    "detail" in response.data
  ) {
    return String((response.data as { detail: unknown }).detail);
  }
  return `Erreur ${response.status} : ${response.statusText}`;
}

/**
 * Interface CoreMindAI — analyse, génération de code via Claude.
 */
export function CoreMindPanel() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState<"analyze" | "generate" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<CoreMindResponse | null>(null);
  const [generated, setGenerated] = useState<CoreMindGenerateResponse | null>(
    null,
  );
  const [activeFile, setActiveFile] = useState(0);

  async function handleAnalyze(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = prompt.trim();
    if (trimmed.length < 3) {
      setError("Décrivez votre projet en au moins 3 caractères.");
      return;
    }

    setLoading("analyze");
    setError(null);
    setAnalysis(null);

    const response = await apiRequest<CoreMindResponse>({
      method: "POST",
      path: `${API_PREFIX}/agents/coremind`,
      body: { prompt: trimmed },
    });

    setLoading(null);

    if (!response.ok) {
      setError(
        apiErrorMessage(
          response,
          "Backend injoignable. Démarrez FastAPI puis réessayez.",
        ),
      );
      return;
    }

    setAnalysis(response.data);
  }

  async function handleGenerate() {
    const trimmed = prompt.trim();
    if (trimmed.length < 3) {
      setError("Décrivez votre projet en au moins 3 caractères.");
      return;
    }

    setLoading("generate");
    setError(null);
    setGenerated(null);

    const response = await apiRequest<CoreMindGenerateResponse>({
      method: "POST",
      path: `${API_PREFIX}/agents/coremind/generate`,
      body: { prompt: trimmed },
    });

    setLoading(null);

    if (!response.ok) {
      setError(
        apiErrorMessage(
          response,
          "Backend injoignable ou ANTHROPIC_API_KEY manquante dans .env",
        ),
      );
      return;
    }

    setGenerated(response.data);
    setActiveFile(0);
  }

  const files =
    generated && generated.files.length > 0
      ? generated.files
      : generated
        ? [{ path: "generated.txt", content: generated.code }]
        : [];

  const displayedCode = files[activeFile]?.content ?? generated?.code ?? "";
  const busy = loading !== null;

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
              Analyse + génération de code via Claude (claude-sonnet-4-20250514)
            </p>
          </div>
          <div className="flex flex-col gap-1 text-right font-mono text-[10px] text-cyber-violet">
            <span>POST {API_PREFIX}/agents/coremind</span>
            <span>POST {API_PREFIX}/agents/coremind/generate</span>
          </div>
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
            disabled={busy}
          />
        </label>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={busy || prompt.trim().length < 3}
            className="cyber-btn disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading === "analyze" ? "Analyse…" : "Analyser"}
          </button>
          <button
            type="button"
            disabled={busy || prompt.trim().length < 3}
            onClick={() => void handleGenerate()}
            className="rounded-md border border-cyber-violet/50 bg-cyber-violet/10 px-4 py-2 text-sm font-medium text-cyber-violet transition hover:border-cyber-violet hover:bg-cyber-violet/20 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading === "generate"
              ? "Génération Claude…"
              : "Générer le code (Claude)"}
          </button>
          {analysis || generated ? (
            <button
              type="button"
              className="rounded-md border border-cyber-border px-3 py-2 text-xs text-cyber-muted transition hover:border-cyber-accent hover:text-cyber-text"
              onClick={() => {
                setAnalysis(null);
                setGenerated(null);
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

      {analysis ? (
        <div className="space-y-4 border-t border-cyber-border bg-cyber-bg/40 p-5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-cyber-violet">
            Analyse
          </p>
          <p className="text-sm leading-relaxed text-cyber-text">
            {analysis.summary}
          </p>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <ResultCard
              label="Type de projet"
              value={analysis.project_type_label}
            />
            <ResultCard
              label="Outil recommandé"
              value={analysis.recommended_tool}
              highlight={TOOL_STYLES[analysis.recommended_tool]}
            />
            <ResultCard
              label="Complexité"
              value={`${analysis.complexity} (${analysis.complexity_score}/10)`}
              highlight={COMPLEXITY_STYLES[analysis.complexity]}
            />
            <ResultCard label="Agent" value={analysis.agent_name} />
          </div>

          <div className="rounded-md border border-cyber-border bg-cyber-surface/80 p-3">
            <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Pourquoi cet outil ?
            </p>
            <p className="mt-1 text-xs leading-relaxed text-cyber-text">
              {analysis.tool_rationale}
            </p>
          </div>

          <div>
            <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-cyber-violet">
              Prochaines étapes
            </p>
            <ol className="space-y-2">
              {analysis.next_steps.map((step, index) => (
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

      {generated ? (
        <div className="space-y-4 border-t border-cyber-border bg-cyber-bg/60 p-5">
          <p className="text-[10px] font-bold uppercase tracking-wider text-cyber-accent">
            Code généré
          </p>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded border border-cyber-accent/40 bg-cyber-accent/10 px-2 py-0.5 text-cyber-neon">
              {generated.provider}
            </span>
            <span className="text-cyber-muted">{generated.model}</span>
            {generated.stack.length > 0 ? (
              <span className="text-cyber-muted">
                · {generated.stack.join(", ")}
              </span>
            ) : null}
          </div>

          <p className="text-sm text-cyber-text">{generated.summary}</p>

          {files.length > 1 ? (
            <div className="flex flex-wrap gap-2">
              {files.map((file, index) => (
                <button
                  key={file.path}
                  type="button"
                  onClick={() => setActiveFile(index)}
                  className={`rounded border px-2 py-1 font-mono text-[10px] ${
                    index === activeFile
                      ? "border-cyber-accent bg-cyber-accent/10 text-cyber-neon"
                      : "border-cyber-border text-cyber-muted hover:border-cyber-violet"
                  }`}
                >
                  {file.path}
                </button>
              ))}
            </div>
          ) : (
            <p className="font-mono text-[10px] text-cyber-muted">
              {files[0]?.path ?? "output"}
            </p>
          )}

          <pre className="max-h-96 overflow-auto rounded-md border border-cyber-border bg-cyber-bg p-4 font-mono text-xs leading-relaxed text-cyber-text">
            <code>{displayedCode}</code>
          </pre>
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
      <p className="text-[10px] uppercase tracking-wider text-cyber-muted">
        {label}
      </p>
      <p className="mt-0.5 font-mono text-sm font-bold">{value}</p>
    </div>
  );
}

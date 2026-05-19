import { useState } from "react";
import { API_PREFIX } from "@shared/constants";
import type { BoltGenerateResponse } from "@shared/types";
import { apiRequest } from "@/lib/api-client";

/**
 * Interface Bolt.new — saisie de prompt et affichage du code généré.
 */
export function BoltPanel() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BoltGenerateResponse | null>(null);
  const [activeFile, setActiveFile] = useState(0);

  async function handleGenerate(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = prompt.trim();
    if (trimmed.length < 3) {
      setError("Décrivez votre projet en au moins 3 caractères.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const response = await apiRequest<BoltGenerateResponse>({
      method: "POST",
      path: `${API_PREFIX}/tools/bolt`,
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
    setActiveFile(0);
  }

  const files =
    result && result.files.length > 0
      ? result.files
      : result
        ? [{ path: "generated.txt", content: result.code }]
        : [];

  const displayedCode = files[activeFile]?.content ?? result?.code ?? "";

  return (
    <section
      className="cyber-panel mb-8 overflow-hidden border-cyber-borderGlow p-0"
      aria-labelledby="bolt-heading"
    >
      <div className="border-b border-cyber-border bg-gradient-to-r from-cyan-500/10 via-cyber-surfaceAlt to-violet-500/10 px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-cyber-accent">
              Outil
            </p>
            <h2 id="bolt-heading" className="text-lg font-bold text-cyber-neon">
              Bolt.new
            </h2>
            <p className="mt-0.5 text-xs text-cyber-muted">
              Génération de code full-stack depuis un prompt
            </p>
          </div>
          <span className="rounded border border-cyber-accent/50 bg-cyber-accent/10 px-2 py-1 font-mono text-[10px] text-cyber-neon">
            POST {API_PREFIX}/tools/bolt
          </span>
        </div>
      </div>

      <form onSubmit={(e) => void handleGenerate(e)} className="space-y-4 p-5">
        <label className="block">
          <span className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-cyber-muted">
            Prompt Bolt
          </span>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            placeholder="Ex. : Crée une landing page React + Tailwind pour une plateforme de cybersécurité avec hero néon et CTA…"
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
            {loading ? "Génération…" : "Générer avec Bolt.new"}
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
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded border border-cyber-violet/40 bg-cyber-violet/10 px-2 py-0.5 text-cyber-violet">
              {result.provider}
            </span>
            <span className="text-cyber-muted">{result.model}</span>
            {result.stack.length > 0 ? (
              <span className="text-cyber-muted">
                · {result.stack.join(", ")}
              </span>
            ) : null}
            {result.project_url ? (
              <a
                href={result.project_url}
                target="_blank"
                rel="noreferrer"
                className="text-cyber-neon underline"
              >
                Ouvrir le projet
              </a>
            ) : null}
          </div>

          <p className="text-sm text-cyber-text">{result.summary}</p>

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

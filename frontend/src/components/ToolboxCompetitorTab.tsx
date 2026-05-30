import { useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  analyzeFirecrawlCompetitor,
  type AnalyzeCompetitorResult,
} from "@/lib/firecrawl-api";
import type { SectorData } from "@/lib/toolbox-api";

const SECTOR_LABELS: Record<string, string> = {
  restauration: "Restauration",
  nautisme: "Nautisme",
  immobilier: "Immobilier",
  sante: "Santé",
  artisanat: "Artisanat",
  beaute: "Beauté",
  sport: "Sport",
  technologie: "Technologie",
  education: "Éducation",
  commerce: "Commerce",
};

function sectorLabel(nom: string): string {
  return SECTOR_LABELS[nom] ?? nom;
}

function BulletList({ items }: { items: string[] }) {
  if (!items.length) {
    return <p className="text-sm text-cf-muted">Aucun élément.</p>;
  }
  return (
    <ul className="space-y-2 text-sm leading-relaxed text-cf-body">
      {items.map((item) => (
        <li key={item} className="flex gap-2">
          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-cf-gold" aria-hidden />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export function ToolboxCompetitorTab({ secteurs }: { secteurs: SectorData[] }) {
  const [url, setUrl] = useState("");
  const [secteur, setSecteur] = useState(secteurs[0]?.nom ?? "commerce");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeCompetitorResult | null>(null);

  async function handleAnalyze(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      setError("Indiquez l'URL du site concurrent.");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    const response = await analyzeFirecrawlCompetitor({
      url: trimmed,
      secteur,
    });
    setBusy(false);
    if (!response.ok || !response.data) {
      setError(apiErrorMessage(response, "Analyse concurrent impossible."));
      return;
    }
    setResult(response.data);
  }

  return (
    <div className="space-y-6">
      <form
        onSubmit={(e) => void handleAnalyze(e)}
        className="rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card"
      >
        <p className="text-sm text-cf-muted">
          Scrape le site avec Firecrawl puis analyse les forces et faiblesses via DeepSeek.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end">
          <label className="block sm:col-span-1">
            <span className="mb-2 block text-xs text-cf-label">URL du concurrent</span>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://exemple-concurrent.fr"
              disabled={busy}
              className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-4 py-2.5 text-sm text-cf-text placeholder:text-cf-muted focus:border-cf-gold/50 focus:outline-none disabled:opacity-60"
            />
          </label>
          <label className="block">
            <span className="mb-2 block text-xs text-cf-label">Secteur</span>
            <select
              value={secteur}
              onChange={(e) => setSecteur(e.target.value)}
              disabled={busy}
              className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2.5 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none disabled:opacity-60 sm:min-w-[180px]"
            >
              {secteurs.map((s) => (
                <option key={s.nom} value={s.nom}>
                  {sectorLabel(s.nom)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <button
          type="submit"
          disabled={busy}
          className="mt-4 inline-flex rounded-control border border-cf-gold bg-cf-gold px-6 py-2.5 text-sm font-semibold text-cf-main transition hover:bg-cf-gold-hover disabled:cursor-not-allowed disabled:opacity-60"
        >
          {busy ? "Analyse en cours…" : "Analyser le concurrent"}
        </button>
      </form>

      {busy ? (
        <div
          className="flex items-center gap-3 rounded-card border border-cf-gold/30 bg-cf-active px-4 py-4"
          role="status"
        >
          <span
            className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-cf-gold border-t-transparent"
            aria-hidden
          />
          <p className="text-sm text-cf-text">
            Scraping Firecrawl et analyse DeepSeek… (30–90 s)
          </p>
        </div>
      ) : null}

      {error ? (
        <p className="rounded-card border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="space-y-4">
          <div className="rounded-card border border-cf-gold/40 bg-cf-active px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-cf-gold">
              Synthèse
            </p>
            <p className="mt-2 text-sm leading-relaxed text-cf-text">{result.analyse}</p>
            {result.composants_recommandes.length > 0 ? (
              <p className="mt-3 text-xs text-cf-muted">
                Composants suggérés :{" "}
                <span className="text-cf-gold">
                  {result.composants_recommandes.join(" · ")}
                </span>
              </p>
            ) : null}
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <article className="rounded-card border border-cf-border-input bg-cf-card p-4 shadow-card">
              <h3 className="mb-3 text-sm font-medium text-cf-gold">Points forts</h3>
              <BulletList items={result.points_forts} />
            </article>
            <article className="rounded-card border border-cf-border-input bg-cf-card p-4 shadow-card">
              <h3 className="mb-3 text-sm font-medium text-cf-gold">Points faibles</h3>
              <BulletList items={result.points_faibles} />
            </article>
            <article className="rounded-card border border-cf-border-input bg-cf-card p-4 shadow-card">
              <h3 className="mb-3 text-sm font-medium text-cf-gold">Suggestions</h3>
              <BulletList items={result.suggestions} />
            </article>
          </div>
        </div>
      ) : null}
    </div>
  );
}

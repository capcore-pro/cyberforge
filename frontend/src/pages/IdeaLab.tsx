import { useState } from "react";
import {
  generateMarketingIdeas,
  generateProductIdeas,
  IDEA_SECTORS,
  type IdeaMode,
  type MarketingIdea,
  type MarketingIdeaResult,
  type ProductIdea,
  type ProductIdeaResult,
} from "@/lib/idea-api";

type IdeaResult = MarketingIdeaResult | ProductIdeaResult;

export function IdeaLab() {
  const [mode, setMode] = useState<IdeaMode>("marketing");
  const [sector, setSector] = useState("");
  const [target, setTarget] = useState("");
  const [context, setContext] = useState("");
  const [budget, setBudget] = useState("medium");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<IdeaResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<number | null>(null);

  async function generate() {
    if (!sector || !target) return;
    setLoading(true);
    setResult(null);
    setError(null);
    setSelected(null);

    try {
      const data =
        mode === "marketing"
          ? await generateMarketingIdeas({ sector, target, context, count: 6 })
          : await generateProductIdeas({ sector, target, context, budget, count: 6 });

      if (data.error) {
        setError(data.error);
        return;
      }

      setResult(data);
      setSelected(data.best_pick ?? 0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }

  function injectToVideoBuilder(idea: MarketingIdea) {
    window.location.hash = `#/video-builder?prompt=${encodeURIComponent(idea.video_prompt || idea.hook)}`;
  }

  function launchInCyberForge(idea: ProductIdea) {
    window.location.hash = `#/generator?brief=${encodeURIComponent(`${idea.name} — ${idea.concept}`)}&type=${idea.cyberforge_type}`;
  }

  const complexityColor = (c: string) =>
    ({
      simple: "text-green-400",
      medium: "text-yellow-400",
      complex: "text-red-400",
    })[c] || "text-gray-400";

  const marketingResult = mode === "marketing" ? (result as MarketingIdeaResult | null) : null;
  const productResult = mode === "product" ? (result as ProductIdeaResult | null) : null;

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          💡 Idea Lab
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          Génère des idées créatives — pub marketing ou produits digitaux
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-6">
        <button
          type="button"
          onClick={() => {
            setMode("marketing");
            setResult(null);
            setError(null);
          }}
          className={`p-4 rounded-xl border text-left transition-colors
            ${mode === "marketing"
              ? "border-purple-500 bg-purple-500/10"
              : "border-gray-700 hover:border-gray-600"}`}
        >
          <p className="text-white font-semibold">🎬 Idées Pub & Marketing</p>
          <p className="text-gray-400 text-xs mt-1">
            Concepts créatifs, scripts vidéo, accroches — injectables dans Video Builder
          </p>
        </button>
        <button
          type="button"
          onClick={() => {
            setMode("product");
            setResult(null);
            setError(null);
          }}
          className={`p-4 rounded-xl border text-left transition-colors
            ${mode === "product"
              ? "border-blue-500 bg-blue-500/10"
              : "border-gray-700 hover:border-gray-600"}`}
        >
          <p className="text-white font-semibold">🚀 Idées Produits Digitaux</p>
          <p className="text-gray-400 text-xs mt-1">
            Apps mobiles, logiciels, SaaS — lançables directement dans CyberForge
          </p>
        </button>
      </div>

      <div className="bg-gray-800 rounded-xl p-5 mb-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-gray-400 mb-1 block">Secteur *</label>
            <select
              className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm"
              value={sector}
              onChange={(e) => setSector(e.target.value)}
            >
              <option value="">Choisir un secteur...</option>
              {IDEA_SECTORS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm text-gray-400 mb-1 block">Cible *</label>
            <input
              className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm"
              placeholder="Ex: artisans plombiers 30-50 ans"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />
          </div>
        </div>

        {mode === "product" && (
          <div>
            <label className="text-sm text-gray-400 mb-1 block">Budget développement</label>
            <div className="flex gap-2">
              {(["low", "medium", "high"] as const).map((b) => (
                <button
                  key={b}
                  type="button"
                  onClick={() => setBudget(b)}
                  className={`px-4 py-1.5 rounded-lg text-sm transition-colors
                    ${budget === b
                      ? "bg-blue-600 text-white"
                      : "bg-gray-700 text-gray-400 hover:text-white"}`}
                >
                  {b === "low" ? "Petit" : b === "medium" ? "Moyen" : "Grand"}
                </button>
              ))}
            </div>
          </div>
        )}

        <div>
          <label className="text-sm text-gray-400 mb-1 block">
            Contexte supplémentaire (optionnel)
          </label>
          <input
            className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm"
            placeholder="Ex: concurrent principal, zone géographique, contraintes..."
            value={context}
            onChange={(e) => setContext(e.target.value)}
          />
        </div>

        <button
          type="button"
          onClick={() => void generate()}
          disabled={loading || !sector || !target}
          className="w-full py-3 bg-gradient-to-r from-purple-600 to-blue-600
                     hover:from-purple-700 hover:to-blue-700
                     disabled:opacity-50 text-white font-medium rounded-lg
                     transition-all flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <span className="animate-spin">⚙</span> Génération en cours...
            </>
          ) : (
            <>
              ✨ Générer {mode === "marketing" ? "6 idées marketing" : "6 idées produits"}
            </>
          )}
        </button>
      </div>

      {result && (
        <div className="space-y-4">
          {(marketingResult?.summary || productResult?.market_insight) && (
            <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
              <p className="text-gray-300 text-sm italic">
                💬 {marketingResult?.summary || productResult?.market_insight}
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 gap-3">
            {result.ideas?.map((idea, i) => (
              <div
                key={i}
                onClick={() => setSelected(i)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") setSelected(i);
                }}
                role="button"
                tabIndex={0}
                className={`bg-gray-800 rounded-xl p-4 cursor-pointer transition-all border
                  ${selected === i
                    ? "border-purple-500 bg-purple-500/5"
                    : "border-gray-700 hover:border-gray-600"}`}
              >
                {i === result.best_pick && (
                  <span className="inline-block mb-2 px-2 py-0.5 bg-yellow-500/20
                                   text-yellow-400 text-xs rounded-full font-medium">
                    ⭐ Meilleure idée
                  </span>
                )}

                {mode === "marketing" ? (
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <p className="text-white font-semibold">{(idea as MarketingIdea).title}</p>
                      <p className="text-gray-400 text-sm mt-1">{(idea as MarketingIdea).concept}</p>
                      <div className="flex gap-2 mt-2 flex-wrap">
                        <span className="px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded">
                          {(idea as MarketingIdea).format}
                        </span>
                        <span className="px-2 py-0.5 bg-gray-700 text-purple-300 text-xs rounded">
                          {(idea as MarketingIdea).emotional_angle}
                        </span>
                        {(idea as MarketingIdea).video_ready && (
                          <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">
                            🎬 Video Ready
                          </span>
                        )}
                      </div>
                      {selected === i && (
                        <div className="mt-3 p-3 bg-gray-700/50 rounded-lg">
                          <p className="text-xs text-gray-400 mb-1">Accroche :</p>
                          <p className="text-white text-sm italic">
                            &ldquo;{(idea as MarketingIdea).hook}&rdquo;
                          </p>
                        </div>
                      )}
                    </div>
                    {(idea as MarketingIdea).video_ready && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          injectToVideoBuilder(idea as MarketingIdea);
                        }}
                        className="shrink-0 px-3 py-1.5 bg-purple-600 hover:bg-purple-700
                                   text-white text-xs rounded-lg transition-colors"
                      >
                        → Video Builder
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <p className="text-white font-semibold">{(idea as ProductIdea).name}</p>
                      <p className="text-gray-400 text-sm mt-1">{(idea as ProductIdea).concept}</p>
                      <div className="flex gap-2 mt-2 flex-wrap">
                        <span className="px-2 py-0.5 bg-gray-700 text-blue-300 text-xs rounded">
                          {(idea as ProductIdea).type}
                        </span>
                        <span
                          className={`px-2 py-0.5 bg-gray-700 text-xs rounded ${complexityColor((idea as ProductIdea).complexity)}`}
                        >
                          {(idea as ProductIdea).complexity}
                        </span>
                        <span className="px-2 py-0.5 bg-gray-700 text-gray-300 text-xs rounded">
                          ⏱ {(idea as ProductIdea).dev_time}
                        </span>
                      </div>
                      {selected === i && (
                        <div className="mt-3 space-y-2">
                          <div className="p-3 bg-gray-700/50 rounded-lg">
                            <p className="text-xs text-gray-400 mb-1">Problème résolu :</p>
                            <p className="text-white text-sm">{(idea as ProductIdea).problem_solved}</p>
                          </div>
                          <div className="p-3 bg-gray-700/50 rounded-lg">
                            <p className="text-xs text-gray-400 mb-1">Revenus potentiels :</p>
                            <p className="text-green-400 text-sm font-medium">
                              {(idea as ProductIdea).revenue_model} —{" "}
                              {(idea as ProductIdea).revenue_potential}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                    {(idea as ProductIdea).cyberforge_ready && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          launchInCyberForge(idea as ProductIdea);
                        }}
                        className="shrink-0 px-3 py-1.5 bg-blue-600 hover:bg-blue-700
                                   text-white text-xs rounded-lg transition-colors"
                      >
                        → Lancer dans CyberForge
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4">
          <p className="text-red-400 text-sm">Erreur : {error}</p>
        </div>
      )}
    </div>
  );
}

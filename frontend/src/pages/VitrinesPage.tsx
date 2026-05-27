import { useCallback, useEffect, useMemo, useState } from "react";
import type { ManagedProjectRecord } from "@shared/types";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  createVitrine,
  deleteVitrine,
  hardDeleteVitrine,
  listVitrines,
  updateVitrine,
} from "@/lib/vitrines-api";

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case "draft":
      return "Brouillon";
    case "building":
      return "En déploiement";
    case "deployed":
      return "Déployé";
    case "failed":
      return "Échec";
    case "deleted":
      return "Supprimé";
    default:
      return status;
  }
}

export function VitrinesPage() {
  const [items, setItems] = useState<ManagedProjectRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [prompt, setPrompt] = useState("");
  const [slug, setSlug] = useState("");
  const [createBusy, setCreateBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const hasBuilding = useMemo(
    () => items.some((p) => p.status === "building"),
    [items],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await listVitrines();
      if (!resp.ok) {
        setError(apiErrorMessage(resp, "Impossible de charger les vitrines."));
        return;
      }
      setItems(Array.isArray(resp.data) ? resp.data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur chargement vitrines.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Auto-refresh pendant un déploiement
  useEffect(() => {
    if (!hasBuilding) return;
    const id = window.setInterval(() => void load(), 4000);
    return () => window.clearInterval(id);
  }, [hasBuilding, load]);

  async function onCreate() {
    setActionError(null);
    const trimmed = prompt.trim();
    if (trimmed.length < 10) {
      setActionError("Prompt trop court.");
      return;
    }
    setCreateBusy(true);
    try {
      const resp = await createVitrine(trimmed, slug.trim() || undefined);
      if (!resp.ok) {
        setActionError(apiErrorMessage(resp, "Création impossible."));
        return;
      }
      setPrompt("");
      setSlug("");
      await load();
    } finally {
      setCreateBusy(false);
    }
  }

  async function onUpdate(id: string) {
    setActionError(null);
    const txt = window.prompt("Nouveau prompt (mise à jour vitrine) ?");
    if (!txt) return;
    const resp = await updateVitrine(id, txt);
    if (!resp.ok) {
      setActionError(apiErrorMessage(resp, "Mise à jour impossible."));
      return;
    }
    await load();
  }

  async function onDelete(id: string) {
    setActionError(null);
    if (!window.confirm("Supprimer la vitrine ? (soft delete)")) return;
    const resp = await deleteVitrine(id);
    if (!resp.ok) {
      setActionError(apiErrorMessage(resp, "Suppression impossible."));
      return;
    }
    await load();
  }

  async function onHardDelete(id: string) {
    setActionError(null);
    if (
      !window.confirm(
        "Hard delete : supprimer la branche GitHub + nettoyer les déploiements Vercel ?",
      )
    )
      return;
    const resp = await hardDeleteVitrine(id);
    if (!resp.ok) {
      setActionError(apiErrorMessage(resp, "Hard delete impossible."));
      return;
    }
    await load();
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-white/10 bg-white/5 p-4">
        <div className="text-lg font-semibold">Vitrines (Vercel)</div>
        <div className="mt-2 grid gap-2 md:grid-cols-2">
          <textarea
            className="h-28 w-full rounded bg-black/30 p-2 text-sm outline-none"
            placeholder="Prompt vitrine…"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <div className="space-y-2">
            <input
              className="w-full rounded bg-black/30 p-2 text-sm outline-none"
              placeholder="Slug (optionnel) ex: boulangerie-le-fournil"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
            />
            <button
              className="w-full rounded bg-white/10 px-3 py-2 text-sm hover:bg-white/15 disabled:opacity-50"
              onClick={() => void onCreate()}
              disabled={createBusy}
            >
              {createBusy ? "Création…" : "Créer + déployer"}
            </button>
            {actionError ? (
              <div className="text-sm text-red-300">{actionError}</div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-white/10 bg-white/5 p-4">
        <div className="flex items-center justify-between">
          <div className="text-lg font-semibold">Projets</div>
          <button
            className="rounded bg-white/10 px-3 py-1 text-sm hover:bg-white/15"
            onClick={() => void load()}
          >
            Rafraîchir
          </button>
        </div>

        {loading ? <div className="mt-3 text-sm opacity-80">Chargement…</div> : null}
        {error ? <div className="mt-3 text-sm text-red-300">{error}</div> : null}

        <div className="mt-3 space-y-3">
          {items.map((p) => (
            <div
              key={p.id}
              className="rounded border border-white/10 bg-black/20 p-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-semibold">
                  {p.title || p.slug}{" "}
                  <span className="ml-2 text-xs opacity-70">
                    ({statusLabel(p.status)})
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    className="rounded bg-white/10 px-2 py-1 text-xs hover:bg-white/15"
                    onClick={() => void onUpdate(p.id)}
                  >
                    Modifier
                  </button>
                  <button
                    className="rounded bg-white/10 px-2 py-1 text-xs hover:bg-white/15"
                    onClick={() => void onDelete(p.id)}
                  >
                    Supprimer
                  </button>
                  <button
                    className="rounded bg-red-500/20 px-2 py-1 text-xs hover:bg-red-500/30"
                    onClick={() => void onHardDelete(p.id)}
                  >
                    Hard delete
                  </button>
                </div>
              </div>
              <div className="mt-2 text-xs opacity-80">
                Dernière maj: {formatDate(p.updated_at)}
              </div>
              {p.url_preview ? (
                <div className="mt-2 text-sm">
                  URL:{" "}
                  <a
                    className="underline"
                    href={p.url_preview}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {p.url_preview}
                  </a>
                </div>
              ) : null}
              {p.error_last ? (
                <div className="mt-2 text-sm text-red-300">{p.error_last}</div>
              ) : null}
            </div>
          ))}
          {!items.length && !loading ? (
            <div className="text-sm opacity-80">Aucune vitrine pour l’instant.</div>
          ) : null}
        </div>
      </div>
    </div>
  );
}


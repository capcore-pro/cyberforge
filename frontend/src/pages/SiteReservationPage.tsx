import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ManagedProjectRecord } from "@shared/types";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  createReservationSite,
  deleteReservationSite,
  hardDeleteReservationSite,
  listReservationSites,
  updateReservationSite,
} from "@/lib/site-reservation-api";

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
      return "Déploiement…";
    case "deployed":
      return "En ligne";
    case "failed":
      return "Échec";
    case "deleted":
      return "Supprimé";
    default:
      return status;
  }
}

export function SiteReservationPage() {
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

  const pollTimerRef = useRef<number | null>(null);
  const lastItemsRef = useRef<ManagedProjectRecord[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await listReservationSites();
      if (!resp.ok) {
        setError(apiErrorMessage(resp, "Impossible de charger les sites réservation."));
        return;
      }
      const next = Array.isArray(resp.data) ? resp.data : [];
      lastItemsRef.current = next;
      setItems(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur chargement réservation.");
    } finally {
      setLoading(false);
    }
  }, []);

  const pollStatuses = useCallback(async () => {
    try {
      const resp = await listReservationSites();
      if (!resp.ok || !Array.isArray(resp.data)) return;
      const next = resp.data;
      const prev = lastItemsRef.current;

      const prevById = new Map(prev.map((p) => [p.id, p]));
      const nextById = new Map(next.map((p) => [p.id, p]));
      const merged: ManagedProjectRecord[] = [];
      for (const old of prev) merged.push(nextById.get(old.id) ?? old);
      for (const fresh of next) if (!prevById.has(fresh.id)) merged.push(fresh);

      const changed =
        merged.length !== prev.length ||
        merged.some((p, idx) => {
          const o = prev[idx];
          if (!o) return true;
          return (
            p.id !== o.id ||
            p.status !== o.status ||
            p.updated_at !== o.updated_at ||
            p.error_last !== o.error_last ||
            p.url_production !== o.url_production
          );
        });
      if (changed) {
        lastItemsRef.current = merged;
        setItems(merged);
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (pollTimerRef.current) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    if (!hasBuilding) return;
    pollTimerRef.current = window.setInterval(() => void pollStatuses(), 2500);
    return () => {
      if (pollTimerRef.current) {
        window.clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [hasBuilding, pollStatuses]);

  async function onCreate() {
    setActionError(null);
    const trimmed = prompt.trim();
    if (trimmed.length < 10) {
      setActionError("Prompt trop court.");
      return;
    }
    setCreateBusy(true);
    try {
      const resp = await createReservationSite(trimmed, slug.trim() || undefined);
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
    const txt = window.prompt("Nouveau prompt (mise à jour site réservation) ?");
    if (!txt) return;
    const resp = await updateReservationSite(id, txt);
    if (!resp.ok) {
      setActionError(apiErrorMessage(resp, "Mise à jour impossible."));
      return;
    }
    await load();
  }

  async function onDelete(id: string) {
    setActionError(null);
    if (!window.confirm("Supprimer le site ? (soft delete)")) return;
    const resp = await deleteReservationSite(id);
    if (!resp.ok) {
      setActionError(apiErrorMessage(resp, "Suppression impossible."));
      return;
    }
    await load();
  }

  async function onHardDelete(id: string) {
    setActionError(null);
    if (!window.confirm("Hard delete : supprimer branche GitHub + projet Vercel ?")) return;
    const resp = await hardDeleteReservationSite(id);
    if (!resp.ok) {
      setActionError(apiErrorMessage(resp, "Hard delete impossible."));
      return;
    }
    await load();
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-white/10 bg-white/5 p-4">
        <div className="text-lg font-semibold">Sites de réservation (V1)</div>
        <div className="mt-2 grid gap-2 md:grid-cols-2">
          <textarea
            className="h-28 w-full rounded bg-black/30 p-2 text-sm outline-none"
            placeholder="Prompt site réservation…"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <div className="space-y-2">
            <input
              className="w-full rounded bg-black/30 p-2 text-sm outline-none"
              placeholder="Slug (optionnel) ex: salon-paris-15"
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
            {actionError ? <div className="text-sm text-red-300">{actionError}</div> : null}
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
            <div key={p.id} className="rounded border border-white/10 bg-black/20 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-[220px]">
                  <div className="font-medium">{p.slug}</div>
                  <div className="text-xs opacity-70">Créé: {formatDate(p.created_at)}</div>
                </div>
                <div className="text-sm">
                  <span className="rounded bg-white/10 px-2 py-1">{statusLabel(p.status)}</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {p.url_production ? (
                    <a
                      className="rounded bg-white/10 px-3 py-1 text-sm hover:bg-white/15"
                      href={p.url_production}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Ouvrir
                    </a>
                  ) : null}
                  <button
                    className="rounded bg-white/10 px-3 py-1 text-sm hover:bg-white/15"
                    onClick={() => void onUpdate(p.id)}
                  >
                    Modifier
                  </button>
                  <button
                    className="rounded bg-white/10 px-3 py-1 text-sm hover:bg-white/15"
                    onClick={() => void onDelete(p.id)}
                  >
                    Supprimer
                  </button>
                  <button
                    className="rounded bg-red-500/20 px-3 py-1 text-sm hover:bg-red-500/30"
                    onClick={() => void onHardDelete(p.id)}
                  >
                    Hard delete
                  </button>
                </div>
              </div>
              {p.error_last ? <div className="mt-2 text-sm text-red-300">{p.error_last}</div> : null}
              {p.url_backend ? (
                <div className="mt-2 text-xs opacity-70">API: {p.url_backend}</div>
              ) : null}
            </div>
          ))}
          {!loading && items.length === 0 ? (
            <div className="text-sm opacity-70">Aucun site réservation.</div>
          ) : null}
        </div>
      </div>
    </div>
  );
}


import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ManagedProjectRecord } from "@shared/types";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  createApplicationWeb,
  deleteApplicationWeb,
  hardDeleteApplicationWeb,
  listApplicationWeb,
  updateApplicationWeb,
} from "@/lib/application-web-api";

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

function statusBadgeClass(status: string): string {
  switch (status) {
    case "deployed":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
    case "building":
      return "border-cyber-accent/40 bg-cyber-accent/10 text-cyber-neon";
    case "failed":
      return "border-red-500/40 bg-red-500/10 text-red-200";
    case "deleted":
      return "border-cyber-border text-cyber-muted";
    default:
      return "border-cyber-border bg-cyber-bg/60 text-cyber-muted";
  }
}

export function ApplicationWebPage() {
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
      const resp = await listApplicationWeb();
      if (!resp.ok) {
        setError(apiErrorMessage(resp, "Impossible de charger les applications web."));
        return;
      }
      const next = Array.isArray(resp.data) ? resp.data : [];
      lastItemsRef.current = next;
      setItems(next);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Erreur lors du chargement.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const pollStatuses = useCallback(async () => {
    try {
      const resp = await listApplicationWeb();
      if (!resp.ok || !Array.isArray(resp.data)) return;
      const next = resp.data;
      const prev = lastItemsRef.current;

      const prevById = new Map(prev.map((p) => [p.id, p]));
      const nextById = new Map(next.map((p) => [p.id, p]));
      const merged: ManagedProjectRecord[] = [];
      for (const old of prev) {
        const fresh = nextById.get(old.id);
        merged.push(fresh ?? old);
      }
      for (const fresh of next) {
        if (!prevById.has(fresh.id)) merged.push(fresh);
      }

      const changed =
        merged.length !== prev.length ||
        merged.some((p, idx) => {
          const o = prev[idx];
          if (!o) return true;
          return (
            p.id !== o.id ||
            p.status !== o.status ||
            p.updated_at !== o.updated_at ||
            p.url_production !== o.url_production ||
            p.url_backend !== o.url_backend ||
            p.error_last !== o.error_last
          );
        });
      if (changed) {
        lastItemsRef.current = merged;
        setItems(merged);
      }
    } catch {
      // ignore polling errors
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
    pollTimerRef.current = window.setInterval(() => void pollStatuses(), 4000);
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
      setActionError("Le prompt doit contenir au moins 10 caractères.");
      return;
    }
    setCreateBusy(true);
    try {
      const resp = await createApplicationWeb(trimmed, slug.trim() || undefined);
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
    const txt = window.prompt("Nouveau prompt pour cette application web ?");
    if (!txt) return;
    const resp = await updateApplicationWeb(id, txt);
    if (!resp.ok) {
      setActionError(apiErrorMessage(resp, "Mise à jour impossible."));
      return;
    }
    await load();
  }

  async function onDelete(id: string) {
    setActionError(null);
    if (!window.confirm("Supprimer cette application web ? (suppression logique)")) {
      return;
    }
    const resp = await deleteApplicationWeb(id);
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
        "Suppression définitive : dépôts GitHub, projet Vercel et service Railway ?",
      )
    ) {
      return;
    }
    const resp = await hardDeleteApplicationWeb(id);
    if (!resp.ok) {
      setActionError(apiErrorMessage(resp, "Suppression définitive impossible."));
      return;
    }
    await load();
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.35em] text-cyber-violet">
          // applications_web
        </p>
        <h1 className="text-2xl font-bold text-cyber-neon md:text-3xl">
          Applications web
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-cyber-muted">
          Déploiement Railway (backend) et Vercel (frontend) à partir d&apos;un
          prompt.
        </p>
      </header>

      <section className="cyber-panel space-y-4 p-5">
        <h2 className="text-sm font-semibold text-cyber-text">Nouvelle application</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block space-y-1 md:col-span-2">
            <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Prompt
            </span>
            <textarea
              className="cyber-prompt-field min-h-[7rem]"
              placeholder="Décrivez l'application web à générer et déployer…"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
          </label>
          <label className="block space-y-1">
            <span className="text-[10px] uppercase tracking-wider text-cyber-muted">
              Slug (optionnel)
            </span>
            <input
              className="cyber-prompt-field min-h-0"
              placeholder="ex. crm-agence"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
            />
          </label>
          <div className="flex items-end">
            <button
              type="button"
              className="cyber-generate-btn w-full disabled:opacity-50"
              onClick={() => void onCreate()}
              disabled={createBusy}
            >
              {createBusy ? "Création en cours…" : "Créer et déployer"}
            </button>
          </div>
        </div>
        {actionError ? (
          <p className="rounded border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
            {actionError}
          </p>
        ) : null}
      </section>

      <section className="cyber-panel p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-cyber-text">Projets déployés</h2>
          <button
            type="button"
            className="cyber-action-btn"
            onClick={() => void load()}
          >
            Rafraîchir
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-cyber-muted animate-pulse">Chargement…</p>
        ) : null}
        {error ? (
          <p className="rounded border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        ) : null}

        <div className="mt-3 space-y-3">
          {items.map((p) => (
            <article
              key={p.id}
              className="rounded-lg border border-cyber-border bg-cyber-bg/50 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-cyber-text">
                    {p.title || p.slug}
                  </h3>
                  <span
                    className={`mt-1 inline-block rounded border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${statusBadgeClass(p.status)}`}
                  >
                    {statusLabel(p.status)}
                  </span>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="cyber-action-btn text-[10px]"
                    onClick={() => void onUpdate(p.id)}
                  >
                    Modifier
                  </button>
                  <button
                    type="button"
                    className="cyber-action-btn text-[10px]"
                    onClick={() => void onDelete(p.id)}
                  >
                    Supprimer
                  </button>
                  <button
                    type="button"
                    className="cyber-action-btn border-red-500/40 text-[10px] text-red-300"
                    onClick={() => void onHardDelete(p.id)}
                  >
                    Suppression définitive
                  </button>
                </div>
              </div>

              <p className="mt-2 text-xs text-cyber-muted">
                Dernière mise à jour : {formatDate(p.updated_at)}
              </p>

              {p.url_production ? (
                <p className="mt-2 text-sm text-cyber-text">
                  Interface :{" "}
                  <a
                    className="text-cyber-neon underline hover:text-cyber-accent"
                    href={p.url_production}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {p.url_production}
                  </a>
                </p>
              ) : null}
              {p.url_backend ? (
                <p className="mt-1 text-sm text-cyber-text">
                  API :{" "}
                  <a
                    className="text-cyber-neon underline hover:text-cyber-accent"
                    href={p.url_backend}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {p.url_backend}
                  </a>
                </p>
              ) : null}

              {p.error_last ? (
                <p className="mt-2 rounded border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
                  {p.error_last}
                </p>
              ) : null}
            </article>
          ))}
          {!items.length && !loading && !error ? (
            <p className="text-sm text-cyber-muted">
              Aucune application web pour l&apos;instant.
            </p>
          ) : null}
        </div>
      </section>
    </div>
  );
}

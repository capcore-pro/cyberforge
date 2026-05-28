import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ManagedProjectRecord } from "@shared/types";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  createVitrine,
  deleteVitrine,
  hardDeleteVitrine,
  listVitrines,
  updateVitrine,
} from "@/lib/vitrines-api";
import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

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
  const [previewTarget, setPreviewTarget] = useState<ManagedProjectRecord | null>(
    null,
  );
  const [previewBusy, setPreviewBusy] = useState(false);
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  const [authById, setAuthById] = useState<
    Record<
      string,
      { enabled: boolean; client_email: string | null; password: string | null }
    >
  >({});
  const [authBusyId, setAuthBusyId] = useState<string | null>(null);

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

  const pollStatuses = useCallback(async () => {
    // Ne touche pas à "loading" pour éviter les clignotements.
    try {
      const resp = await listVitrines();
      if (!resp.ok || !Array.isArray(resp.data)) {
        return;
      }
      const next = resp.data;
      const prev = lastItemsRef.current;
      // Merge sans casser la stabilité : garder l'ordre précédent, puis ajouter les nouveaux.
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
      // Evite setState si rien n'a changé sur les champs "dynamiques".
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
            p.url_preview !== o.url_preview ||
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

  // Auto-refresh pendant un déploiement
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

  useEffect(() => {
    lastItemsRef.current = items;
  }, [items]);

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

  async function loadAuth(id: string) {
    setAuthBusyId(id);
    try {
      const resp = await apiRequest<{
        enabled: boolean;
        client_email: string | null;
        password: string | null;
      }>({
        method: "GET",
        path: `${API_PREFIX}/managed-projects/vitrines/${id}/auth`,
      });
      if (resp.ok) {
        setAuthById((prev) => ({ ...prev, [id]: resp.data }));
      } else {
        setActionError(apiErrorMessage(resp, "Chargement mot de passe impossible."));
      }
    } finally {
      setAuthBusyId(null);
    }
  }

  async function toggleAuth(id: string, enabled: boolean) {
    setAuthBusyId(id);
    try {
      const resp = await apiRequest<{
        enabled: boolean;
        client_email: string | null;
        password: string | null;
      }>({
        method: "POST",
        path: `${API_PREFIX}/managed-projects/vitrines/${id}/auth`,
        body: { enabled },
      });
      if (resp.ok) {
        setAuthById((prev) => ({ ...prev, [id]: resp.data }));
      } else {
        setActionError(apiErrorMessage(resp, "Mise à jour mot de passe impossible."));
      }
    } finally {
      setAuthBusyId(null);
    }
  }

  async function regeneratePassword(id: string) {
    setAuthBusyId(id);
    try {
      const resp = await apiRequest<{
        enabled: boolean;
        client_email: string | null;
        password: string | null;
      }>({
        method: "POST",
        path: `${API_PREFIX}/managed-projects/vitrines/${id}/auth`,
        body: { generate_password: true },
      });
      if (resp.ok) {
        setAuthById((prev) => ({ ...prev, [id]: resp.data }));
      } else {
        setActionError(apiErrorMessage(resp, "Génération mot de passe impossible."));
      }
    } finally {
      setAuthBusyId(null);
    }
  }

  async function openPreview(p: ManagedProjectRecord) {
    setPreviewTarget(p);
    setPreviewImage(null);
    const url = p.url_production || p.url_preview;
    if (!url) return;
    setPreviewBusy(true);
    try {
      const resp = await apiRequest<{ screenshot_url: string | null }>({
        method: "GET",
        path: `${API_PREFIX}/managed-projects/vitrines/${p.id}/preview`,
      });
      if (resp.ok) {
        setPreviewImage(resp.data?.screenshot_url ?? null);
      }
    } finally {
      setPreviewBusy(false);
    }
  }

  function closePreview() {
    setPreviewTarget(null);
    setPreviewImage(null);
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
              {authById[p.id] ? (
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2 rounded border border-white/10 bg-white/5 px-2 py-1 text-xs">
                  <div className="opacity-80">
                    Mot de passe:{" "}
                    <span className="font-mono text-white">
                      {authById[p.id].password || "—"}
                    </span>{" "}
                    <span className="ml-2 opacity-60">
                      ({authById[p.id].enabled ? "protégé" : "non protégé"})
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      className="rounded bg-white/10 px-2 py-0.5 hover:bg-white/15 disabled:opacity-50"
                      onClick={() => void toggleAuth(p.id, !authById[p.id].enabled)}
                      disabled={authBusyId === p.id}
                    >
                      {authById[p.id].enabled ? "Désactiver" : "Activer"}
                    </button>
                    <button
                      className="rounded bg-white/10 px-2 py-0.5 hover:bg-white/15 disabled:opacity-50"
                      onClick={() => void regeneratePassword(p.id)}
                      disabled={authBusyId === p.id}
                    >
                      Nouveau
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mb-2 flex items-center justify-between gap-2 text-xs opacity-80">
                  <span>Mot de passe: —</span>
                  <button
                    className="rounded bg-white/10 px-2 py-0.5 hover:bg-white/15 disabled:opacity-50"
                    onClick={() => void loadAuth(p.id)}
                    disabled={authBusyId === p.id}
                  >
                    {authBusyId === p.id ? "Chargement…" : "Afficher"}
                  </button>
                </div>
              )}
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
                    onClick={() => void openPreview(p)}
                    disabled={!p.url_production && !p.url_preview}
                  >
                    Aperçu
                  </button>
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
              {p.url_production || p.url_preview ? (
                <div className="mt-2 text-sm">
                  URL:{" "}
                  <a
                    className="underline"
                    href={p.url_production || p.url_preview || undefined}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {p.url_production || p.url_preview}
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

      {previewTarget ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
        >
          <div className="flex h-[min(90vh,720px)] w-full max-w-5xl flex-col overflow-hidden rounded-lg border border-white/10 bg-[#0a0a0f]">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-4 py-3">
              <div>
                <div className="text-xs font-bold uppercase tracking-[0.2em] text-cyber-neon">
                  Aperçu vitrine
                </div>
                <div className="text-[10px] text-cyber-muted">
                  {previewTarget.url_production || previewTarget.url_preview}
                </div>
              </div>
              <button
                type="button"
                onClick={closePreview}
                className="rounded border border-white/10 px-3 py-1 text-xs text-cyber-muted hover:border-white/20 hover:text-white"
              >
                Fermer
              </button>
            </div>
            <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 p-3 md:grid-cols-2">
              <div className="min-h-0 overflow-hidden rounded border border-white/10 bg-black/20">
                <iframe
                  title="Vitrine (production)"
                  className="h-full w-full bg-white"
                  src={previewTarget.url_production || previewTarget.url_preview || undefined}
                />
              </div>
              <div className="min-h-0 overflow-hidden rounded border border-white/10 bg-black/20 p-2">
                <div className="mb-2 flex items-center justify-between text-xs">
                  <span className="opacity-80">Screenshot</span>
                  <span className="opacity-60">
                    {previewBusy ? "Génération…" : previewImage ? "OK" : "—"}
                  </span>
                </div>
                {previewImage ? (
                  <img
                    src={previewImage}
                    alt="Capture vitrine"
                    className="h-[min(70vh,520px)] w-full object-contain object-top"
                  />
                ) : (
                  <div className="text-xs opacity-70">
                    {previewBusy
                      ? "Capture en cours…"
                      : "Capture indisponible (Replicate non configuré ou erreur)."}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}


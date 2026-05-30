import { useCallback, useEffect, useState } from "react";
import { BackButton } from "@/components/BackButton";
import { PasswordRevealField } from "@/components/PasswordRevealField";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  STATUS_LABELS,
  TYPE_LABELS,
  type UnifiedProject,
} from "@/lib/unified-projects";
import {
  fetchVitrineAuth,
  regenerateVitrinePassword,
  toggleVitrineAuth,
  type VitrineAuthInfo,
} from "@/lib/vitrines-api";

interface ProjectDetailProps {
  project: UnifiedProject;
  onClose: () => void;
  onEdit: () => void;
  onView: () => void;
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function statusDotClass(status: UnifiedProject["status"]): string {
  if (status === "online") return "bg-cf-success";
  if (status === "demo") return "bg-cf-info";
  return "bg-red-500";
}

/**
 * Fiche détail d'un projet unifié — infos + mot de passe vitrine si disponible.
 */
export function ProjectDetail({
  project,
  onClose,
  onEdit,
  onView,
}: ProjectDetailProps) {
  const isVitrine = project.source === "managed_vitrine" && Boolean(project.managedId);

  const [auth, setAuth] = useState<VitrineAuthInfo | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const loadAuth = useCallback(async () => {
    if (!project.managedId) return;
    setAuthLoading(true);
    setAuthError(null);
    try {
      const resp = await fetchVitrineAuth(project.managedId);
      if (resp.ok && resp.data) {
        setAuth(resp.data);
      } else {
        setAuthError(apiErrorMessage(resp, "Impossible de charger le mot de passe."));
      }
    } finally {
      setAuthLoading(false);
    }
  }, [project.managedId]);

  useEffect(() => {
    setAuth(null);
    setAuthError(null);
    if (isVitrine) {
      void loadAuth();
    }
  }, [isVitrine, loadAuth]);

  async function handleToggleAuth() {
    if (!project.managedId || !auth) return;
    setAuthBusy(true);
    setAuthError(null);
    try {
      const resp = await toggleVitrineAuth(project.managedId, !auth.enabled);
      if (resp.ok && resp.data) {
        setAuth(resp.data);
      } else {
        setAuthError(apiErrorMessage(resp, "Mise à jour impossible."));
      }
    } finally {
      setAuthBusy(false);
    }
  }

  async function handleRegeneratePassword() {
    if (!project.managedId) return;
    setAuthBusy(true);
    setAuthError(null);
    try {
      const resp = await regenerateVitrinePassword(project.managedId);
      if (resp.ok && resp.data) {
        setAuth(resp.data);
      } else {
        setAuthError(apiErrorMessage(resp, "Génération impossible."));
      }
    } finally {
      setAuthBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={`Fiche projet — ${project.name}`}
      onClick={onClose}
    >
      <aside
        className="flex h-full w-full max-w-md flex-col border-l border-cf-border-input bg-cf-card shadow-card"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="border-b border-cf-border-input px-5 py-4">
          <BackButton onClick={onClose} />
          <p className="cf-section-label mt-3">Fiche projet</p>
          <h2 className="mt-1 text-lg font-semibold text-cf-text">{project.name}</h2>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="rounded border border-cf-gold/30 bg-cf-gold-subtle px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-cf-gold">
              {TYPE_LABELS[project.type]}
            </span>
            <span className="flex items-center gap-1.5 text-xs text-cf-muted">
              <span
                className={`inline-block h-2 w-2 rounded-full ${statusDotClass(project.status)}`}
                aria-hidden
              />
              {STATUS_LABELS[project.status]}
            </span>
          </div>
        </header>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
          <div>
            <p className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
              URL
            </p>
            {project.url ? (
              <button
                type="button"
                onClick={onView}
                className="mt-1 break-all text-left text-sm text-cf-info hover:text-cf-gold hover:underline"
              >
                {project.url}
              </button>
            ) : (
              <p className="mt-1 text-sm text-cf-muted">—</p>
            )}
          </div>

          <div>
            <p className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
              Créé le
            </p>
            <p className="mt-1 text-sm text-cf-text">{formatDate(project.createdAt)}</p>
          </div>

          {project.prompt ? (
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
                Prompt
              </p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-cf-muted">{project.prompt}</p>
            </div>
          ) : null}

          {isVitrine ? (
            <div className="space-y-3 rounded-card border border-cf-border-input bg-cf-secondary/40 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs font-medium text-cf-text">Protection par mot de passe</p>
                {auth ? (
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
                      auth.enabled
                        ? "border-cf-gold/40 bg-cf-active text-cf-gold"
                        : "border-cf-border-input text-cf-muted"
                    }`}
                  >
                    {auth.enabled ? "Activée" : "Désactivée"}
                  </span>
                ) : null}
              </div>

              {authLoading ? (
                <p className="text-xs text-cf-muted animate-pulse">Chargement du mot de passe…</p>
              ) : auth ? (
                <>
                  <PasswordRevealField password={auth.password} />
                  {auth.client_email ? (
                    <p className="text-[11px] text-cf-muted">
                      Client : {auth.client_email}
                    </p>
                  ) : null}
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={authBusy}
                      onClick={() => void handleToggleAuth()}
                      className="rounded-control border border-cf-border-input bg-cf-secondary px-3 py-1.5 text-xs text-cf-text hover:border-cf-gold/50 hover:text-cf-gold disabled:opacity-50"
                    >
                      {auth.enabled ? "Désactiver" : "Activer"}
                    </button>
                    <button
                      type="button"
                      disabled={authBusy}
                      onClick={() => void handleRegeneratePassword()}
                      className="rounded-control border border-cf-border-input bg-cf-secondary px-3 py-1.5 text-xs text-cf-text hover:border-cf-gold/50 hover:text-cf-gold disabled:opacity-50"
                    >
                      Nouveau mot de passe
                    </button>
                  </div>
                </>
              ) : (
                <button
                  type="button"
                  disabled={authLoading}
                  onClick={() => void loadAuth()}
                  className="rounded-control border border-cf-border-input bg-cf-secondary px-3 py-1.5 text-xs text-cf-gold hover:border-cf-gold/50"
                >
                  Charger le mot de passe
                </button>
              )}

              {authError ? (
                <p className="text-xs text-red-300">{authError}</p>
              ) : null}
            </div>
          ) : null}
        </div>

        <footer className="flex flex-wrap gap-2 border-t border-cf-border-input px-5 py-4">
          <button
            type="button"
            onClick={onEdit}
            className="rounded-control border border-cf-border-input bg-cf-secondary px-4 py-2 text-sm text-cf-text hover:border-cf-gold/50 hover:text-cf-gold"
          >
            Modifier
          </button>
          <button
            type="button"
            onClick={onView}
            disabled={!project.url}
            className="rounded-control border border-cf-gold/40 bg-cf-active px-4 py-2 text-sm text-cf-gold hover:border-cf-gold disabled:cursor-not-allowed disabled:opacity-40"
          >
            Ouvrir
          </button>
        </footer>
      </aside>
    </div>
  );
}

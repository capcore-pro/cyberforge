import { useCallback, useEffect, useState } from "react";
import { API_PREFIX } from "@shared/constants";
import type { ProjectDetailResponse, ProjectRecord } from "@shared/types";
import { ProjectPreviewThumbnail } from "@/components/ProjectPreviewThumbnail";
import { apiErrorMessage } from "@/lib/api-errors";
import { apiRequest } from "@/lib/api-client";
import { PROJECT_TYPE_OPTIONS } from "@/lib/project-types";

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

function projectTypeLabel(type: string): string {
  return PROJECT_TYPE_OPTIONS.find((o) => o.id === type)?.label ?? type;
}

function formatCost(usd: number | null | undefined): string {
  if (usd === null || usd === undefined) return "—";
  if (usd < 0.01) return `< $0.01`;
  return `~$${usd.toFixed(4)}`;
}

/**
 * Page Projets — cartes avec type, date, coût et miniature visuelle.
 */
export function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ProjectDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    const response = await apiRequest<ProjectRecord[]>({
      method: "GET",
      path: `${API_PREFIX}/projects`,
    });
    setLoading(false);
    if (!response.ok) {
      setError(
        apiErrorMessage(
          response,
          "Impossible de charger les projets. Vérifiez Supabase dans backend/.env.",
        ),
      );
      return;
    }
    setProjects(Array.isArray(response.data) ? response.data : []);
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  async function toggleProject(projectId: string) {
    if (expandedId === projectId) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(projectId);
    setDetail(null);
    setDetailLoading(true);
    const response = await apiRequest<ProjectDetailResponse>({
      method: "GET",
      path: `${API_PREFIX}/projects/${projectId}`,
    });
    setDetailLoading(false);
    if (!response.ok) {
      setError(apiErrorMessage(response, "Détail du projet indisponible."));
      return;
    }
    setDetail(response.data);
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.35em] text-cyber-violet">
            // supabase_projects
          </p>
          <h1 className="text-2xl font-bold text-cyber-neon md:text-3xl">Projets</h1>
          <p className="mt-2 max-w-2xl text-sm text-cyber-muted">
            Historique cloud des générations — titre, type, date, coût estimé et
            aperçu visuel de chaque projet.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadProjects()}
          className="cyber-action-btn"
          disabled={loading}
        >
          Actualiser
        </button>
      </header>

      {loading ? (
        <section className="cyber-panel p-8 text-center">
          <p className="text-sm text-cyber-neon animate-pulse">
            Chargement des projets…
          </p>
        </section>
      ) : null}

      {error ? (
        <section className="cyber-panel border-red-400/30 p-5">
          <p className="text-xs font-bold uppercase tracking-wider text-red-400">
            Erreur Supabase
          </p>
          <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap rounded border border-red-400/20 bg-cyber-bg/80 p-3 font-mono text-[11px] leading-relaxed text-red-300">
            {error}
          </pre>
        </section>
      ) : null}

      {!loading && !error && projects.length === 0 ? (
        <section className="cyber-panel p-8 text-center">
          <p className="text-sm text-cyber-muted">
            Aucun projet enregistré. Lancez une génération depuis le Générateur.
          </p>
        </section>
      ) : null}

      {!loading && !error && projects.length > 0 ? (
        <ul className="grid gap-4 sm:grid-cols-2">
          {projects.map((project) => {
            const isOpen = expandedId === project.id;
            return (
              <li key={project.id} className="cyber-panel overflow-hidden p-0">
                <article className="flex flex-col">
                  <ProjectPreviewThumbnail
                    html={project.preview_html}
                    title={project.title}
                  />

                  <div className="flex flex-1 flex-col p-4">
                    <button
                      type="button"
                      onClick={() => void toggleProject(project.id)}
                      className="flex flex-1 flex-col text-left"
                    >
                      <h2 className="line-clamp-2 text-base font-semibold text-cyber-text">
                        {project.title}
                      </h2>

                      <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-[10px]">
                        <div>
                          <dt className="uppercase tracking-wider text-cyber-muted">
                            Type
                          </dt>
                          <dd className="mt-0.5 font-medium text-cyber-violet">
                            {projectTypeLabel(project.project_type)}
                          </dd>
                        </div>
                        <div>
                          <dt className="uppercase tracking-wider text-cyber-muted">
                            Créé le
                          </dt>
                          <dd className="mt-0.5 text-cyber-text">
                            {formatDate(project.created_at)}
                          </dd>
                        </div>
                        <div>
                          <dt className="uppercase tracking-wider text-cyber-muted">
                            Coût estimé
                          </dt>
                          <dd className="mt-0.5 font-mono text-cyber-neon">
                            {formatCost(project.latest_estimated_cost_usd)}
                          </dd>
                        </div>
                        <div>
                          <dt className="uppercase tracking-wider text-cyber-muted">
                            Générations
                          </dt>
                          <dd className="mt-0.5 text-cyber-text">
                            {project.generation_count}
                            {project.latest_model
                              ? ` · ${project.latest_model}`
                              : ""}
                          </dd>
                        </div>
                      </dl>

                      {project.summary ? (
                        <p className="mt-3 line-clamp-2 text-xs text-cyber-muted">
                          {project.summary}
                        </p>
                      ) : null}

                      <span className="mt-3 text-[10px] text-cyber-accent">
                        {isOpen ? "Masquer le détail ▲" : "Voir l'historique ▼"}
                      </span>
                    </button>
                  </div>
                </article>

                {isOpen ? (
                  <div className="border-t border-cyber-border bg-cyber-bg/40 p-4">
                    {detailLoading ? (
                      <p className="text-xs text-cyber-muted">Chargement…</p>
                    ) : detail && detail.project.id === project.id ? (
                      <div className="space-y-4">
                        <ul className="space-y-3">
                          {detail.generations.map((gen) => (
                            <li
                              key={gen.id}
                              className="rounded-lg border border-cyber-border bg-cyber-surface/80 p-3"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] text-cyber-muted">
                                <span>{formatDate(gen.created_at)}</span>
                                <span className="font-mono text-cyber-neon">
                                  {formatCost(gen.estimated_cost_usd)} ·{" "}
                                  {gen.model}
                                </span>
                              </div>
                              {gen.generation_summary ? (
                                <p className="mt-2 text-xs text-cyber-text">
                                  {gen.generation_summary}
                                </p>
                              ) : null}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <p className="text-xs text-cyber-muted">
                        Aucune génération trouvée.
                      </p>
                    )}
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

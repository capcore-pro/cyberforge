import { useCallback, useEffect, useState } from "react";
import { API_PREFIX } from "@shared/constants";
import type { ProjectDetailResponse, ProjectRecord } from "@shared/types";
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
  return (
    PROJECT_TYPE_OPTIONS.find((o) => o.id === type)?.label ?? type
  );
}

/**
 * Page Projets — historique Supabase des générations CoreMindAI.
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
    <div className="mx-auto max-w-5xl space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.35em] text-cyber-violet">
            // supabase_projects
          </p>
          <h1 className="text-2xl font-bold text-cyber-neon md:text-3xl">Projets</h1>
          <p className="mt-2 max-w-2xl text-sm text-cyber-muted">
            Historique cloud des générations réussies — chaque exécution du
            Générateur est enregistrée automatiquement.
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
          <p className="text-sm text-red-400">{error}</p>
          <p className="mt-2 text-xs text-cyber-muted">
            Exécutez la migration{" "}
            <code className="text-cyber-violet">supabase/migrations/001_projects_generations.sql</code>{" "}
            puis renseignez SUPABASE_URL et SUPABASE_SECRET_KEY dans backend/.env.
          </p>
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
        <ul className="space-y-3">
          {projects.map((project) => {
            const isOpen = expandedId === project.id;
            return (
              <li key={project.id} className="cyber-panel overflow-hidden p-0">
                <button
                  type="button"
                  onClick={() => void toggleProject(project.id)}
                  className="flex w-full items-start justify-between gap-4 p-5 text-left transition hover:bg-cyber-violet/5"
                >
                  <div className="min-w-0 flex-1">
                    <h2 className="truncate text-base font-semibold text-cyber-text">
                      {project.title}
                    </h2>
                    <p className="mt-1 line-clamp-2 text-xs text-cyber-muted">
                      {project.prompt}
                    </p>
                    <p className="mt-2 text-[10px] text-cyber-violet">
                      {projectTypeLabel(project.project_type)} ·{" "}
                      {project.generation_count} génération
                      {project.generation_count > 1 ? "s" : ""}
                      {project.latest_model
                        ? ` · ${project.latest_model}`
                        : ""}
                    </p>
                  </div>
                  <span className="shrink-0 text-[10px] text-cyber-muted">
                    {formatDate(project.updated_at)}
                    <span className="mt-1 block text-cyber-accent">
                      {isOpen ? "▲" : "▼"}
                    </span>
                  </span>
                </button>

                {isOpen ? (
                  <div className="border-t border-cyber-border bg-cyber-bg/40 p-5">
                    {detailLoading ? (
                      <p className="text-xs text-cyber-muted">Chargement…</p>
                    ) : detail && detail.project.id === project.id ? (
                      <div className="space-y-4">
                        {project.summary || detail.project.summary ? (
                          <p className="text-sm text-cyber-text">
                            {detail.project.summary ?? project.summary}
                          </p>
                        ) : null}
                        <ul className="space-y-3">
                          {detail.generations.map((gen) => (
                            <li
                              key={gen.id}
                              className="rounded-lg border border-cyber-border bg-cyber-surface/80 p-4"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] text-cyber-muted">
                                <span>
                                  {formatDate(gen.created_at)} · {gen.model} ·{" "}
                                  {gen.complexity} ({gen.complexity_score}/10)
                                </span>
                                <span>
                                  {(gen.duration_ms / 1000).toFixed(2)} s · ~$
                                  {gen.estimated_cost_usd.toFixed(4)}
                                </span>
                              </div>
                              {gen.generation_summary ? (
                                <p className="mt-2 text-xs text-cyber-text">
                                  {gen.generation_summary}
                                </p>
                              ) : null}
                              <pre className="mt-3 max-h-48 overflow-auto rounded border border-cyber-border bg-cyber-bg p-3 font-mono text-[10px] text-cyber-neon">
                                {gen.code.slice(0, 1200)}
                                {gen.code.length > 1200 ? "\n…" : ""}
                              </pre>
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

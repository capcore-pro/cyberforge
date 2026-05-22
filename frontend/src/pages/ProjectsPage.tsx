import { useCallback, useEffect, useState } from "react";
import { API_PREFIX } from "@shared/constants";
import type {
  GenerationRecord,
  ProjectDetailResponse,
  ProjectRecord,
} from "@shared/types";
import { CreateDemoModal } from "@/components/CreateDemoModal";
import { ProjectPreviewThumbnail } from "@/components/ProjectPreviewThumbnail";
import { apiErrorMessage } from "@/lib/api-errors";
import { apiRequest } from "@/lib/api-client";
import {
  createClientDemo,
  type CreateDemoResponse,
  type DemoDuration,
} from "@/lib/demos-api";
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

function filesFromGeneration(gen: GenerationRecord) {
  if (gen.files?.length) {
    return gen.files.map((f) => ({ path: f.path, content: f.content }));
  }
  if (gen.code?.trim()) {
    return [{ path: "src/App.tsx", content: gen.code }];
  }
  return [];
}

/**
 * Page Projets — cartes avec titre, date, miniature visuelle et création de démo.
 */
export function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ProjectDetailResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [demoModalOpen, setDemoModalOpen] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);
  const [demoCreated, setDemoCreated] = useState<CreateDemoResponse | null>(null);
  const [demoProject, setDemoProject] = useState<ProjectRecord | null>(null);
  const [demoGeneration, setDemoGeneration] = useState<GenerationRecord | null>(
    null,
  );
  const [demoPrepLoading, setDemoPrepLoading] = useState(false);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiRequest<ProjectRecord[]>({
        method: "GET",
        path: `${API_PREFIX}/projects`,
      });
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
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erreur inattendue lors du chargement des projets.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  async function fetchProjectDetail(
    projectId: string,
  ): Promise<ProjectDetailResponse | null> {
    const response = await apiRequest<ProjectDetailResponse>({
      method: "GET",
      path: `${API_PREFIX}/projects/${projectId}`,
    });
    if (!response.ok) return null;
    return response.data ?? null;
  }

  async function toggleProject(projectId: string) {
    if (expandedId === projectId) {
      setExpandedId(null);
      setDetail(null);
      return;
    }
    setExpandedId(projectId);
    setDetail(null);
    setDetailLoading(true);
    try {
      const data = await fetchProjectDetail(projectId);
      if (!data) {
        setError("Détail du projet indisponible.");
        return;
      }
      setDetail(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erreur inattendue lors du chargement du détail.",
      );
    } finally {
      setDetailLoading(false);
    }
  }

  function closeDemoModal() {
    setDemoModalOpen(false);
    setDemoBusy(false);
    setDemoError(null);
    setDemoCreated(null);
    setDemoProject(null);
    setDemoGeneration(null);
    setDemoPrepLoading(false);
  }

  async function openDemoModal(project: ProjectRecord) {
    setDemoProject(project);
    setDemoGeneration(null);
    setDemoError(null);
    setDemoCreated(null);
    setDemoModalOpen(true);
    setDemoPrepLoading(true);

    try {
      const data = await fetchProjectDetail(project.id);
      const latest = data?.generations?.[0] ?? null;
      if (!latest) {
        setDemoError(
          "Aucune génération enregistrée — impossible de créer une démo.",
        );
        return;
      }
      const files = filesFromGeneration(latest);
      if (!files.length) {
        setDemoError("Le livrable de ce projet est vide.");
        return;
      }
      setDemoGeneration(latest);
    } catch (err) {
      setDemoError(
        err instanceof Error
          ? err.message
          : "Impossible de charger le projet pour la démo.",
      );
    } finally {
      setDemoPrepLoading(false);
    }
  }

  async function handleCreateDemo(duration: DemoDuration) {
    if (!demoProject || !demoGeneration) return;
    const files = filesFromGeneration(demoGeneration);
    if (!files.length) {
      setDemoError("Aucun fichier à publier.");
      return;
    }

    setDemoBusy(true);
    setDemoError(null);
    const response = await createClientDemo({
      duration,
      title: demoProject.title,
      files,
      stack: demoGeneration.stack,
      summary: demoGeneration.generation_summary ?? demoProject.summary,
      project_type: demoProject.project_type,
      code: demoGeneration.code,
      generation_id: demoGeneration.id,
    });
    setDemoBusy(false);

    if (!response.ok || !response.data) {
      setDemoError(
        apiErrorMessage(
          response,
          "Impossible de créer la démo (vérifiez Supabase et Cloudflare).",
        ),
      );
      return;
    }
    setDemoCreated(response.data);
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
            Historique cloud des générations — titre, date, aperçu visuel et démo
            client en un clic.
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
        <ul className="grid gap-5 sm:grid-cols-2">
          {projects.map((project) => {
            const isOpen = expandedId === project.id;
            return (
              <li key={project.id} className="cyber-panel overflow-hidden p-0">
                <article className="flex flex-col">
                  <div className="border-b border-cyber-border p-4">
                    <h2 className="line-clamp-2 text-base font-semibold text-cyber-text">
                      {project.title}
                    </h2>
                    <p className="mt-1 text-xs text-cyber-muted">
                      Créé le{" "}
                      <time dateTime={project.created_at}>
                        {formatDate(project.created_at)}
                      </time>
                    </p>
                  </div>

                  <div className="flex justify-center border-b border-cyber-border bg-cyber-bg/50 px-4 py-3">
                    <ProjectPreviewThumbnail
                      html={project.preview_html}
                      title={project.title}
                    />
                  </div>

                  <div className="flex flex-col gap-2 p-4">
                    <button
                      type="button"
                      className="cyber-action-btn w-full text-center"
                      onClick={() => void openDemoModal(project)}
                    >
                      Créer une démo
                    </button>
                    <button
                      type="button"
                      onClick={() => void toggleProject(project.id)}
                      className="w-full rounded border border-cyber-border bg-cyber-bg/60 px-3 py-2 text-left text-[10px] text-cyber-accent transition hover:border-cyber-violet/40"
                    >
                      {isOpen ? "Masquer le détail ▲" : "Voir l'historique ▼"}
                    </button>
                    <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-[10px]">
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
                          Coût estimé
                        </dt>
                        <dd className="mt-0.5 font-mono text-cyber-neon">
                          {formatCost(project.latest_estimated_cost_usd)}
                        </dd>
                      </div>
                      <div className="col-span-2">
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
                      <p className="line-clamp-2 text-xs text-cyber-muted">
                        {project.summary}
                      </p>
                    ) : null}
                  </div>
                </article>

                {isOpen ? (
                  <div className="border-t border-cyber-border bg-cyber-bg/40 p-4">
                    {detailLoading ? (
                      <p className="text-xs text-cyber-muted">Chargement…</p>
                    ) : detail && detail.project.id === project.id ? (
                      <ul className="space-y-3">
                        {detail.generations.map((gen) => (
                          <li
                            key={gen.id}
                            className="rounded-lg border border-cyber-border bg-cyber-surface/80 p-3"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] text-cyber-muted">
                              <span>{formatDate(gen.created_at)}</span>
                              <span className="font-mono text-cyber-neon">
                                {formatCost(gen.estimated_cost_usd)} · {gen.model}
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

      <CreateDemoModal
        open={demoModalOpen}
        busy={demoBusy || demoPrepLoading}
        created={demoCreated}
        error={demoError}
        onClose={closeDemoModal}
        onCreate={(duration) => void handleCreateDemo(duration)}
      />
    </div>
  );
}

import { useCallback, useEffect, useMemo, useState } from "react";
import { ProjectDetailView } from "@/components/ProjectDetailView";
import { ProjectEditView } from "@/components/ProjectEditView";
import { useGeneratorSession } from "@/context/GeneratorSessionContext";
import type { AppPage } from "@/lib/navigation";
import {
  deleteUnifiedProject,
  filterUnifiedProjects,
  loadAllUnifiedProjects,
  openProjectUrl,
  STATUS_FILTER_OPTIONS,
  STATUS_LABELS,
  TYPE_FILTER_OPTIONS,
  TYPE_LABELS,
  type UnifiedProject,
  type UnifiedProjectStatusFilter,
  type UnifiedProjectTypeFilter,
} from "@/lib/unified-projects";

type ProjectsView = "list" | "detail" | "edit";

interface ProjectsPageProps {
  onNavigate?: (page: AppPage) => void;
  onOpenGenerator: () => void;
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
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

function truncateUrl(url: string, max = 42): string {
  if (url.length <= max) return url;
  return `${url.slice(0, max - 1)}…`;
}

function ProjectCard({
  project,
  onOpen,
  onEdit,
  onView,
  onConvert,
  onDelete,
  deleteBusy,
}: {
  project: UnifiedProject;
  onOpen: () => void;
  onEdit: () => void;
  onView: () => void;
  onConvert: () => void;
  onDelete: () => void;
  deleteBusy: boolean;
}) {
  return (
    <article className="group relative overflow-hidden rounded-card border border-cf-border-input bg-cf-card shadow-card">
      <button
        type="button"
        onClick={onOpen}
        className="flex h-full w-full flex-col p-4 text-left transition hover:bg-cf-secondary/20"
      >
        <div className="flex items-start justify-between gap-2">
          <h3 className="line-clamp-2 text-sm font-medium text-cf-text">{project.name}</h3>
          <span className="shrink-0 rounded border border-cf-gold/30 bg-cf-gold-subtle px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-cf-gold">
            {TYPE_LABELS[project.type]}
          </span>
        </div>

        <div className="mt-3 flex items-center gap-2 text-xs text-cf-muted">
          <span
            className={`inline-block h-2 w-2 shrink-0 rounded-full ${statusDotClass(project.status)}`}
            aria-hidden
          />
          <span>{STATUS_LABELS[project.status]}</span>
        </div>

        <div className="mt-3 min-h-[2.5rem] text-xs">
          {project.url ? (
            <span className="break-all text-cf-info">{truncateUrl(project.url)}</span>
          ) : (
            <span className="text-cf-tertiary">—</span>
          )}
        </div>

        <p className="mt-auto pt-4 text-[11px] text-cf-label">
          Créé le {formatDate(project.createdAt)}
        </p>
      </button>

      <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/80 p-4 opacity-0 backdrop-blur-[2px] transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onOpen();
          }}
          className="w-full max-w-[200px] rounded-control border border-cf-gold/40 bg-cf-active px-3 py-2 text-xs text-cf-gold hover:border-cf-gold"
        >
          Fiche projet
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onEdit();
          }}
          className="w-full max-w-[200px] rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-xs text-cf-text hover:border-cf-gold/50 hover:text-cf-gold"
        >
          Modifier
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onView();
          }}
          disabled={!project.url}
          className="w-full max-w-[200px] rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-xs text-cf-text hover:border-cf-gold/50 hover:text-cf-gold disabled:cursor-not-allowed disabled:opacity-40"
        >
          Voir
        </button>
        {project.status === "demo" ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onConvert();
            }}
            className="w-full max-w-[200px] rounded-control border border-cf-gold/40 bg-cf-active px-3 py-2 text-xs text-cf-gold hover:border-cf-gold"
          >
            Convertir en app réelle
          </button>
        ) : null}
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          disabled={deleteBusy}
          className="w-full max-w-[200px] rounded-control border border-red-500/40 bg-red-950/40 px-3 py-2 text-xs text-red-200 hover:bg-red-950/60 disabled:opacity-50"
        >
          Supprimer
        </button>
      </div>
    </article>
  );
}

export function ProjectsPage({ onOpenGenerator }: ProjectsPageProps) {
  const { resetSession, patch } = useGeneratorSession();

  const [projects, setProjects] = useState<UnifiedProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [view, setView] = useState<ProjectsView>("list");
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  const [typeFilter, setTypeFilter] = useState<UnifiedProjectTypeFilter>("all");
  const [statusFilter, setStatusFilter] =
    useState<UnifiedProjectStatusFilter>("all");
  const [search, setSearch] = useState("");

  const [deleteTarget, setDeleteTarget] = useState<UnifiedProject | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const selectedProject = useMemo(
    () => projects.find((p) => p.key === selectedKey) ?? null,
    [projects, selectedKey],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await loadAllUnifiedProjects();
      setProjects(items);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Impossible de charger les projets.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(
    () => filterUnifiedProjects(projects, typeFilter, statusFilter, search),
    [projects, typeFilter, statusFilter, search],
  );

  function openDetail(project: UnifiedProject) {
    setSelectedKey(project.key);
    setView("detail");
    setActionError(null);
  }

  function openEdit(project: UnifiedProject) {
    setSelectedKey(project.key);
    setView("edit");
    setActionError(null);
  }

  function backToList() {
    setView("list");
    setSelectedKey(null);
  }

  function backToDetail() {
    setView("detail");
  }

  function handleNewProject() {
    resetSession();
    onOpenGenerator();
  }

  function handleConvert(project: UnifiedProject) {
    resetSession();
    patch({
      prompt: project.prompt,
      projectName: project.name,
      projectType: project.projectType ?? "site_web",
      generationMode: "real_app",
      phase: "idle",
      error: null,
      actionError: null,
      result: null,
    });
    onOpenGenerator();
  }

  function handleView(project: UnifiedProject) {
    if (!project.url) return;
    openProjectUrl(project.url);
  }

  function upsertProject(updated: UnifiedProject) {
    setProjects((prev) => {
      const idx = prev.findIndex((p) => p.key === updated.key);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = updated;
        return next;
      }
      return [updated, ...prev];
    });
  }

  function handleDuplicate(project: UnifiedProject) {
    upsertProject(project);
    setSelectedKey(project.key);
    setView("detail");
  }

  function requestDelete(project: UnifiedProject) {
    setActionError(null);
    setDeleteTarget(project);
  }

  async function confirmDelete() {
    if (!deleteTarget) return;

    setDeleteBusy(true);
    setActionError(null);
    try {
      const result = await deleteUnifiedProject(deleteTarget);
      if (!result.ok) {
        setActionError(result.error ?? "Suppression impossible.");
        return;
      }
      setDeleteTarget(null);
      if (selectedKey === deleteTarget.key) {
        backToList();
      }
      await load();
    } finally {
      setDeleteBusy(false);
    }
  }

  if (view === "detail" && selectedProject) {
    return (
      <>
        <ProjectDetailView
          project={selectedProject}
          onBack={backToList}
          onEdit={() => openEdit(selectedProject)}
          onView={() => handleView(selectedProject)}
          onProjectUpdated={upsertProject}
          onDuplicate={handleDuplicate}
        />
        {deleteTarget ? (
          <DeleteDialog
            project={deleteTarget}
            busy={deleteBusy}
            onCancel={() => setDeleteTarget(null)}
            onConfirm={() => void confirmDelete()}
          />
        ) : null}
      </>
    );
  }

  if (view === "edit" && selectedProject) {
    return (
      <ProjectEditView
        project={selectedProject}
        onBack={backToDetail}
        onSaved={() => {
          void load().then(() => backToDetail());
        }}
      />
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="cf-page-title">Projets</h1>
          <p className="mt-1 text-sm text-cf-muted">
            Vitrines, applications, extensions et démos — tout au même endroit
          </p>
        </div>
        <button
          type="button"
          onClick={handleNewProject}
          className="rounded-control border border-cf-gold/50 bg-cf-active px-4 py-2 text-sm font-medium text-cf-gold hover:border-cf-gold hover:bg-cf-gold-subtle"
        >
          Nouveau projet
        </button>
      </header>

      <section className="space-y-4 rounded-card border border-cf-border-input bg-cf-card p-4 shadow-card">
        <div className="flex flex-wrap gap-2">
          {TYPE_FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => setTypeFilter(opt.id)}
              className={`cf-subtab ${typeFilter === opt.id ? "cf-subtab-active" : ""}`}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex flex-wrap gap-2">
            {STATUS_FILTER_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setStatusFilter(opt.id)}
                className={`cf-subtab ${statusFilter === opt.id ? "cf-subtab-active" : ""}`}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher par nom…"
            className="ml-auto min-w-[200px] flex-1 rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text placeholder:text-cf-muted focus:border-cf-gold/50 focus:outline-none sm:max-w-xs"
          />
        </div>
      </section>

      {error ? (
        <p className="rounded-card border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {actionError ? (
        <p className="rounded-card border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {actionError}
        </p>
      ) : null}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-44 animate-pulse rounded-card border border-cf-border-input bg-cf-card"
            />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-card border border-cf-border-input bg-cf-card px-6 py-12 text-center shadow-card">
          <p className="text-sm text-cf-muted">Aucun projet ne correspond aux filtres.</p>
          <button
            type="button"
            onClick={handleNewProject}
            className="mt-4 text-sm text-cf-gold hover:text-cf-gold-hover hover:underline"
          >
            Créer un projet
          </button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((project) => (
            <ProjectCard
              key={project.key}
              project={project}
              onOpen={() => openDetail(project)}
              onEdit={() => openEdit(project)}
              onView={() => handleView(project)}
              onConvert={() => handleConvert(project)}
              onDelete={() => requestDelete(project)}
              deleteBusy={deleteBusy && deleteTarget?.key === project.key}
            />
          ))}
        </div>
      )}

      {deleteTarget ? (
        <DeleteDialog
          project={deleteTarget}
          busy={deleteBusy}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={() => void confirmDelete()}
        />
      ) : null}
    </div>
  );
}

function DeleteDialog({
  project,
  busy,
  onCancel,
  onConfirm,
}: {
  project: UnifiedProject;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="delete-project-title"
    >
      <div className="w-full max-w-md rounded-card border border-red-500/30 bg-cf-card p-5 shadow-card">
        <h2 id="delete-project-title" className="text-sm font-semibold text-cf-text">
          Supprimer « {project.name} » ?
        </h2>
        <p className="mt-2 text-xs text-cf-muted">
          Cette action est irréversible. Les ressources associées (GitHub, Vercel,
          Cloudflare, Railway, Supabase) seront supprimées selon le type de projet.
        </p>
        <div className="mt-4 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            className="rounded-control border border-cf-border-input px-3 py-1.5 text-xs text-cf-muted hover:text-cf-text"
            disabled={busy}
            onClick={onCancel}
          >
            Annuler
          </button>
          <button
            type="button"
            className="rounded-control border border-red-500/50 bg-red-950/40 px-3 py-1.5 text-xs text-red-200 hover:bg-red-950/60 disabled:opacity-50"
            disabled={busy}
            onClick={onConfirm}
          >
            {busy ? "Suppression…" : "Supprimer définitivement"}
          </button>
        </div>
      </div>
    </div>
  );
}

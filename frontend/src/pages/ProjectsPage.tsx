import { useCallback, useEffect, useMemo, useState } from "react";
import { ProjectCard } from "@/components/projects/ProjectCard";
import { ProjectDetailView } from "@/components/ProjectDetailView";
import { ProjectEditView } from "@/components/ProjectEditView";
import { useGeneratorSession } from "@/context/GeneratorSessionContext";
import type { AppPage } from "@/lib/navigation";
import {
  deleteUnifiedProject,
  filterUnifiedProjects,
  loadAllUnifiedProjects,
  STATUS_FILTER_OPTIONS,
  TYPE_FILTER_OPTIONS,
  type UnifiedProject,
  type UnifiedProjectStatusFilter,
  type UnifiedProjectTypeFilter,
} from "@/lib/unified-projects";
import { formatDeletionReport } from "@/lib/deletion-report";

type ProjectsView = "list" | "detail" | "edit";

const FILTER_BTN_BASE =
  "rounded-control border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white/70 backdrop-blur-xl transition-all duration-200 hover:border-white/30";
const FILTER_BTN_ACTIVE =
  "border-[#d4a843] bg-[#d4a843]/20 text-[#d4a843] hover:border-[#d4a843]";

interface ProjectsPageProps {
  onNavigate?: (page: AppPage) => void;
  onOpenGenerator: () => void;
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
  const [deleteReport, setDeleteReport] = useState<string | null>(null);

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

  const openDetailByKey = useCallback((key: string) => {
    setSelectedKey(key);
    setView("detail");
    setActionError(null);
  }, []);

  const openEditByKey = useCallback((key: string) => {
    setSelectedKey(key);
    setView("edit");
    setActionError(null);
  }, []);

  function openDetail(project: UnifiedProject) {
    openDetailByKey(project.key);
  }

  function openEdit(project: UnifiedProject) {
    openEditByKey(project.key);
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

  const handleView = useCallback((project: UnifiedProject) => {
    const demoUrl = project.url?.trim();
    if (!demoUrl) return;
    window.open(demoUrl, "_blank", "noopener,noreferrer");
  }, []);

  const handleConvert = useCallback(
    (project: UnifiedProject) => {
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
    },
    [onOpenGenerator, patch, resetSession],
  );

  const requestDelete = useCallback((project: UnifiedProject) => {
    setActionError(null);
    setDeleteTarget(project);
  }, []);

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

  async function confirmDelete() {
    if (!deleteTarget) return;

    setDeleteBusy(true);
    setActionError(null);
    try {
      const result = await deleteUnifiedProject(deleteTarget);
      if (!result.ok && !result.report) {
        setActionError(result.error ?? "Suppression impossible.");
        return;
      }
      if (result.report?.items.length) {
        setDeleteReport(formatDeletionReport(result.report.items));
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
          className="inline-flex items-center gap-2 rounded-control border border-[#d4a843] bg-[#d4a843] px-5 py-2.5 text-sm font-semibold text-[#0a0a0a] transition-all duration-200 hover:scale-[1.02] hover:shadow-[0_0_24px_rgba(212,168,67,0.35)]"
        >
          <span aria-hidden>⚡</span>
          Nouveau projet
        </button>
      </header>

      <section className="space-y-4 rounded-card border border-white/10 bg-white/5 p-4 backdrop-blur-xl">
        <div className="flex flex-wrap gap-2">
          {TYPE_FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              onClick={() => setTypeFilter(opt.id)}
              className={`${FILTER_BTN_BASE} ${
                typeFilter === opt.id ? FILTER_BTN_ACTIVE : ""
              }`}
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
                className={`${FILTER_BTN_BASE} ${
                  statusFilter === opt.id ? FILTER_BTN_ACTIVE : ""
                }`}
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
            className="ml-auto min-w-[200px] flex-1 rounded-control border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder:text-white/30 backdrop-blur-xl focus:border-[#d4a843] focus:outline-none sm:max-w-xs"
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

      {deleteReport ? (
        <div
          className="rounded-card border border-cf-border-input bg-cf-card px-4 py-3 shadow-card"
          role="status"
        >
          <p className="mb-2 text-sm font-medium text-cf-text">Rapport de suppression</p>
          <pre className="whitespace-pre-wrap text-xs leading-relaxed text-cf-muted">
            {deleteReport}
          </pre>
          <button
            type="button"
            className="mt-3 text-xs text-cf-gold hover:underline"
            onClick={() => setDeleteReport(null)}
          >
            Fermer
          </button>
        </div>
      ) : null}

      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="min-h-[380px] animate-pulse rounded-card border border-white/10 bg-white/5 backdrop-blur-xl"
            />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="flex flex-col items-center rounded-card border border-white/10 bg-white/5 px-6 py-16 text-center backdrop-blur-xl">
          <span
            className="mb-6 text-6xl animate-pulse"
            role="img"
            aria-label="Dossier vide"
          >
            📁
          </span>
          <h2 className="text-xl font-semibold text-white">
            Aucun projet pour le moment
          </h2>
          <p className="mt-2 max-w-sm text-sm text-white/50">
            Créez votre premier projet en quelques minutes
          </p>
          <button
            type="button"
            onClick={handleNewProject}
            className="mt-8 inline-flex items-center gap-2 rounded-control border border-[#d4a843] bg-[#d4a843] px-8 py-3.5 text-base font-semibold text-[#0a0a0a] transition-all duration-200 hover:scale-[1.02] hover:shadow-[0_0_32px_rgba(212,168,67,0.4)]"
          >
            <span aria-hidden>⚡</span>
            Créer mon premier projet
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-card border border-white/10 bg-white/5 px-6 py-12 text-center backdrop-blur-xl">
          <p className="text-sm text-white/50">
            Aucun projet ne correspond aux filtres.
          </p>
          <button
            type="button"
            onClick={() => {
              setTypeFilter("all");
              setStatusFilter("all");
              setSearch("");
            }}
            className="mt-4 text-sm text-[#d4a843] hover:underline"
          >
            Réinitialiser les filtres
          </button>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((project) => (
            <ProjectCard
              key={project.key}
              project={project}
              onOpenDetail={openDetailByKey}
              onEditDetail={openEditByKey}
              onViewProject={handleView}
              onConvertProject={handleConvert}
              onDeleteProject={requestDelete}
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
          Cette action est irréversible et effacera le site déployé, le repo GitHub et
          toutes les données associées.
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

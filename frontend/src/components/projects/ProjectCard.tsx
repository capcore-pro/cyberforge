import { memo } from "react";
import {
  STATUS_LABELS,
  TYPE_LABELS,
  type UnifiedProject,
} from "@/lib/unified-projects";

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

export interface ProjectCardProps {
  project: UnifiedProject;
  onOpenDetail: (key: string) => void;
  onEditDetail: (key: string) => void;
  onViewProject: (project: UnifiedProject) => void;
  onConvertProject: (project: UnifiedProject) => void;
  onDeleteProject: (project: UnifiedProject) => void;
  deleteBusy: boolean;
}

export const ProjectCard = memo(function ProjectCard({
  project,
  onOpenDetail,
  onEditDetail,
  onViewProject,
  onConvertProject,
  onDeleteProject,
  deleteBusy,
}: ProjectCardProps) {
  return (
    <article className="group relative overflow-hidden rounded-card border border-cf-border-input bg-cf-card shadow-card">
      <button
        type="button"
        onClick={() => onOpenDetail(project.key)}
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
            onOpenDetail(project.key);
          }}
          className="w-full max-w-[200px] rounded-control border border-cf-gold/40 bg-cf-active px-3 py-2 text-xs text-cf-gold hover:border-cf-gold"
        >
          Fiche projet
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onEditDetail(project.key);
          }}
          className="w-full max-w-[200px] rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-xs text-cf-text hover:border-cf-gold/50 hover:text-cf-gold"
        >
          Modifier
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onViewProject(project);
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
              onConvertProject(project);
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
            onDeleteProject(project);
          }}
          disabled={deleteBusy}
          className="w-full max-w-[200px] rounded-control border border-red-500/40 bg-red-950/40 px-3 py-2 text-xs text-red-200 hover:bg-red-950/60 disabled:opacity-50"
        >
          Supprimer
        </button>
      </div>
    </article>
  );
});

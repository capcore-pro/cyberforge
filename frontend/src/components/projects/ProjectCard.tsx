import { memo, type ReactNode } from "react";
import {
  CalendarDays,
  Globe,
  LayoutDashboard,
  Puzzle,
  ShoppingBag,
} from "lucide-react";
import { ProjectPreviewThumbnail } from "@/components/ProjectPreviewThumbnail";
import {
  STATUS_LABELS,
  TYPE_LABELS,
  type UnifiedProject,
  type UnifiedProjectType,
} from "@/lib/unified-projects";

function formatRelativeDate(iso: string): string {
  try {
    const date = new Date(iso);
    const diffMs = Date.now() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 60) return "à l'instant";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `il y a ${diffMin} min`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `il y a ${diffHours} h`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return "il y a 1 jour";
    if (diffDays < 30) return `il y a ${diffDays} jours`;
    const diffMonths = Math.floor(diffDays / 30);
    if (diffMonths === 1) return "il y a 1 mois";
    if (diffMonths < 12) return `il y a ${diffMonths} mois`;
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(date);
  } catch {
    return iso;
  }
}

function statusBadgeClass(status: UnifiedProject["status"]): string {
  if (status === "online") {
    return "border-green-400/35 bg-green-500/15 text-green-300";
  }
  if (status === "demo") {
    return "border-blue-400/35 bg-blue-500/15 text-blue-300";
  }
  return "border-white/20 bg-white/10 text-white/55";
}

function typeBadgeClass(type: UnifiedProjectType): string {
  switch (type) {
    case "vitrine":
      return "border-amber-400/35 bg-amber-500/15 text-amber-200";
    case "app_web":
      return "border-blue-400/35 bg-blue-500/15 text-blue-200";
    case "ecommerce":
      return "border-emerald-400/35 bg-emerald-500/15 text-emerald-200";
    case "reservation":
      return "border-violet-400/35 bg-violet-500/15 text-violet-200";
    case "extension":
      return "border-cyan-400/35 bg-cyan-500/15 text-cyan-200";
    default:
      return "border-white/20 bg-white/10 text-white/70";
  }
}

function projectTypeIcon(type: UnifiedProjectType): ReactNode {
  const className = "h-10 w-10 text-white/35";
  switch (type) {
    case "app_web":
      return <LayoutDashboard className={className} aria-hidden />;
    case "ecommerce":
      return <ShoppingBag className={className} aria-hidden />;
    case "reservation":
      return <CalendarDays className={className} aria-hidden />;
    case "extension":
      return <Puzzle className={className} aria-hidden />;
    default:
      return <Globe className={className} aria-hidden />;
  }
}

function ProjectCardPreview({ project }: { project: UnifiedProject }) {
  const demoUrl = project.url?.trim();

  if (demoUrl) {
    return (
      <div className="h-[180px] w-full shrink-0 overflow-hidden" aria-hidden>
        <ProjectPreviewThumbnail
          previewUrl={demoUrl}
          title={project.name}
          height={180}
          fill
          className="h-full rounded-none border-0"
        />
      </div>
    );
  }

  return (
    <div
      className="flex h-[180px] w-full shrink-0 flex-col items-center justify-center gap-2 border-b border-white/10 bg-white/5"
      aria-hidden
    >
      {projectTypeIcon(project.type)}
      <span className="text-[10px] uppercase tracking-wider text-white/40">
        {TYPE_LABELS[project.type]}
      </span>
    </div>
  );
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
  const demoUrl = project.url?.trim();

  return (
    <article
      className="group flex min-h-[380px] flex-col overflow-hidden rounded-card border border-white/10 bg-white/5 shadow-none backdrop-blur-xl transition-all duration-200 hover:scale-[1.01] hover:border-[#d4a843]/50 hover:shadow-[0_0_24px_rgba(212,168,67,0.1)]"
    >
      <button
        type="button"
        onClick={() => onOpenDetail(project.key)}
        className="flex w-full flex-1 flex-col text-left transition-colors duration-200 hover:bg-white/[0.03]"
      >
        <ProjectCardPreview project={project} />

        <div className="flex flex-1 flex-col p-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h3 className="line-clamp-2 min-w-0 flex-1 text-sm font-semibold text-white">
              {project.name}
            </h3>
            <span
              className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${typeBadgeClass(project.type)}`}
            >
              {TYPE_LABELS[project.type]}
            </span>
          </div>

          <div className="mt-3">
            <span
              className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-medium ${statusBadgeClass(project.status)}`}
            >
              {STATUS_LABELS[project.status]}
            </span>
          </div>

          <p className="mt-3 text-[11px] text-white/45">
            {formatRelativeDate(project.createdAt)}
          </p>
        </div>
      </button>

      <div className="flex flex-wrap gap-2 border-t border-white/10 p-3">
        <button
          type="button"
          onClick={() => onViewProject(project)}
          disabled={!demoUrl}
          title={demoUrl || "Aucune URL de démo"}
          className="flex-1 rounded-control border border-[#d4a843]/40 bg-[#d4a843]/10 px-2 py-2 text-xs font-medium text-[#d4a843] transition-all duration-200 hover:bg-[#d4a843]/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Voir →
        </button>
        <button
          type="button"
          onClick={() => onEditDetail(project.key)}
          className="flex-1 rounded-control border border-white/15 bg-white/5 px-2 py-2 text-xs text-white/80 transition-all duration-200 hover:border-white/30 hover:text-white"
        >
          Modifier
        </button>
        <button
          type="button"
          onClick={() => onDeleteProject(project)}
          disabled={deleteBusy}
          className="rounded-control border border-red-500/30 bg-red-950/30 px-2 py-2 text-xs text-red-300 transition-all duration-200 hover:bg-red-950/50 disabled:opacity-50"
        >
          Supprimer
        </button>
      </div>

      {project.status === "demo" ? (
        <div className="border-t border-white/10 px-3 pb-3">
          <button
            type="button"
            onClick={() => onConvertProject(project)}
            className="w-full rounded-control border border-white/15 px-2 py-1.5 text-[11px] text-white/60 transition hover:border-[#d4a843]/40 hover:text-[#d4a843]"
          >
            Convertir en app réelle
          </button>
        </div>
      ) : null}
    </article>
  );
});

import { formatEur } from "@/lib/generator-estimation";
import {
  prepareInternalPreviewSrcDoc,
  withCyberforgeInternalPreview,
} from "@/lib/cyberforge-preview";

const PREVIEW_IFRAME_SANDBOX =
  "allow-scripts allow-same-origin allow-forms allow-modals";

function formatDuration(ms: number): string {
  const totalSec = Math.max(0, Math.floor(ms / 1000));
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  if (min > 0) return `${min} min ${sec} s`;
  return `${sec} s`;
}

interface GeneratorResultCardProps {
  projectName: string;
  kindTitle: string;
  sectorLabel: string;
  demoUrl: string | null;
  previewHtml: string | null;
  costEur: number | null;
  durationMs: number;
  showProjectsLink: boolean;
  onOpenDemo: () => void;
  onOpenProjects?: () => void;
  onNewGeneration: () => void;
}

export function GeneratorResultCard({
  projectName,
  kindTitle,
  sectorLabel,
  demoUrl,
  previewHtml,
  costEur,
  durationMs,
  showProjectsLink,
  onOpenDemo,
  onOpenProjects,
  onNewGeneration,
}: GeneratorResultCardProps) {
  return (
    <div className="rounded-card border border-white/10 bg-white/5 p-6 backdrop-blur-xl">
      <div className="flex items-start gap-3">
        <span className="text-2xl" aria-hidden>
          ✅
        </span>
        <div>
          <h3 className="text-lg font-semibold text-white">
            Projet généré avec succès !
          </h3>
          <p className="mt-1 text-sm text-white/60">
            <span className="font-medium text-white">{projectName}</span>
            {" · "}
            {kindTitle}
            {" · "}
            {sectorLabel}
          </p>
        </div>
      </div>

      {demoUrl ? (
        <p className="mt-4 text-sm">
          <span className="text-white/50">URL démo : </span>
          <a
            href={demoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="break-all font-medium text-[#d4a843] underline-offset-2 hover:underline"
          >
            {demoUrl}
          </a>
        </p>
      ) : null}

      {demoUrl || previewHtml ? (
        <div className="mt-5 overflow-hidden rounded-card border border-white/10 bg-black/40">
          <div
            className="relative mx-auto"
            style={{ width: 400, height: 225 }}
          >
            {demoUrl ? (
              <iframe
                title="Aperçu du projet généré"
                src={withCyberforgeInternalPreview(demoUrl)}
                className="h-full w-full border-0"
                sandbox={PREVIEW_IFRAME_SANDBOX}
              />
            ) : (
              <iframe
                title="Aperçu du projet généré"
                srcDoc={prepareInternalPreviewSrcDoc(previewHtml!)}
                sandbox={PREVIEW_IFRAME_SANDBOX}
                className="absolute left-0 top-0 origin-top-left border-0"
                style={{
                  width: 800,
                  height: 450,
                  transform: "scale(0.5)",
                }}
              />
            )}
          </div>
        </div>
      ) : null}

      <div className="mt-5 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onOpenDemo}
          className="inline-flex items-center gap-2 rounded-control border border-[#d4a843] bg-[#d4a843] px-5 py-2.5 text-sm font-semibold text-[#0a0a0a] transition-all duration-200 hover:scale-[1.02] hover:shadow-[0_0_24px_rgba(212,168,67,0.35)]"
        >
          Voir la démo →
        </button>
        {showProjectsLink && onOpenProjects ? (
          <button
            type="button"
            onClick={onOpenProjects}
            className="inline-flex items-center gap-2 rounded-control border border-white/20 bg-white/5 px-5 py-2.5 text-sm font-medium text-white transition-all duration-200 hover:border-[#d4a843]/50 hover:text-[#d4a843]"
          >
            Voir dans Projets →
          </button>
        ) : null}
        <button
          type="button"
          onClick={onNewGeneration}
          className="inline-flex items-center gap-2 rounded-control border border-white/15 px-5 py-2.5 text-sm text-white/70 transition-all duration-200 hover:border-white/30 hover:text-white"
        >
          Nouvelle génération
        </button>
      </div>

      <div className="mt-5 flex flex-wrap gap-6 border-t border-white/10 pt-4 text-xs text-white/50">
        {costEur != null ? (
          <p>
            Coût API :{" "}
            <span className="font-medium text-white">
              ~{formatEur(costEur)}
            </span>
          </p>
        ) : null}
        <p>
          Temps total :{" "}
          <span className="font-medium text-white">
            {formatDuration(durationMs)}
          </span>
        </p>
      </div>
    </div>
  );
}

import type { ErpDockerStatus, ErpProjectRecord } from "@/lib/erp-builder-api";
import { Button } from "@/components/ui";

export function ErpStatusPanel({
  project,
  docker,
  polling,
  onRefresh,
  onOpen,
  onStop,
  onRestart,
}: {
  project: ErpProjectRecord | null;
  docker: ErpDockerStatus | null;
  polling: boolean;
  onRefresh: () => void;
  onOpen: (url: string) => void;
  onStop: () => void;
  onRestart: () => void;
}) {
  if (!project) {
    return (
      <aside className="w-[320px] shrink-0 border-l border-white/10 bg-[#0f1117]/60 p-4">
        <p className="text-sm text-cf-muted">Sélectionnez un projet pour voir le statut.</p>
      </aside>
    );
  }

  const url = project.url ?? docker?.url;
  const logs = docker?.logs_tail ?? [];

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // ignore
    }
  }

  return (
    <aside className="w-[320px] shrink-0 border-l border-white/10 bg-[#0f1117]/60 p-4">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
          Accès ERP
        </p>
        {polling ? <span className="text-[10px] text-cyan-300">Live</span> : null}
      </div>

      {url ? (
        <button
          type="button"
          onClick={() => onOpen(url)}
          className="mb-4 block w-full break-all rounded-card border border-cyan-500/30 bg-cyan-500/10 p-3 text-left text-sm text-cyan-300 hover:bg-cyan-500/15"
        >
          {url}
        </button>
      ) : (
        <p className="mb-4 text-sm text-cf-muted">URL disponible après installation.</p>
      )}

      {project.admin_email ? (
        <div className="mb-3 rounded-card border border-white/10 bg-white/5 p-3 text-xs">
          <div className="flex justify-between gap-2">
            <span className="text-cf-muted">Login</span>
            <button type="button" onClick={() => void copy(project.admin_email ?? "")} className="text-white">
              {project.admin_email}
            </button>
          </div>
          {project.admin_password ? (
            <div className="mt-2 flex justify-between gap-2">
              <span className="text-cf-muted">Password</span>
              <button
                type="button"
                onClick={() => void copy(project.admin_password ?? "")}
                className="text-white"
              >
                Copier
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      {docker?.stats.cpu_percent || docker?.stats.mem_usage ? (
        <div className="mb-4 rounded-card border border-white/10 bg-white/5 p-3 text-xs">
          <p className="mb-2 font-semibold text-cf-muted">Ressources Docker</p>
          {docker.stats.cpu_percent ? (
            <p className="text-white">CPU : {docker.stats.cpu_percent}</p>
          ) : null}
          {docker.stats.mem_usage ? (
            <p className="text-white">RAM : {docker.stats.mem_usage}</p>
          ) : null}
        </div>
      ) : null}

      <div className="mb-4 flex flex-wrap gap-2">
        <Button
          variant="ghost"
          size="sm"
          icon="ti ti-refresh"
          onClick={onRefresh}
        >
          Actualiser
        </Button>
        <Button
          variant="success"
          size="sm"
          icon="ti ti-external-link"
          disabled={!url}
          onClick={() => url && onOpen(url)}
        >
          Ouvrir
        </Button>
        <Button
          variant="ghost"
          size="sm"
          icon="ti ti-player-stop"
          disabled={project.status !== "running"}
          onClick={onStop}
        >
          Arrêter
        </Button>
        <Button
          variant="ghost"
          size="sm"
          icon="ti ti-reload"
          onClick={onRestart}
        >
          Redémarrer
        </Button>
      </div>

      {docker?.error ? (
        <p className="mb-3 rounded border border-red-500/30 bg-red-950/30 p-2 text-xs text-red-200">
          {docker.error}
        </p>
      ) : null}

      {logs.length > 0 ? (
        <div className="rounded-card border border-white/10 bg-black/30 p-3">
          <p className="mb-2 text-[10px] font-semibold uppercase text-cf-muted">Logs récents</p>
          <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap font-mono text-[10px] text-cf-muted">
            {logs.slice(-20).join("\n")}
          </pre>
        </div>
      ) : project.install_logs ? (
        <div className="rounded-card border border-white/10 bg-black/30 p-3">
          <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap font-mono text-[10px] text-cf-muted">
            {project.install_logs.slice(-2000)}
          </pre>
        </div>
      ) : null}
    </aside>
  );
}

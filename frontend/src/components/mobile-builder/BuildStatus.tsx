import type { MobileAppRecord } from "@/lib/mobile-builder-api";
import { getMobileApkDownloadUrl } from "@/lib/mobile-builder-api";
import { Button } from "@/components/ui";

const BUILD_ESTIMATE_MS = 10 * 60 * 1000;

export function BuildStatus({
  app,
  progress,
  polling,
  onRefresh,
}: {
  app: MobileAppRecord | null;
  progress: number;
  polling: boolean;
  onRefresh: () => void;
}) {
  if (!app) {
    return (
      <aside className="w-[320px] shrink-0 border-l border-white/10 bg-[#0f1117]/60 p-4">
        <p className="text-sm text-cf-muted">
          Sélectionnez ou créez une app pour voir le statut build.
        </p>
      </aside>
    );
  }

  const isBuilding = app.status === "building";
  const isReady = app.status === "ready";
  const isFailed = app.status === "failed";
  const downloadUrl = getMobileApkDownloadUrl(app.id);

  return (
    <aside className="w-[320px] shrink-0 border-l border-white/10 bg-[#0f1117]/60 p-4">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
          Build EAS
        </p>
        {polling ? (
          <span className="text-[10px] text-cyan-300">Polling 30s</span>
        ) : null}
      </div>

      <div className="mb-4 rounded-card border border-white/10 bg-white/5 p-3">
        <p className="text-sm font-semibold text-white">{app.name}</p>
        <p className="mt-1 text-xs text-cf-muted">Statut : {app.status}</p>
        {app.eas_build_id ? (
          <p className="mt-1 truncate font-mono text-[10px] text-cf-muted">
            {app.eas_build_id}
          </p>
        ) : null}
      </div>

      {isBuilding ? (
        <div className="mb-4">
          <div className="mb-1 flex justify-between text-xs text-cf-muted">
            <span>Progression estimée</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-violet-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-cf-muted">
            Build cloud ~10 min. Actualisation automatique toutes les 30s.
          </p>
        </div>
      ) : null}

      {isReady ? (
        <Button
          variant="success"
          icon="ti ti-download"
          className="mb-4 w-full"
          onClick={() => {
            if (app.apk_url) {
              void window.cyberforge?.openExternal?.(app.apk_url);
            } else {
              window.open(downloadUrl, "_blank");
            }
          }}
        >
          Télécharger APK
        </Button>
      ) : null}

      {isFailed ? (
        <p className="mb-4 rounded-card border border-red-500/30 bg-red-950/30 px-3 py-2 text-xs text-red-200">
          Build échoué. Consultez les logs ci-dessous.
        </p>
      ) : null}

      <Button
        variant="ghost"
        size="sm"
        icon="ti ti-refresh"
        className="mb-4 w-full"
        onClick={onRefresh}
      >
        Actualiser statut
      </Button>

      {app.build_logs ? (
        <div className="rounded-card border border-white/10 bg-black/30 p-3">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-cf-muted">
            Logs build
          </p>
          <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap font-mono text-[10px] text-cf-muted">
            {app.build_logs}
          </pre>
        </div>
      ) : null}
    </aside>
  );
}

export function estimateBuildProgress(startedAt: number | null): number {
  if (!startedAt) return 5;
  const elapsed = Date.now() - startedAt;
  return Math.min(95, Math.round((elapsed / BUILD_ESTIMATE_MS) * 100));
}

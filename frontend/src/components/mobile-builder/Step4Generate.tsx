import { Button } from "@/components/ui";

export interface GenerateLogEntry {
  type: "start" | "done" | "error";
  message: string;
  timestamp: number;
}

export function Step4Generate({
  appId,
  generated,
  generating,
  logs,
  files,
  onGenerate,
  onBuild,
  buildLoading,
  disabled,
}: {
  appId: string | null;
  generated: boolean;
  generating: boolean;
  logs: GenerateLogEntry[];
  files: string[];
  onGenerate: () => void;
  onBuild: () => void;
  buildLoading: boolean;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="primary"
          icon="ti ti-sparkles"
          loading={generating}
          disabled={!appId || disabled || generating}
          onClick={onGenerate}
        >
          Générer avec MobileAI
        </Button>
        {generated ? (
          <Button
            variant="success"
            icon="ti ti-device-mobile"
            loading={buildLoading}
            disabled={!appId || buildLoading}
            onClick={onBuild}
          >
            Lancer le Build APK
          </Button>
        ) : null}
      </div>

      {logs.length > 0 ? (
        <div className="rounded-card border border-white/10 bg-[#0f1117]/60 p-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-cf-muted">
            Progression SSE
          </p>
          <ul className="space-y-2">
            {logs.map((log, i) => (
              <li key={`${log.timestamp}-${i}`} className="flex items-start gap-2 text-sm">
                <span
                  className={[
                    "mt-0.5 h-2 w-2 shrink-0 rounded-full",
                    log.type === "error"
                      ? "bg-red-400"
                      : log.type === "done"
                        ? "bg-emerald-400"
                        : "bg-cyan-400 animate-pulse",
                  ].join(" ")}
                />
                <span
                  className={
                    log.type === "error" ? "text-red-200" : "text-cf-muted"
                  }
                >
                  {log.message}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {files.length > 0 ? (
        <div className="rounded-card border border-cyan-500/20 bg-cyan-500/5 p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-cyan-300">
            Fichiers générés ({files.length})
          </p>
          <ul className="max-h-48 overflow-y-auto font-mono text-xs text-cf-muted">
            {files.map((f) => (
              <li key={f} className="border-b border-white/5 py-1 last:border-0">
                {f}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

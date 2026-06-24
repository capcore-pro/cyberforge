import { useCallback, useEffect, useState } from "react";
import {
  GLASS_CARD,
  GLASS_SECTION,
  GHOST_BTN,
  GOLD_BTN,
  openExternalUrl,
} from "@/components/settings/settings-theme";
import { useBackendHealth } from "@/context/BackendHealthContext";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  clearSystemCache,
  fetchSystemInfo,
  fetchSystemLogs,
  systemLogsExportUrl,
} from "@/lib/settings-api";
import { APP_VERSION } from "@shared/constants";

export function SystemSettingsPanel() {
  const { status, health, refresh } = useBackendHealth();
  const desktopApi = window.electronAPI ?? window.cyberforge;
  const [appVersion, setAppVersion] = useState("—");
  const [appName, setAppName] = useState("CyberForge");
  const [backendPort, setBackendPort] = useState(8002);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [busy, setBusy] = useState<"cache" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updateStatus, setUpdateStatus] = useState<{
    status: string;
    version?: string;
    message?: string;
  } | null>(null);
  const [downloadProgress, setDownloadProgress] = useState<number | null>(null);
  const [backendStatus, setBackendStatus] = useState<{
    status: string;
    pid?: number;
  }>({ status: "unknown" });
  const [isRestarting, setIsRestarting] = useState(false);
  const [backendLogs, setBackendLogs] = useState<string[]>([]);
  const isDesktopApp = Boolean(window.electronAPI || window.cyberforge);

  const loadInfo = useCallback(async () => {
    const [infoRes, logsRes] = await Promise.all([
      fetchSystemInfo(),
      fetchSystemLogs(5),
    ]);
    if (infoRes.ok && infoRes.data) {
      setAppName(infoRes.data.app_name);
    }
    if (logsRes.ok && logsRes.data) {
      setLogLines(logsRes.data.lines);
      setBackendPort(logsRes.data.backend_port);
    }
  }, []);

  useEffect(() => {
    void loadInfo();
  }, [loadInfo]);

  useEffect(() => {
    const api = window.electronAPI ?? window.cyberforge;
    if (api?.getVersion) {
      void Promise.resolve(api.getVersion()).then((version) => {
        if (typeof version === "string" && version) {
          setAppVersion(version);
        }
      });
      return;
    }
    setAppVersion(APP_VERSION);
  }, []);

  useEffect(() => {
    const api = window.electronAPI ?? window.cyberforge;
    if (!api) return;
    const unsubUpdate = api.onUpdateStatus?.(setUpdateStatus);
    const unsubProgress = api.onDownloadProgress?.((d) =>
      setDownloadProgress(d.percent),
    );
    const unsubBackend = api.onBackendStatus?.((data) =>
      setBackendStatus({ status: data.status, pid: data.pid }),
    );
    return () => {
      unsubUpdate?.();
      unsubProgress?.();
      unsubBackend?.();
    };
  }, []);

  useEffect(() => {
    const api = window.electronAPI ?? window.cyberforge;
    const unsub = api?.onBackendLog?.((log) => {
      setBackendLogs((prev) => [...prev.slice(-10), log]);
    });
    return () => unsub?.();
  }, []);

  const backendOnline = status === "online";

  async function handleClearCache() {
    setBusy("cache");
    setError(null);
    setMessage(null);
    const res = await clearSystemCache();
    setBusy(null);
    if (!res.ok || !res.data) {
      setError(apiErrorMessage(res, "Impossible de vider le cache."));
      return;
    }
    setMessage(res.data.message);
    void refresh();
    void loadInfo();
  }

  async function handleCheckUpdate() {
    setUpdateStatus({ status: "checking" });
    await desktopApi?.checkForUpdates?.();
  }

  async function handleRestartBackend() {
    setIsRestarting(true);
    await desktopApi?.restartBackend?.();
    setTimeout(() => setIsRestarting(false), 4000);
    void refresh();
  }

  function handleExportLogs() {
    openExternalUrl(systemLogsExportUrl());
  }

  return (
    <div className="h-full min-h-0 space-y-6 overflow-y-auto">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className={GLASS_CARD}>
          <p className="text-xs font-semibold uppercase tracking-wide text-white/45">
            Statut backend
          </p>
          <div className="mt-3 flex items-center gap-2">
            <span
              className={`inline-block h-3 w-3 rounded-full ${
                backendOnline
                  ? "animate-pulse bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.6)]"
                  : "bg-red-500"
              }`}
            />
            <span
              className={`text-sm font-medium ${
                backendOnline ? "text-emerald-300" : "text-red-300"
              }`}
            >
              {backendOnline ? "En ligne" : "Hors ligne"}
            </span>
          </div>
        </div>

        <div className={GLASS_CARD}>
          <p className="text-xs font-semibold uppercase tracking-wide text-white/45">
            Version CyberForge
          </p>
          <p className="mt-3 text-lg font-semibold text-white">v{appVersion}</p>
        </div>

        <div className={GLASS_CARD}>
          <p className="text-xs font-semibold uppercase tracking-wide text-white/45">
            Port backend
          </p>
          <p className="mt-3 font-mono text-lg font-semibold text-[#d4a843]">
            {backendPort}
          </p>
        </div>
      </div>

      <div className={GLASS_SECTION}>
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/45">
          Logs récents
        </h3>
        {logLines.length ? (
          <pre className="max-h-48 overflow-auto rounded-control border border-white/10 bg-black/40 p-3 font-mono text-[11px] leading-relaxed text-white/70">
            {logLines.join("\n")}
          </pre>
        ) : (
          <p className="text-sm text-white/45">
            Aucun log capturé pour l&apos;instant.
          </p>
        )}
      </div>

      {isDesktopApp ? (
        <div className={GLASS_SECTION}>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/45">
            Mise à jour CyberForge
          </h3>

          <div className="mb-3 text-sm text-white/55">
            {!updateStatus && "Vérification automatique au lancement."}
            {updateStatus?.status === "checking" && "Vérification en cours..."}
            {updateStatus?.status === "up-to-date" &&
              `✓ CyberForge est à jour (v${updateStatus.version})`}
            {updateStatus?.status === "downloading" && (
              <span>
                Téléchargement v{updateStatus.version}...
                {downloadProgress !== null && ` ${downloadProgress}%`}
              </span>
            )}
            {updateStatus?.status === "ready" &&
              `✓ v${updateStatus.version} prête — redémarre pour installer`}
            {updateStatus?.status === "error" && `Erreur : ${updateStatus.message}`}
          </div>

          {downloadProgress !== null && updateStatus?.status === "downloading" && (
            <div className="mb-3 h-1.5 w-full rounded-full bg-white/10">
              <div
                className="h-1.5 rounded-full bg-amber-400 transition-all"
                style={{ width: `${downloadProgress}%` }}
              />
            </div>
          )}

          <div className="flex gap-2">
            {updateStatus?.status !== "ready" && (
              <button
                type="button"
                onClick={() => void handleCheckUpdate()}
                disabled={
                  updateStatus?.status === "checking" ||
                  updateStatus?.status === "downloading"
                }
                className={GOLD_BTN}
              >
                {updateStatus?.status === "checking"
                  ? "Vérification..."
                  : "Vérifier les mises à jour"}
              </button>
            )}
            {updateStatus?.status === "ready" && (
              <button
                type="button"
                onClick={() => desktopApi?.restartAndUpdate?.()}
                className={GOLD_BTN}
              >
                Redémarrer et installer
              </button>
            )}
          </div>

          <a
            href="https://github.com/capcore-pro/cyberforge/releases/latest"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-gray-400 hover:text-gray-300 text-xs mt-3 transition-colors"
          >
            <span>⬇️</span>
            <span>Télécharger manuellement la dernière version</span>
            <span>→</span>
          </a>
        </div>
      ) : null}

      {isDesktopApp ? (
        <div className={GLASS_SECTION}>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-white/45">
            Processus backend
          </h3>
          <div className="mb-3 flex items-center gap-2 text-sm">
            <span
              className={`h-2 w-2 rounded-full ${
                backendStatus.status === "online"
                  ? "bg-green-400"
                  : backendStatus.status === "starting"
                    ? "animate-pulse bg-amber-400"
                    : "bg-red-400"
              }`}
            />
            <span className="text-white/70">
              {backendStatus.status === "online" &&
                `En ligne${backendStatus.pid ? ` · PID ${backendStatus.pid}` : ""}`}
              {backendStatus.status === "starting" && "Démarrage..."}
              {backendStatus.status === "offline" && "Hors ligne"}
              {backendStatus.status === "error" && "Erreur"}
              {backendStatus.status === "unknown" && "Statut inconnu"}
            </span>
          </div>
          <button
            type="button"
            onClick={() => void handleRestartBackend()}
            disabled={isRestarting || backendStatus.status === "starting"}
            className={GOLD_BTN}
          >
            {isRestarting ? "Redémarrage..." : "Redémarrer le backend"}
          </button>
          {backendLogs.length > 0 && (
            <div
              style={{
                marginTop: 8,
                fontFamily: "monospace",
                fontSize: 11,
                color: "rgba(255,255,255,0.4)",
                maxHeight: 120,
                overflow: "auto",
              }}
            >
              {backendLogs.map((l, i) => (
                <div key={i}>{l}</div>
              ))}
            </div>
          )}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={busy !== null}
          onClick={() => void handleClearCache()}
          className={GHOST_BTN}
        >
          {busy === "cache" ? "Nettoyage…" : "Vider le cache"}
        </button>
        <button type="button" onClick={handleExportLogs} className={GHOST_BTN}>
          Exporter les logs
        </button>
      </div>

      {error ? (
        <p className="rounded-control border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}
      {message ? (
        <p className="rounded-control border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/60">
          {message}
        </p>
      ) : null}
    </div>
  );
}

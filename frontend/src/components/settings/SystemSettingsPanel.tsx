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
  restartBackend,
  systemLogsExportUrl,
} from "@/lib/settings-api";
import { APP_VERSION } from "@shared/constants";

export function SystemSettingsPanel() {
  const { status, health, refresh } = useBackendHealth();
  const [version, setVersion] = useState(APP_VERSION);
  const [appName, setAppName] = useState("CyberForge");
  const [backendPort, setBackendPort] = useState(8002);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [busy, setBusy] = useState<"cache" | "restart" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updateReady, setUpdateReady] = useState(false);
  const isDesktopApp = Boolean(window.electronAPI?.restartAndUpdate);

  const loadInfo = useCallback(async () => {
    const [infoRes, logsRes] = await Promise.all([
      fetchSystemInfo(),
      fetchSystemLogs(5),
    ]);
    if (infoRes.ok && infoRes.data) {
      setVersion(infoRes.data.version);
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
    const unsubscribe = window.electronAPI?.onUpdateReady?.(() => {
      setUpdateReady(true);
    });
    return () => unsubscribe?.();
  }, []);

  const backendOnline = status === "online";
  const displayVersion = health?.version ?? version;

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

  async function handleRestart() {
    setBusy("restart");
    setError(null);
    setMessage(null);
    const res = await restartBackend();
    setBusy(null);
    if (!res.ok || !res.data) {
      setError(apiErrorMessage(res, "Action impossible."));
      return;
    }
    setMessage(res.data.message);
    void refresh();
    void loadInfo();
  }

  function handleExportLogs() {
    openExternalUrl(systemLogsExportUrl());
  }

  function handleRestartAndUpdate() {
    window.electronAPI?.restartAndUpdate?.();
  }

  return (
    <div className="space-y-6">
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
            Version {appName}
          </p>
          <p className="mt-3 text-lg font-semibold text-white">
            v{displayVersion}
          </p>
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
          <p className="mb-4 text-sm text-white/55">
            Les mises à jour sont vérifiées automatiquement au lancement de
            l&apos;application installée. Une notification apparaît lorsqu&apos;une
            nouvelle version est téléchargée depuis GitHub Releases.
          </p>
          {updateReady ? (
            <button
              type="button"
              onClick={handleRestartAndUpdate}
              className={GOLD_BTN}
            >
              Mettre à jour CyberForge
            </button>
          ) : (
            <p className="text-sm text-white/45">
              Aucune mise à jour en attente.
            </p>
          )}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={busy !== null}
          onClick={() => void handleRestart()}
          className={GHOST_BTN}
        >
          {busy === "restart" ? "Rechargement…" : "Redémarrer le backend"}
        </button>
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

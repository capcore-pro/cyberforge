import { useCallback, useEffect, useState } from "react";
import { useBackendHealth } from "@/context/BackendHealthContext";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  clearSystemCache,
  fetchSystemInfo,
  restartBackend,
} from "@/lib/settings-api";

export function SystemSettingsPanel() {
  const { status, health, refresh } = useBackendHealth();
  const [version, setVersion] = useState<string>("—");
  const [appName, setAppName] = useState("CyberForge");
  const [busy, setBusy] = useState<"cache" | "restart" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadInfo = useCallback(async () => {
    const res = await fetchSystemInfo();
    if (res.ok && res.data) {
      setVersion(res.data.version);
      setAppName(res.data.app_name);
    }
  }, []);

  useEffect(() => {
    void loadInfo();
  }, [loadInfo]);

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
  }

  return (
    <div className="space-y-6">
      <dl className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-card border border-cf-border-input bg-cf-secondary/40 p-4">
          <dt className="cf-section-label">Statut backend</dt>
          <dd className="mt-2 flex items-center gap-2 text-sm font-medium">
            <span
              className={`inline-block h-2.5 w-2.5 rounded-full ${
                backendOnline ? "bg-cf-success" : "bg-red-500"
              }`}
            />
            <span className={backendOnline ? "text-cf-success" : "text-red-300"}>
              {backendOnline ? "En ligne" : status === "checking" ? "Connexion…" : "Hors ligne"}
            </span>
          </dd>
        </div>
        <div className="rounded-card border border-cf-border-input bg-cf-secondary/40 p-4">
          <dt className="cf-section-label">Version {appName}</dt>
          <dd className="mt-2 text-sm font-medium text-cf-text">
            v{displayVersion}
          </dd>
        </div>
      </dl>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          disabled={busy !== null}
          onClick={() => void handleRestart()}
          className="rounded-control border border-cf-border-input bg-cf-secondary px-4 py-2.5 text-sm text-cf-text hover:border-cf-gold/40 disabled:opacity-50"
        >
          {busy === "restart" ? "Rechargement…" : "Redémarrer le backend"}
        </button>
        <button
          type="button"
          disabled={busy !== null}
          onClick={() => void handleClearCache()}
          className="rounded-control border border-cf-border-input bg-cf-secondary px-4 py-2.5 text-sm text-cf-text hover:border-cf-gold/40 disabled:opacity-50"
        >
          {busy === "cache" ? "Nettoyage…" : "Vider le cache"}
        </button>
      </div>

      {error ? (
        <p className="rounded-control border border-red-500/40 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}
      {message ? (
        <p className="rounded-control border border-cf-border-input bg-cf-secondary/60 px-4 py-3 text-sm text-cf-muted">
          {message}
        </p>
      ) : null}
    </div>
  );
}

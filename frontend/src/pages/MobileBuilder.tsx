import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createMobileApp,
  deleteMobileApp,
  fetchMobileBuildStatus,
  listMobileApps,
  streamMobileGenerate,
  triggerMobileBuild,
  updateMobileApp,
  type MobileAppRecord,
  type MobileAppUpsert,
} from "@/lib/mobile-builder-api";
import { MobileBuilderSidebar } from "@/components/mobile-builder/MobileBuilderSidebar";
import { MobileAppWizard } from "@/components/mobile-builder/MobileAppWizard";
import {
  BuildStatus,
  estimateBuildProgress,
} from "@/components/mobile-builder/BuildStatus";
import type { GenerateLogEntry } from "@/components/mobile-builder/Step4Generate";

const EMPTY_APP: MobileAppUpsert = {
  name: "",
  description: "",
  mode: "client",
  sector: "vitrine",
  primary_color: "#06b6d4",
  secondary_color: "#8b5cf6",
  logo_url: null,
  app_slug: "",
  bundle_id: "",
  features: [],
};

function recordToUpsert(app: MobileAppRecord): MobileAppUpsert {
  return {
    name: app.name,
    description: app.description ?? "",
    mode: app.mode,
    sector: app.sector,
    primary_color: app.primary_color,
    secondary_color: app.secondary_color,
    logo_url: app.logo_url,
    app_slug: app.app_slug,
    bundle_id: app.bundle_id ?? "",
    features: app.features,
  };
}

export function MobileBuilder() {
  const [apps, setApps] = useState<MobileAppRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<MobileAppUpsert>(EMPTY_APP);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [generateLogs, setGenerateLogs] = useState<GenerateLogEntry[]>([]);
  const [generatedFiles, setGeneratedFiles] = useState<string[]>([]);
  const [buildLoading, setBuildLoading] = useState(false);
  const [buildStartedAt, setBuildStartedAt] = useState<number | null>(null);
  const [polling, setPolling] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  const selected = useMemo(
    () => apps.find((a) => a.id === selectedId) ?? null,
    [apps, selectedId],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await listMobileApps();
      setApps(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chargement impossible.");
      setApps([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (selected) {
      setDraft(recordToUpsert(selected));
      setGenerated(
        selected.status === "generated" ||
          selected.status === "building" ||
          selected.status === "ready" ||
          selected.status === "failed",
      );
      if (selected.status === "building") {
        setBuildStartedAt(Date.now());
        setPolling(true);
      }
    } else {
      setDraft(EMPTY_APP);
      setGenerated(false);
    }
    setGenerateLogs([]);
    setGeneratedFiles([]);
  }, [selected?.id]);

  const refreshStatus = useCallback(async () => {
    if (!selectedId) return;
    try {
      const status = await fetchMobileBuildStatus(selectedId);
      setApps((prev) =>
        prev.map((a) => (a.id === selectedId ? status.app : a)),
      );
      if (status.app.status !== "building") {
        setPolling(false);
      }
    } catch {
      // silencieux pour le polling
    }
  }, [selectedId]);

  useEffect(() => {
    if (!polling || !selectedId) return;
    const id = window.setInterval(() => {
      void refreshStatus();
    }, 30_000);
    void refreshStatus();
    return () => window.clearInterval(id);
  }, [polling, selectedId, refreshStatus]);

  async function handleSave(payload: MobileAppUpsert): Promise<string | null> {
    setBusy(true);
    setError(null);
    try {
      const saved = selected
        ? await updateMobileApp(selected.id, payload)
        : await createMobileApp(payload);
      setToast(selected ? "✓ App mise à jour" : "✓ App créée");
      window.setTimeout(() => setToast(null), 4000);
      await load();
      setSelectedId(saved.id);
      return saved.id;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sauvegarde impossible.");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Supprimer cette app mobile ?")) return;
    setBusy(true);
    setError(null);
    try {
      await deleteMobileApp(id);
      setToast("App supprimée");
      window.setTimeout(() => setToast(null), 4000);
      if (selectedId === id) setSelectedId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suppression impossible.");
    } finally {
      setBusy(false);
    }
  }

  function handleNew() {
    setSelectedId(null);
    setDraft(EMPTY_APP);
    setGenerated(false);
    setGenerateLogs([]);
    setGeneratedFiles([]);
  }

  async function handleGenerate() {
    const appId = selectedId ?? (await handleSave(draft));
    if (!appId) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setGenerating(true);
    setGenerateLogs([]);
    setGeneratedFiles([]);
    setError(null);

    await streamMobileGenerate(
      appId,
      {
        onAgentStart: (message) => {
          setGenerateLogs((prev) => [
            ...prev,
            { type: "start", message, timestamp: Date.now() },
          ]);
        },
        onAgentDone: (message, extra) => {
          setGenerateLogs((prev) => [
            ...prev,
            { type: "done", message, timestamp: Date.now() },
          ]);
          const files = extra?.files;
          if (Array.isArray(files)) {
            setGeneratedFiles(files.map((f) => String(f)));
          }
        },
        onDone: (payload) => {
          setGenerated(true);
          setGeneratedFiles(payload.files);
          setToast(`✓ ${payload.screens_count} écrans · ${payload.features_count} features`);
          window.setTimeout(() => setToast(null), 4000);
          void load();
        },
        onError: (message) => {
          setError(message);
          setGenerateLogs((prev) => [
            ...prev,
            { type: "error", message, timestamp: Date.now() },
          ]);
        },
      },
      controller.signal,
    );

    setGenerating(false);
  }

  async function handleBuild(targetId?: string) {
    const appId = targetId ?? selectedId;
    if (!appId) return;
    setBuildLoading(true);
    setError(null);
    try {
      await triggerMobileBuild(appId);
      setBuildStartedAt(Date.now());
      setPolling(true);
      setToast("Build EAS lancé");
      window.setTimeout(() => setToast(null), 4000);
      await load();
      if (!targetId) setSelectedId(appId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Build impossible.");
    } finally {
      setBuildLoading(false);
    }
  }

  const buildProgress = estimateBuildProgress(buildStartedAt);

  return (
    <div className="flex min-h-[75vh] flex-col">
      <div className="mb-4">
        <p className="cf-section-label">Mobile Builder</p>
        <h1 className="text-xl font-semibold text-white">
          Mobile<span className="text-cyan-400">AI</span>
        </h1>
        <p className="text-sm text-cf-muted">
          Générez des apps React Native Android et compilez des APK via EAS Build.
        </p>
      </div>

      {error ? (
        <p className="mb-4 rounded-card border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {toast ? (
        <p className="mb-4 rounded-card border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-200">
          {toast}
        </p>
      ) : null}

      <div className="flex min-h-0 flex-1 rounded-card border border-white/10 bg-white/5 backdrop-blur-xl">
        <MobileBuilderSidebar
          apps={apps}
          selectedId={selectedId}
          loading={loading}
          onSelect={setSelectedId}
          onNew={handleNew}
          onDelete={handleDelete}
          onBuild={(id) => void handleBuild(id)}
        />

        <div className="min-w-0 flex-1 overflow-y-auto p-6">
          <MobileAppWizard
            appId={selectedId}
            value={draft}
            disabled={busy}
            generating={generating}
            generated={generated}
            generateLogs={generateLogs}
            generatedFiles={generatedFiles}
            buildLoading={buildLoading}
            onChange={setDraft}
            onSave={handleSave}
            onGenerate={() => void handleGenerate()}
            onBuild={() => void handleBuild()}
          />
        </div>

        <BuildStatus
          app={selected}
          progress={buildProgress}
          polling={polling}
          onRefresh={() => void refreshStatus()}
        />
      </div>
    </div>
  );
}

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createErpProject,
  deleteErpProject,
  fetchErpStatus,
  listErpProjects,
  restartErpProject,
  stopErpProject,
  streamErpInstall,
  streamErpRecommend,
  updateErpProject,
  type ErpDockerStatus,
  type ErpProjectRecord,
  type ErpProjectUpsert,
  type ErpRecommendation,
  type ErpType,
} from "@/lib/erp-builder-api";
import { ErpBuilderSidebar } from "@/components/erp-builder/ErpBuilderSidebar";
import { ErpWizard } from "@/components/erp-builder/ErpWizard";
import { ErpStatusPanel } from "@/components/erp-builder/ErpStatusPanel";
import {
  mapInstallMessageToSteps,
  type InstallStep,
} from "@/components/erp-builder/Step4Install";

const EMPTY_PROJECT: ErpProjectUpsert = {
  name: "",
  client_name: "",
  company_size: "small",
  budget: "medium",
  modules: [],
  erp_type: null,
  primary_color: "#0f1117",
  admin_email: "admin@cyberforge.local",
  admin_password: "CyberForge2026!",
  port: null,
};

function recordToUpsert(p: ErpProjectRecord): ErpProjectUpsert {
  return {
    name: p.name,
    client_name: p.client_name ?? "",
    company_size: p.company_size,
    budget: p.budget,
    modules: p.modules,
    erp_type: p.erp_type,
    primary_color: p.primary_color,
    logo_url: p.logo_url,
    domain: p.domain,
    admin_email: p.admin_email ?? "admin@cyberforge.local",
    admin_password: p.admin_password ?? "CyberForge2026!",
    port: p.port,
  };
}

export function ErpBuilder() {
  const [projects, setProjects] = useState<ErpProjectRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draft, setDraft] = useState<ErpProjectUpsert>(EMPTY_PROJECT);
  const [toast, setToast] = useState<string | null>(null);

  const [recommendation, setRecommendation] = useState<ErpRecommendation | null>(null);
  const [recommendLoading, setRecommendLoading] = useState(false);
  const [showAlternatives, setShowAlternatives] = useState(false);

  const [installing, setInstalling] = useState(false);
  const [installSteps, setInstallSteps] = useState<InstallStep[]>([]);
  const [installResult, setInstallResult] = useState<{
    url: string;
    admin_email: string;
    admin_password: string;
  } | null>(null);

  const [dockerStatus, setDockerStatus] = useState<ErpDockerStatus | null>(null);
  const [polling, setPolling] = useState(false);

  const abortRef = useRef<AbortController | null>(null);

  const selected = useMemo(
    () => projects.find((p) => p.id === selectedId) ?? null,
    [projects, selectedId],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setProjects(await listErpProjects());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chargement impossible.");
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
      if (selected.url) {
        setInstallResult({
          url: selected.url,
          admin_email: selected.admin_email ?? "",
          admin_password: selected.admin_password ?? "",
        });
      }
      if (selected.status === "running" || selected.status === "installing") {
        setPolling(true);
      }
    } else {
      setDraft(EMPTY_PROJECT);
      setRecommendation(null);
      setInstallResult(null);
    }
  }, [selected?.id]);

  const refreshStatus = useCallback(async () => {
    if (!selectedId) return;
    try {
      const status = await fetchErpStatus(selectedId);
      setDockerStatus(status.docker);
      setProjects((prev) =>
        prev.map((p) => (p.id === selectedId ? status.project : p)),
      );
      if (status.project.status !== "running" && status.project.status !== "installing") {
        setPolling(false);
      }
    } catch {
      // polling silencieux
    }
  }, [selectedId]);

  useEffect(() => {
    if (!polling || !selectedId) return;
    const id = window.setInterval(() => void refreshStatus(), 30_000);
    void refreshStatus();
    return () => window.clearInterval(id);
  }, [polling, selectedId, refreshStatus]);

  async function handleSave(payload: ErpProjectUpsert): Promise<string | null> {
    setError(null);
    try {
      const saved = selected
        ? await updateErpProject(selected.id, payload)
        : await createErpProject(payload);
      setToast(selected ? "Projet mis à jour" : "Projet créé");
      window.setTimeout(() => setToast(null), 3000);
      await load();
      setSelectedId(saved.id);
      return saved.id;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sauvegarde impossible.");
      return null;
    }
  }

  async function handleRecommend() {
    const id = selectedId ?? (await handleSave(draft));
    if (!id) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setRecommendLoading(true);
    setRecommendation(null);
    await streamErpRecommend(
      id,
      {
        onStart: () => {},
        onDone: (rec) => {
          setRecommendation(rec);
          setDraft((d) => ({ ...d, erp_type: rec.erp_type, modules: rec.modules }));
        },
        onError: (msg) => setError(msg),
      },
      controller.signal,
    );
    setRecommendLoading(false);
    await load();
  }

  async function handleChooseErp(type: ErpType) {
    setDraft((d) => ({ ...d, erp_type: type }));
    if (selectedId) {
      await updateErpProject(selectedId, { erp_type: type });
      await load();
    }
    setToast(`ERP sélectionné : ${type}`);
    window.setTimeout(() => setToast(null), 3000);
  }

  async function handleInstall() {
    const id = selectedId ?? (await handleSave(draft));
    if (!id) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setInstalling(true);
    setInstallSteps([]);
    setInstallResult(null);
    setPolling(true);

    await streamErpInstall(
      id,
      {
        onStep: (message) => {
          setInstallSteps((prev) => mapInstallMessageToSteps(message, prev));
        },
        onLog: (message) => {
          setInstallSteps((prev) => mapInstallMessageToSteps(message, prev));
        },
        onDone: (payload) => {
          setInstallResult(payload);
          setInstallSteps((prev) =>
            prev.map((s) => ({ ...s, status: "done" as const })),
          );
          setToast("ERP en ligne !");
          window.setTimeout(() => setToast(null), 4000);
          void load();
          void refreshStatus();
        },
        onError: (msg) => setError(msg),
      },
      controller.signal,
    );
    setInstalling(false);
  }

  function openUrl(url: string) {
    void window.cyberforge?.openExternal?.(url);
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Supprimer ce projet ERP ?")) return;
    try {
      await deleteErpProject(id);
      if (selectedId === id) setSelectedId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suppression impossible.");
    }
  }

  async function handleStop(id: string) {
    try {
      await stopErpProject(id);
      await load();
      await refreshStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Arrêt impossible.");
    }
  }

  async function handleRestart() {
    if (!selectedId) return;
    try {
      await restartErpProject(selectedId);
      setPolling(true);
      await load();
      await refreshStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Redémarrage impossible.");
    }
  }

  function handleNew() {
    setSelectedId(null);
    setDraft(EMPTY_PROJECT);
    setRecommendation(null);
    setInstallResult(null);
    setInstallSteps([]);
  }

  return (
    <div className="flex min-h-[75vh] flex-col">
      <div className="mb-4">
        <p className="cf-section-label">ERP Builder</p>
        <h1 className="text-xl font-semibold text-white">
          Choisissez votre <span className="text-violet-400">ERP</span> en 4 étapes
        </h1>
        <p className="text-sm text-cf-muted">
          Odoo, ERPNext ou ERP Custom — installation Docker automatique.
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
        <ErpBuilderSidebar
          projects={projects}
          selectedId={selectedId}
          loading={loading}
          onSelect={setSelectedId}
          onNew={handleNew}
          onDelete={handleDelete}
          onOpen={(p) => p.url && openUrl(p.url)}
          onStop={handleStop}
        />

        <div className="min-w-0 flex-1 overflow-y-auto p-6">
          <ErpWizard
            projectId={selectedId}
            value={draft}
            recommendation={recommendation}
            recommendLoading={recommendLoading}
            showAlternatives={showAlternatives}
            onToggleAlternatives={() => setShowAlternatives((v) => !v)}
            onChange={setDraft}
            onSave={handleSave}
            onRecommend={() => void handleRecommend()}
            onChooseErp={(type) => void handleChooseErp(type)}
            installing={installing}
            installSteps={installSteps}
            installResult={installResult}
            onInstall={() => void handleInstall()}
            onOpenUrl={openUrl}
          />
        </div>

        <ErpStatusPanel
          project={selected}
          docker={dockerStatus}
          polling={polling}
          onRefresh={() => void refreshStatus()}
          onOpen={openUrl}
          onStop={() => selectedId && void handleStop(selectedId)}
          onRestart={() => void handleRestart()}
        />
      </div>
    </div>
  );
}

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { BackButton } from "@/components/BackButton";
import { Button, Modal } from "@/components/ui";
import { PasswordRevealField } from "@/components/PasswordRevealField";
import {
  ProjectClientStripeSection,
  projectSupportsClientStripe,
} from "@/components/projects/ProjectClientStripeSection";
import { apiErrorMessage } from "@/lib/api-errors";
import { listClients, type ClientRecord } from "@/lib/clients-api";
import { fetchClientStripe } from "@/lib/stripe-api";
import {
  affiliateUnifiedProjectClient,
  duplicateUnifiedProject,
  renameUnifiedProject,
  STATUS_LABELS,
  TYPE_LABELS,
  type UnifiedProject,
} from "@/lib/unified-projects";
import {
  fetchVitrineAuth,
  regenerateVitrinePassword,
  toggleVitrineAuth,
  type VitrineAuthInfo,
} from "@/lib/vitrines-api";
import {
  fetchCmsProjectSettings,
  patchCmsProjectSettings,
  type CmsProjectSettings,
} from "@/lib/cms-projects-api";
import { findDemoIdByGeneration } from "@/lib/demos-api";
import { copyTextToClipboard } from "@/lib/generation-export";
import { PlaywrightScoreBadge } from "@/components/PlaywrightScoreBadge";
import { LighthouseScorePanel } from "@/components/LighthouseScorePanel";
import { DataPaymentPanel } from "@/components/DataPaymentPanel";
import { ProjectClientReviewPanel } from "@/components/projects/ProjectClientReviewPanel";
import { LazyProjectAnalyticsPanel } from "@/components/projects/ProjectAnalyticsPanel";
import { getPlaywrightReport } from "@/lib/playwright-reports";
import { getLighthouseReport } from "@/lib/lighthouse-reports";
import { createSubdomain, deleteSubdomain } from "@/lib/subdomains-api";
import { exportZip, fetchProjectHTML } from "@/lib/editor-api";
import { PreviewDevice } from "@/components/editor/PreviewDevice";
import {
  PREVIEW_DEVICE_ORDER,
  PREVIEW_DEVICE_SPECS,
  type PreviewDeviceType,
} from "@/lib/preview-devices";

interface ProjectDetailViewProps {
  project: UnifiedProject;
  onBack: () => void;
  onEdit: () => void;
  onView: () => void;
  onProjectUpdated: (project: UnifiedProject) => void;
  onDuplicate: (project: UnifiedProject) => void;
  /** Ouvre l'éditeur inline (projets Supabase uniquement). */
  onOpenEditor?: () => void;
  /** Masque l'affiliation client (projets perso). */
  hideClientAffiliate?: boolean;
  extraSections?: ReactNode;
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function statusDotClass(status: UnifiedProject["status"]): string {
  if (status === "online") return "bg-cf-success";
  if (status === "demo") return "bg-cf-info";
  return "bg-red-500";
}

export function ProjectDetailView({
  project,
  onBack,
  onEdit,
  onView,
  onProjectUpdated,
  onDuplicate,
  onOpenEditor,
  hideClientAffiliate = false,
  extraSections,
}: ProjectDetailViewProps) {
  const isVitrine = project.source === "managed_vitrine" && Boolean(project.managedId);
  const isManaged = Boolean(project.managedId);

  const [cmsSettings, setCmsSettings] = useState<CmsProjectSettings | null>(null);
  const [cmsLoading, setCmsLoading] = useState(false);
  const [cmsBusy, setCmsBusy] = useState(false);
  const [cmsError, setCmsError] = useState<string | null>(null);
  const [cmsCopyOk, setCmsCopyOk] = useState(false);

  const [name, setName] = useState(project.name);
  const [nameBusy, setNameBusy] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);

  const [clients, setClients] = useState<ClientRecord[]>([]);
  const [clientsLoading, setClientsLoading] = useState(true);
  const [clientId, setClientId] = useState<string>(project.clientId ?? "");
  const [clientBusy, setClientBusy] = useState(false);
  const [clientError, setClientError] = useState<string | null>(null);

  const [duplicateBusy, setDuplicateBusy] = useState(false);
  const [duplicateError, setDuplicateError] = useState<string | null>(null);

  const [auth, setAuth] = useState<VitrineAuthInfo | null>(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const [clientStripeConfigured, setClientStripeConfigured] = useState<boolean | null>(
    null,
  );

  const [demoUrl, setDemoUrl] = useState<string | null>(() => project.url?.trim() || null);

  const [subdomainBusy, setSubdomainBusy] = useState(false);
  const [subdomainToast, setSubdomainToast] = useState<string | null>(null);
  const [subdomainError, setSubdomainError] = useState<string | null>(null);

  const [zipBusy, setZipBusy] = useState(false);
  const [zipError, setZipError] = useState<string | null>(null);

  const [showPreview, setShowPreview] = useState(false);
  const [previewDevice, setPreviewDevice] = useState<PreviewDeviceType>("mobile");
  const [projectHtml, setProjectHtml] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const showClientStripe = projectSupportsClientStripe(project);

  const projectReportKey =
    project.supabaseProjectId ?? project.managedId ?? project.key;

  const analyticsProjectId = project.supabaseProjectId?.trim() || null;

  const playwrightReport = getPlaywrightReport(projectReportKey);
  const lighthouseReport = getLighthouseReport(projectReportKey);

  useEffect(() => {
    if (!showPreview || !project.supabaseProjectId) {
      return;
    }
    let cancelled = false;
    setPreviewLoading(true);
    setPreviewError(null);
    void fetchProjectHTML(project.supabaseProjectId).then((res) => {
      if (cancelled) return;
      setPreviewLoading(false);
      if (!res.ok || !res.data?.html) {
        setPreviewError(apiErrorMessage(res, "Impossible de charger l'aperçu."));
        setProjectHtml(null);
        return;
      }
      setProjectHtml(res.data.html);
    });
    return () => {
      cancelled = true;
    };
  }, [showPreview, project.supabaseProjectId]);

  useEffect(() => {
    if (!showClientStripe || !project.managedId) {
      setClientStripeConfigured(null);
      return;
    }
    let cancelled = false;
    void fetchClientStripe(project.managedId).then((res) => {
      if (cancelled) return;
      setClientStripeConfigured(res.ok ? Boolean(res.data?.configured) : false);
    });
    return () => {
      cancelled = true;
    };
  }, [showClientStripe, project.managedId]);

  useEffect(() => {
    setName(project.name);
    setClientId(project.clientId ?? "");
  }, [project.key, project.name, project.clientId]);

  useEffect(() => {
    const fromProject = project.url?.trim();
    if (fromProject) {
      setDemoUrl(fromProject);
      return;
    }
    const generationId = project.generationId;
    if (!generationId) {
      setDemoUrl(null);
      return;
    }
    let cancelled = false;
    void findDemoIdByGeneration(generationId).then((res) => {
      if (cancelled || !res.ok) return;
      const url = res.data?.url?.trim() || null;
      setDemoUrl(url);
    });
    return () => {
      cancelled = true;
    };
  }, [project.key, project.url, project.generationId]);

  useEffect(() => {
    let cancelled = false;
    setClientsLoading(true);
    void listClients("client").then((res) => {
      if (cancelled) return;
      setClients(res.ok && Array.isArray(res.data) ? res.data : []);
      setClientsLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadAuth = useCallback(async () => {
    if (!project.managedId) return;
    setAuthLoading(true);
    setAuthError(null);
    try {
      const resp = await fetchVitrineAuth(project.managedId);
      if (resp.ok && resp.data) {
        setAuth(resp.data);
      } else {
        setAuthError(apiErrorMessage(resp, "Impossible de charger le mot de passe."));
      }
    } finally {
      setAuthLoading(false);
    }
  }, [project.managedId]);

  useEffect(() => {
    setAuth(null);
    setAuthError(null);
    if (isVitrine) {
      void loadAuth();
    }
  }, [isVitrine, loadAuth]);

  const loadCmsSettings = useCallback(async () => {
    if (!project.managedId) return;
    setCmsLoading(true);
    setCmsError(null);
    try {
      const resp = await fetchCmsProjectSettings(project.managedId);
      if (resp.ok && resp.data) {
        setCmsSettings(resp.data);
      } else {
        setCmsError(apiErrorMessage(resp, "Impossible de charger le mode CMS."));
      }
    } finally {
      setCmsLoading(false);
    }
  }, [project.managedId]);

  useEffect(() => {
    setCmsSettings(null);
    setCmsError(null);
    if (isManaged) {
      void loadCmsSettings();
    }
  }, [isManaged, loadCmsSettings]);

  async function handleToggleCms(enabled: boolean) {
    if (!project.managedId) return;
    setCmsBusy(true);
    setCmsError(null);
    const resp = await patchCmsProjectSettings(project.managedId, enabled);
    setCmsBusy(false);
    if (!resp.ok || !resp.data) {
      setCmsError(apiErrorMessage(resp, "Mise à jour CMS impossible."));
      return;
    }
    setCmsSettings(resp.data);
  }

  async function handleCopyCmsLink() {
    const link = cmsSettings?.cms_login_url;
    if (!link) return;
    try {
      await copyTextToClipboard(link);
      setCmsCopyOk(true);
      window.setTimeout(() => setCmsCopyOk(false), 2000);
    } catch {
      setCmsError("Copie impossible.");
    }
  }

  async function saveName() {
    const trimmed = name.trim();
    if (!trimmed || trimmed === project.name) return;
    setNameBusy(true);
    setNameError(null);
    const result = await renameUnifiedProject(project, trimmed);
    setNameBusy(false);
    if (!result.ok) {
      setNameError(result.error ?? "Échec mise à jour.");
      setName(project.name);
      return;
    }
    onProjectUpdated({ ...project, name: trimmed });
  }

  async function handleClientChange(nextId: string) {
    setClientId(nextId);
    if (!project.demoId) return;
    setClientBusy(true);
    setClientError(null);
    const result = await affiliateUnifiedProjectClient(
      project,
      nextId.trim() || null,
    );
    setClientBusy(false);
    if (!result.ok) {
      setClientError(result.error ?? "Échec association.");
      setClientId(project.clientId ?? "");
      return;
    }
    onProjectUpdated({ ...project, clientId: nextId.trim() || null });
  }

  async function handleDuplicate() {
    setDuplicateBusy(true);
    setDuplicateError(null);
    const result = await duplicateUnifiedProject(project);
    setDuplicateBusy(false);
    if (!result.ok || !result.project) {
      setDuplicateError(result.error ?? "Duplication impossible.");
      return;
    }
    onDuplicate(result.project);
  }

  const isPagesDevDemo = Boolean(
    demoUrl && demoUrl.includes("cyberforge-demos.pages.dev"),
  );
  const isCapcoreSubdomain = Boolean(demoUrl && demoUrl.includes(".capcore.pro"));

  async function handleCreateSubdomain() {
    setSubdomainBusy(true);
    setSubdomainError(null);
    setSubdomainToast(null);
    const res = await createSubdomain({
      client_name: project.name,
      project_id: project.supabaseProjectId,
    });
    setSubdomainBusy(false);
    if (!res.ok || !res.data) {
      setSubdomainError(apiErrorMessage(res, "Activation du sous-domaine impossible."));
      return;
    }
    const newUrl = res.data.url;
    setDemoUrl(newUrl);
    onProjectUpdated({ ...project, url: newUrl });
    setSubdomainToast(`✓ ${newUrl.replace(/^https?:\/\//, "")} activé`);
    window.setTimeout(() => setSubdomainToast(null), 5000);
  }

  async function handleDeactivateSubdomain() {
    setSubdomainBusy(true);
    setSubdomainError(null);
    setSubdomainToast(null);
    const res = await deleteSubdomain(project.name);
    setSubdomainBusy(false);
    if (!res.ok) {
      setSubdomainError(apiErrorMessage(res, "Désactivation du sous-domaine impossible."));
      return;
    }
    setSubdomainToast("Sous-domaine capcore.pro désactivé");
    window.setTimeout(() => setSubdomainToast(null), 4000);
  }

  async function handleExportZip() {
    if (!project.supabaseProjectId) return;
    setZipBusy(true);
    setZipError(null);
    try {
      await exportZip(project.supabaseProjectId, project.name);
    } catch (err) {
      setZipError(err instanceof Error ? err.message : "Export ZIP impossible.");
    } finally {
      setZipBusy(false);
    }
  }

  async function handleToggleAuth() {
    if (!project.managedId || !auth) return;
    setAuthBusy(true);
    setAuthError(null);
    try {
      const resp = await toggleVitrineAuth(project.managedId, !auth.enabled);
      if (resp.ok && resp.data) {
        setAuth(resp.data);
      } else {
        setAuthError(apiErrorMessage(resp, "Mise à jour impossible."));
      }
    } finally {
      setAuthBusy(false);
    }
  }

  async function handleRegeneratePassword() {
    if (!project.managedId) return;
    setAuthBusy(true);
    setAuthError(null);
    try {
      const resp = await regenerateVitrinePassword(project.managedId);
      if (resp.ok && resp.data) {
        setAuth(resp.data);
      } else {
        setAuthError(apiErrorMessage(resp, "Génération impossible."));
      }
    } finally {
      setAuthBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header className="space-y-3">
        <BackButton onClick={onBack} />
        <p className="cf-section-label">Fiche projet</p>
        <div className="flex flex-wrap items-start gap-3">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={() => void saveName()}
            disabled={nameBusy}
            className="min-w-0 flex-1 rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-xl font-semibold text-cf-text focus:border-cf-gold/50 focus:outline-none"
            aria-label="Nom du projet"
          />
          {nameBusy ? (
            <span className="text-xs text-cf-muted">Enregistrement…</span>
          ) : null}
        </div>
        {nameError ? <p className="text-xs text-red-300">{nameError}</p> : null}
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded border border-cf-gold/30 bg-cf-gold-subtle px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-cf-gold">
            {TYPE_LABELS[project.type]}
          </span>
          <span className="flex items-center gap-1.5 text-xs text-cf-muted">
            <span
              className={`inline-block h-2 w-2 rounded-full ${statusDotClass(project.status)}`}
              aria-hidden
            />
            {STATUS_LABELS[project.status]}
          </span>
          {showClientStripe && clientStripeConfigured !== null ? (
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
                clientStripeConfigured
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                  : "border-amber-500/40 bg-amber-500/10 text-amber-200"
              }`}
            >
              {clientStripeConfigured ? "Paiement actif" : "Paiement non configuré"}
            </span>
          ) : null}
        </div>
        {playwrightReport ? (
          <PlaywrightScoreBadge report={playwrightReport} showDetails />
        ) : null}
        {lighthouseReport ? <LighthouseScorePanel report={lighthouseReport} /> : null}
      </header>

      <section className="space-y-5 rounded-card border border-cf-border-input bg-cf-card p-5 shadow-card">
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
            Client affilié
          </p>
          {hideClientAffiliate ? (
            <p className="mt-2 text-sm text-cf-muted">— Projet perso (sans client)</p>
          ) : project.demoId ? (
            <select
              value={clientId}
              disabled={clientBusy || clientsLoading}
              onChange={(e) => void handleClientChange(e.target.value)}
              className="mt-2 w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none disabled:opacity-60"
            >
              <option value="">Aucun client</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.company?.trim() || c.name}
                </option>
              ))}
            </select>
          ) : (
            <p className="mt-2 text-sm text-cf-muted">
              Aucun client — en créer un dans l&apos;onglet Clients
            </p>
          )}
          {clientError ? <p className="mt-1 text-xs text-red-300">{clientError}</p> : null}
        </div>

        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-cf-label">URL</p>
          {demoUrl ? (
            <a
              href={demoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 block break-all text-sm text-[#d4a843] underline cursor-pointer"
            >
              {demoUrl}
            </a>
          ) : (
            <p className="mt-1 text-sm text-cf-muted">—</p>
          )}
          {isCapcoreSubdomain ? (
            <span className="mt-2 inline-flex items-center rounded-full border border-[#3b82f6]/40 bg-[#3b82f6]/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#60a5fa]">
              capcore.pro ✓
            </span>
          ) : null}
          {isPagesDevDemo ? (
            <div className="mt-3">
              <Button
                variant="ghost"
                size="sm"
                icon="ti ti-world"
                loading={subdomainBusy}
                onClick={() => void handleCreateSubdomain()}
              >
                Activer nom-client.capcore.pro
              </Button>
            </div>
          ) : null}
          {isCapcoreSubdomain ? (
            <div className="mt-2">
              <Button
                variant="ghost"
                size="sm"
                icon="ti ti-trash"
                loading={subdomainBusy}
                onClick={() => void handleDeactivateSubdomain()}
              >
                Désactiver
              </Button>
            </div>
          ) : null}
          {subdomainToast ? (
            <p className="mt-2 text-xs text-emerald-300">{subdomainToast}</p>
          ) : null}
          {subdomainError ? (
            <p className="mt-1 text-xs text-red-300">{subdomainError}</p>
          ) : null}
          {project.supabaseProjectId ? (
            <ProjectClientReviewPanel
              projectId={project.supabaseProjectId}
              projectName={project.name}
              demoUrl={demoUrl}
            />
          ) : null}
        </div>

        <div>
          <p className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
            Créé le
          </p>
          <p className="mt-1 text-sm text-cf-text">{formatDate(project.createdAt)}</p>
        </div>

        {project.prompt ? (
          <div>
            <p className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
              Prompt
            </p>
            <p className="mt-1 whitespace-pre-wrap text-sm text-cf-muted">{project.prompt}</p>
          </div>
        ) : null}

        <ProjectClientStripeSection
          project={project}
          onConfiguredChange={setClientStripeConfigured}
        />

        {extraSections}

        {isManaged ? (
          <div className="space-y-3 rounded-card border border-cf-border-input bg-cf-secondary/40 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-medium text-cf-text">Mode CMS client</p>
              {cmsSettings ? (
                <span
                  className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
                    cmsSettings.cms_enabled
                      ? "border-emerald-500/40 bg-emerald-950/40 text-emerald-300"
                      : "border-cf-border-input text-cf-muted"
                  }`}
                >
                  {cmsSettings.cms_enabled ? "Activé" : "Désactivé"}
                </span>
              ) : null}
            </div>
            <p className="text-[11px] leading-relaxed text-cf-muted">
              Le client peut modifier textes, images et couleurs depuis son site avec le panneau
              d&apos;édition (?cms=1).
            </p>
            {cmsLoading ? (
              <p className="animate-pulse text-xs text-cf-muted">Chargement…</p>
            ) : cmsSettings ? (
              <>
                <label className="flex cursor-pointer items-center gap-2 text-sm text-cf-text">
                  <input
                    type="checkbox"
                    checked={cmsSettings.cms_enabled}
                    disabled={cmsBusy}
                    onChange={(e) => void handleToggleCms(e.target.checked)}
                  />
                  Mode CMS activé
                </label>
                {cmsSettings.cms_enabled && cmsSettings.cms_login_url ? (
                  <div className="space-y-2 rounded-control border border-cf-gold/25 bg-cf-active/30 p-3">
                    <p className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
                      Lien connexion client
                    </p>
                    <p className="break-all font-mono text-xs text-cf-gold">
                      {cmsSettings.cms_login_url}
                    </p>
                    <button
                      type="button"
                      onClick={() => void handleCopyCmsLink()}
                      className="rounded-control border border-cf-gold/40 bg-cf-secondary px-3 py-1.5 text-xs text-cf-gold hover:border-cf-gold"
                    >
                      {cmsCopyOk ? "Copié !" : "Copier le lien"}
                    </button>
                    <p className="text-[10px] text-cf-muted">
                      Inclus automatiquement dans l&apos;email de livraison (séquence bienvenue J0).
                    </p>
                  </div>
                ) : cmsSettings.cms_enabled && !project.url ? (
                  <p className="text-xs text-amber-200/90">
                    URL de production requise pour générer le lien CMS.
                  </p>
                ) : null}
              </>
            ) : (
              <button
                type="button"
                disabled={cmsLoading}
                onClick={() => void loadCmsSettings()}
                className="rounded-control border border-cf-border-input bg-cf-secondary px-3 py-1.5 text-xs text-cf-gold hover:border-cf-gold/50"
              >
                Charger les paramètres CMS
              </button>
            )}
            {cmsError ? <p className="text-xs text-red-300">{cmsError}</p> : null}
          </div>
        ) : null}

        {isVitrine ? (
          <div className="space-y-3 rounded-card border border-cf-border-input bg-cf-secondary/40 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-medium text-cf-text">Protection par mot de passe</p>
              {auth ? (
                <span
                  className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${
                    auth.enabled
                      ? "border-cf-gold/40 bg-cf-active text-cf-gold"
                      : "border-cf-border-input text-cf-muted"
                  }`}
                >
                  {auth.enabled ? "Activée" : "Désactivée"}
                </span>
              ) : null}
            </div>

            {authLoading ? (
              <p className="animate-pulse text-xs text-cf-muted">Chargement du mot de passe…</p>
            ) : auth ? (
              <>
                <PasswordRevealField password={auth.password} />
                {auth.client_email ? (
                  <p className="text-[11px] text-cf-muted">Client : {auth.client_email}</p>
                ) : null}
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={authBusy}
                    onClick={() => void handleToggleAuth()}
                    className="rounded-control border border-cf-border-input bg-cf-secondary px-3 py-1.5 text-xs text-cf-text hover:border-cf-gold/50 hover:text-cf-gold disabled:opacity-50"
                  >
                    {auth.enabled ? "Désactiver" : "Activer"}
                  </button>
                  <button
                    type="button"
                    disabled={authBusy}
                    onClick={() => void handleRegeneratePassword()}
                    className="rounded-control border border-cf-border-input bg-cf-secondary px-3 py-1.5 text-xs text-cf-text hover:border-cf-gold/50 hover:text-cf-gold disabled:opacity-50"
                  >
                    Nouveau mot de passe
                  </button>
                </div>
              </>
            ) : (
              <button
                type="button"
                disabled={authLoading}
                onClick={() => void loadAuth()}
                className="rounded-control border border-cf-border-input bg-cf-secondary px-3 py-1.5 text-xs text-cf-gold hover:border-cf-gold/50"
              >
                Charger le mot de passe
              </button>
            )}

            {authError ? <p className="text-xs text-red-300">{authError}</p> : null}
          </div>
        ) : null}
      </section>

      <DataPaymentPanel
        databaseSchema={(project as any).databaseSchema ?? null}
        authSchema={(project as any).authSchema ?? null}
        paymentConfig={(project as any).paymentConfig ?? null}
      />

      {analyticsProjectId ? (
        <LazyProjectAnalyticsPanel
          project_id={analyticsProjectId}
          generation_id={project.generationId}
        />
      ) : null}

      {duplicateError ? (
        <p className="rounded-card border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {duplicateError}
        </p>
      ) : null}

      {zipError ? (
        <p className="rounded-card border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {zipError}
        </p>
      ) : null}

      <footer className="flex flex-wrap gap-2">
        {onOpenEditor ? (
          <Button variant="primary" icon="ti ti-pencil" onClick={onOpenEditor}>
            Éditer le site
          </Button>
        ) : null}
        {project.supabaseProjectId ? (
          <Button
            variant="ghost"
            icon="ti ti-download"
            loading={zipBusy}
            onClick={() => void handleExportZip()}
          >
            Télécharger ZIP
          </Button>
        ) : null}
        {project.supabaseProjectId ? (
          <Button
            variant="ghost"
            icon="ti ti-devices"
            onClick={() => setShowPreview(true)}
          >
            Aperçu multi-device
          </Button>
        ) : null}
        <button
          type="button"
          onClick={onEdit}
          className="rounded-control border border-cf-border-input bg-cf-secondary px-4 py-2 text-sm text-cf-text hover:border-cf-gold/50 hover:text-cf-gold"
        >
          Modifier
        </button>
        <button
          type="button"
          onClick={() => void handleDuplicate()}
          disabled={duplicateBusy}
          className="rounded-control border border-cf-border-input bg-cf-secondary px-4 py-2 text-sm text-cf-text hover:border-cf-gold/50 hover:text-cf-gold disabled:opacity-50"
        >
          {duplicateBusy ? "Duplication…" : "Dupliquer"}
        </button>
        <button
          type="button"
          onClick={() => {
            if (demoUrl) window.open(demoUrl, "_blank");
          }}
          disabled={!demoUrl}
          className="rounded-control border border-cf-gold/40 bg-cf-active px-4 py-2 text-sm text-cf-gold hover:border-cf-gold disabled:cursor-not-allowed disabled:opacity-50"
        >
          Ouvrir
        </button>
      </footer>

      <Modal
        isOpen={showPreview}
        onClose={() => setShowPreview(false)}
        title={`Aperçu — ${project.name}`}
        size="xl"
        icon="ti ti-devices"
      >
        <div className="mb-4 flex flex-wrap gap-2">
          {PREVIEW_DEVICE_ORDER.map((device) => (
            <button
              key={device}
              type="button"
              onClick={() => setPreviewDevice(device)}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${
                previewDevice === device
                  ? "border-cf-gold/50 bg-cf-gold/15 text-cf-gold"
                  : "border-white/10 bg-white/5 text-cf-muted hover:text-cf-text"
              }`}
            >
              {PREVIEW_DEVICE_SPECS[device].shortLabel}
            </button>
          ))}
        </div>
        {previewLoading ? (
          <p className="py-16 text-center text-sm text-cf-muted animate-pulse">
            Chargement de l&apos;aperçu…
          </p>
        ) : previewError ? (
          <p className="py-16 text-center text-sm text-red-300">{previewError}</p>
        ) : projectHtml ? (
          <PreviewDevice html={projectHtml} device={previewDevice} className="min-h-[70vh]" />
        ) : (
          <p className="py-16 text-center text-sm text-cf-muted">
            Aucun HTML disponible pour ce projet.
          </p>
        )}
      </Modal>
    </div>
  );
}

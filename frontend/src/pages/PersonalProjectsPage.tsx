import { useCallback, useEffect, useState } from "react";
import { Layers, Sparkles } from "lucide-react";
import { BackButton } from "@/components/BackButton";
import { PersoBadge } from "@/components/PersoBadge";
import { PersonalProjectDetailView } from "@/components/personal/PersonalProjectDetailView";
import {
  GLASS_PILL_BTN,
  GLASS_SECTION,
  GOLD_BTN,
  logAccountingApiError,
} from "@/components/accounting/accounting-theme";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  createPersonalProject,
  fetchDesktopTemplates,
  fetchPersonalProjects,
  publishDesktopTemplate,
  USAGE_LABELS,
  type DesktopTemplate,
  type PersonalProject,
  type PersonalUsage,
} from "@/lib/personal-projects-api";
import {
  loadAllUnifiedProjects,
  openProjectUrl,
  TYPE_LABELS,
  type UnifiedProject,
} from "@/lib/unified-projects";

type View = "list" | "detail" | "create";

interface PersonalProjectsPageProps {
  onOpenGenerator: (opts: {
    usage: PersonalUsage;
    priceEur: number | null;
    commercialDescription: string;
    title: string;
  }) => void;
}

function formatDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("fr-FR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

function formatEur(n: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(n);
}

function reportError(context: string, res: { ok: boolean; status?: number }) {
  const msg = apiErrorMessage(res, `${context} impossible.`);
  logAccountingApiError(`Projets perso / ${context}`, msg);
}

function resolveLinkedProject(
  pp: PersonalProject,
  unified: UnifiedProject[],
): UnifiedProject | null {
  if (pp.production_url?.trim()) {
    const slug = pp.pages_project_slug?.trim() || pp.title.toLowerCase().replace(/\s+/g, "-");
    return {
      key: `perso-pages:${pp.id}`,
      name: pp.title,
      type: "vitrine",
      status: "online",
      url: pp.production_url.trim(),
      createdAt: pp.created_at,
      prompt: pp.commercial_description?.trim() || "",
      source: "supabase",
      supabaseProjectId: pp.supabase_project_id ?? undefined,
      projectType: "site_web",
      generationMode: "real_app",
    };
  }
  if (pp.project_key) {
    const found = unified.find((u) => u.key === pp.project_key);
    if (found) return found;
  }
  if (pp.supabase_project_id) {
    return unified.find((u) => u.supabaseProjectId === pp.supabase_project_id) ?? null;
  }
  if (pp.managed_id) {
    return unified.find((u) => u.managedId === pp.managed_id) ?? null;
  }
  return null;
}

export function PersonalProjectsPage({ onOpenGenerator }: PersonalProjectsPageProps) {
  const [view, setView] = useState<View>("list");
  const [projects, setProjects] = useState<PersonalProject[]>([]);
  const [unified, setUnified] = useState<UnifiedProject[]>([]);
  const [templates, setTemplates] = useState<DesktopTemplate[]>([]);
  const [selected, setSelected] = useState<PersonalProject | null>(null);
  const [loading, setLoading] = useState(true);

  const [createTitle, setCreateTitle] = useState("");
  const [createUsage, setCreateUsage] = useState<PersonalUsage>("personal");
  const [createPrice, setCreatePrice] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [createBusy, setCreateBusy] = useState(false);

  const [publishTemplate, setPublishTemplate] = useState<DesktopTemplate | null>(null);
  const [publishPrice, setPublishPrice] = useState("29");
  const [publishDesc, setPublishDesc] = useState("");
  const [publishBusy, setPublishBusy] = useState(false);
  const [publishToast, setPublishToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    const [ppRes, uRes, tplRes] = await Promise.all([
      fetchPersonalProjects(),
      loadAllUnifiedProjects(),
      fetchDesktopTemplates(),
    ]);
    setLoading(false);
    if (!ppRes.ok) {
      reportError("chargement", ppRes);
      setProjects([]);
      return;
    }
    setProjects(Array.isArray(ppRes.data) ? ppRes.data : []);
    setUnified(uRes);
    if (tplRes.ok && Array.isArray(tplRes.data)) {
      setTemplates(tplRes.data);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function openDetail(pp: PersonalProject) {
    setSelected(pp);
    setView("detail");
  }

  async function handleCreateMiniApp(template: DesktopTemplate) {
    const res = await createPersonalProject({
      title: template.title,
      usage_type: "personal",
      app_type: template.id,
      commercial_description: template.description,
    });
    if (!res.ok || !res.data) {
      reportError("création mini-app", res);
      return;
    }
    openDetail(res.data);
    await load();
  }

  async function handlePublish() {
    if (!publishTemplate) return;
    setPublishBusy(true);
    const res = await publishDesktopTemplate(publishTemplate.id, {
      price_eur: Number(publishPrice) || 29,
      commercial_description: publishDesc.trim() || publishTemplate.description,
    });
    setPublishBusy(false);
    if (!res.ok) {
      reportError("publication", res);
      return;
    }
    setPublishToast(res.data?.message ?? "Package publié.");
    setPublishTemplate(null);
    await load();
    window.setTimeout(() => setPublishToast(null), 4000);
  }

  function startGeneratorCreate() {
    onOpenGenerator({
      usage: createUsage,
      priceEur: createPrice.trim() ? Number(createPrice) : null,
      commercialDescription: createDescription.trim(),
      title: createTitle.trim() || "Nouveau projet perso",
    });
  }

  if (view === "detail" && selected) {
    const linked = resolveLinkedProject(selected, unified);
    return (
      <PersonalProjectDetailView
        personal={selected}
        linkedProject={linked}
        onBack={() => {
          setView("list");
          setSelected(null);
          void load();
        }}
        onUpdated={(pp) => {
          setSelected(pp);
          void load();
        }}
        onView={() => {
          if (linked) openProjectUrl(linked);
        }}
      />
    );
  }

  if (view === "create") {
    return (
      <div className="mx-auto max-w-2xl space-y-6">
        <BackButton onClick={() => setView("list")} />
        <header>
          <PersoBadge className="mb-2" />
          <h1 className="cf-page-title">Nouveau projet perso</h1>
          <p className="mt-2 text-sm text-cf-muted">
            Même générateur que les projets clients, sans affiliation client.
          </p>
        </header>

        <div className="space-y-4 rounded-card border border-cf-border-input bg-cf-card p-6 shadow-card">
          <label className="block space-y-1">
            <span className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
              Nom du projet
            </span>
            <input
              value={createTitle}
              onChange={(e) => setCreateTitle(e.target.value)}
              className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text"
              placeholder="Mon outil interne…"
            />
          </label>

          <fieldset className="space-y-2">
            <legend className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
              Usage
            </legend>
            {(Object.keys(USAGE_LABELS) as PersonalUsage[]).map((u) => (
              <label
                key={u}
                className={`flex cursor-pointer items-center gap-3 rounded-control border px-3 py-2 text-sm ${
                  createUsage === u
                    ? "border-fuchsia-400/50 bg-fuchsia-500/10 text-cf-text"
                    : "border-cf-border-input text-cf-muted"
                }`}
              >
                <input
                  type="radio"
                  name="usage"
                  checked={createUsage === u}
                  onChange={() => setCreateUsage(u)}
                  className="accent-fuchsia-400"
                />
                {USAGE_LABELS[u]}
              </label>
            ))}
          </fieldset>

          {createUsage !== "personal" ? (
            <>
              <label className="block space-y-1">
                <span className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
                  Prix (€)
                </span>
                <input
                  type="number"
                  min={0}
                  step={1}
                  value={createPrice}
                  onChange={(e) => setCreatePrice(e.target.value)}
                  className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text"
                  placeholder={createUsage === "subscription" ? "9.99 / mois" : "49"}
                />
              </label>
              <label className="block space-y-1">
                <span className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
                  Description commerciale
                </span>
                <textarea
                  value={createDescription}
                  onChange={(e) => setCreateDescription(e.target.value)}
                  rows={3}
                  className="w-full resize-y rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text"
                  placeholder="Ce que l'acheteur obtient…"
                />
              </label>
            </>
          ) : null}

          <button
            type="button"
            disabled={createBusy}
            onClick={() => startGeneratorCreate()}
            className="w-full rounded-control border border-fuchsia-400/50 bg-fuchsia-500/15 px-4 py-2.5 text-sm font-medium text-fuchsia-100 hover:border-fuchsia-300"
          >
            Ouvrir le générateur
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-[#d4a843]">
            Mat · créations perso
          </p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold text-white">Projets Perso</h1>
            <PersoBadge />
          </div>
          <p className="mt-2 max-w-2xl text-sm text-white/50">
            Projets que vous créez pour vous — usage interne, vente one-shot ou abonnement.
            Distincts des projets clients.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setView("create")}
          className={`${GOLD_BTN} hover:bg-[#d4a843]/80`}
        >
          + Créer un projet perso
        </button>
      </header>

      {publishToast ? (
        <p className="rounded-lg border border-[#d4a843]/30 bg-[#d4a843]/10 px-4 py-3 text-sm text-[#d4a843]">
          {publishToast}
        </p>
      ) : null}

      <section>
        <h2 className="mb-3 text-lg font-semibold text-white">Mes projets perso</h2>
        {loading ? (
          <p className="animate-pulse text-sm text-white/50">Chargement…</p>
        ) : projects.length === 0 ? (
          <div
            className={`${GLASS_SECTION} flex min-h-[140px] flex-col items-center justify-center text-center`}
          >
            <Layers className="mb-2 h-8 w-8 text-white/20" aria-hidden />
            <p className="text-sm text-white/30">Aucun projet perso pour le moment</p>
            <p className="mt-1 text-xs text-white/20">
              Créez-en un ou personnalisez une mini-app ci-dessous
            </p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((pp) => {
              const linked = resolveLinkedProject(pp, unified);
              return (
                <button
                  key={pp.id}
                  type="button"
                  onClick={() => openDetail(pp)}
                  className={`${GLASS_SECTION} flex flex-col text-left transition-all hover:border-[#d4a843]/50`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="line-clamp-2 text-sm font-medium text-white">
                      {pp.title}
                    </h3>
                    <PersoBadge />
                  </div>
                  <p className="mt-2 text-xs text-[#d4a843]/80">
                    {USAGE_LABELS[pp.usage_type]}
                    {pp.price_eur != null ? ` · ${formatEur(pp.price_eur)}` : ""}
                  </p>
                  {linked ? (
                    <p className="mt-1 text-[10px] text-white/45">
                      {TYPE_LABELS[linked.type]} · {linked.status}
                    </p>
                  ) : pp.app_type ? (
                    <p className="mt-1 text-[10px] text-white/45">
                      Mini-app · {pp.app_type}
                    </p>
                  ) : null}
                  <p className="mt-auto pt-3 text-[10px] text-white/35">
                    {formatDate(pp.created_at)}
                  </p>
                </button>
              );
            })}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold text-white">
          Mini-apps pré-fabriquées (P13)
        </h2>
        <p className="mt-1 text-sm text-white/40">
          Templates desktop CapCore — personnalisez, générez ou publiez sur capcore.pro.
        </p>
        <div className={`${GLASS_SECTION} mt-2 p-6`}>
          {templates.length === 0 ? (
            <div className="flex flex-col items-center py-8 text-center">
              <Sparkles className="mb-3 h-10 w-10 text-white/20" aria-hidden />
              <p className="text-sm text-white/30">Templates disponibles prochainement</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-3">
              {templates.map((tpl) => (
                <article
                  key={tpl.id}
                  className="flex flex-col rounded-xl border border-white/10 bg-white/[0.03] p-5"
                >
                  <span className="text-3xl" aria-hidden>
                    {tpl.icon}
                  </span>
                  <h3 className="mt-2 text-base font-medium text-white">{tpl.title}</h3>
                  <p className="mt-2 flex-1 text-xs leading-relaxed text-white/50">
                    {tpl.description}
                  </p>
                  <ul className="mt-3 space-y-1">
                    {tpl.preview_features.map((f) => (
                      <li key={f} className="text-[10px] text-white/40">
                        · {f}
                      </li>
                    ))}
                  </ul>
                  <div className="mt-4 flex flex-col gap-2">
                    <button
                      type="button"
                      onClick={() => void handleCreateMiniApp(tpl)}
                      className={GOLD_BTN}
                    >
                      Personnaliser et générer
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setPublishTemplate(tpl);
                        setPublishDesc(tpl.description);
                      }}
                      className={GLASS_PILL_BTN}
                    >
                      Publier sur capcore.pro
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>

      {publishTemplate ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
          role="dialog"
          aria-modal
        >
          <div className="w-full max-w-md rounded-card border border-cf-border-input bg-cf-card p-6 shadow-card">
            <BackButton className="mb-3" onClick={() => setPublishTemplate(null)} />
            <h3 className="text-base font-semibold text-cf-text">
              Publier {publishTemplate.title}
            </h3>
            <div className="mt-4 space-y-3">
              <label className="block space-y-1">
                <span className="text-[10px] uppercase text-cf-label">Prix (€)</span>
                <input
                  type="number"
                  min={1}
                  value={publishPrice}
                  onChange={(e) => setPublishPrice(e.target.value)}
                  className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm"
                />
              </label>
              <label className="block space-y-1">
                <span className="text-[10px] uppercase text-cf-label">
                  Description commerciale
                </span>
                <textarea
                  value={publishDesc}
                  onChange={(e) => setPublishDesc(e.target.value)}
                  rows={3}
                  className="w-full resize-y rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm"
                />
              </label>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-control border border-cf-border-input px-4 py-2 text-xs"
                onClick={() => setPublishTemplate(null)}
              >
                Annuler
              </button>
              <button
                type="button"
                disabled={publishBusy}
                onClick={() => void handlePublish()}
                className="rounded-control border border-cf-gold/50 bg-cf-active px-4 py-2 text-xs text-cf-gold disabled:opacity-50"
              >
                {publishBusy ? "Publication…" : "Publier"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

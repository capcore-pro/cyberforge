import { useCallback, useEffect, useMemo, useState } from "react";
import { GLASS_SECTION } from "@/components/accounting/accounting-theme";
import { TAB_ACTIVE, TAB_BASE } from "@/components/settings/settings-theme";
import { Badge, Button, Card, Input, Modal } from "@/components/ui";
import { formatRelativeDate } from "@/lib/client-page-utils";
import {
  addInteraction,
  createProspect,
  deleteProspect,
  fetchInteractions,
  fetchProspects,
  fetchStats,
  formatEuro,
  INTERACTION_TYPES,
  moveStatut,
  nextStatut,
  PROSPECT_SOURCES,
  PROSPECT_STATUTS,
  STATUT_COLUMN_LABELS,
  STATUT_HEADER_COLORS,
  STATUT_LABELS,
  updateProspect,
  type PipelineStats,
  type Prospect,
  type ProspectInteraction,
  type ProspectStatut,
} from "@/lib/pipeline-api";

type PipelineTab = "kanban" | "stats";

const TABS: { id: PipelineTab; label: string }[] = [
  { id: "kanban", label: "Kanban" },
  { id: "stats", label: "Statistiques" },
];

function emptyCreateForm() {
  return {
    nom: "",
    entreprise: "",
    email: "",
    telephone: "",
    secteur: "",
    source: "manuel",
    valeur_estimee: "",
    notes: "",
  };
}

function StatBars({ stats }: { stats: PipelineStats }) {
  const max = Math.max(
    ...PROSPECT_STATUTS.map((s) => stats.par_statut[s]?.count ?? 0),
    1,
  );

  return (
    <div className="flex h-48 items-end gap-3">
      {PROSPECT_STATUTS.map((statut) => {
        const count = stats.par_statut[statut]?.count ?? 0;
        const height = Math.round((count / max) * 100);
        return (
          <div key={statut} className="flex min-w-[48px] flex-1 flex-col items-center gap-2">
            <span className="text-xs tabular-nums text-white/60">{count}</span>
            <div className="flex w-full flex-1 items-end">
              <div
                className="w-full rounded-t-md bg-[#d4a843]/70 transition-all"
                style={{ height: `${Math.max(height, 4)}%` }}
              />
            </div>
            <span className="text-center text-[10px] uppercase tracking-wide text-white/40">
              {STATUT_LABELS[statut]}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export function PipelinePage() {
  const [tab, setTab] = useState<PipelineTab>("kanban");
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [stats, setStats] = useState<PipelineStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState(emptyCreateForm);
  const [createBusy, setCreateBusy] = useState(false);

  const [detail, setDetail] = useState<Prospect | null>(null);
  const [interactions, setInteractions] = useState<ProspectInteraction[]>([]);
  const [detailNotes, setDetailNotes] = useState("");
  const [demoUrl, setDemoUrl] = useState("");
  const [interactionType, setInteractionType] = useState("note");
  const [interactionNotes, setInteractionNotes] = useState("");
  const [detailBusy, setDetailBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rows, statRows] = await Promise.all([
        fetchProspects(),
        fetchStats(),
      ]);
      setProspects(rows);
      setStats(statRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chargement impossible.");
      setProspects([]);
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const byStatut = useMemo(() => {
    const map = Object.fromEntries(
      PROSPECT_STATUTS.map((s) => [s, [] as Prospect[]]),
    ) as Record<ProspectStatut, Prospect[]>;
    for (const p of prospects) {
      const key = (p.statut in map ? p.statut : "nouveau") as ProspectStatut;
      map[key].push(p);
    }
    return map;
  }, [prospects]);

  const topProspects = useMemo(
    () =>
      [...prospects]
        .sort((a, b) => (b.valeur_estimee ?? 0) - (a.valeur_estimee ?? 0))
        .slice(0, 5),
    [prospects],
  );

  async function openDetail(prospect: Prospect) {
    setDetail(prospect);
    setDetailNotes(prospect.notes ?? "");
    setDemoUrl(prospect.demo_url ?? "");
    try {
      const rows = await fetchInteractions(prospect.id);
      setInteractions(rows);
    } catch {
      setInteractions([]);
    }
  }

  async function handleCreate() {
    if (!createForm.nom.trim()) return;
    setCreateBusy(true);
    setError(null);
    try {
      await createProspect({
        nom: createForm.nom.trim(),
        entreprise: createForm.entreprise.trim() || undefined,
        email: createForm.email.trim() || undefined,
        telephone: createForm.telephone.trim() || undefined,
        secteur: createForm.secteur.trim() || undefined,
        source: createForm.source,
        valeur_estimee: Number(createForm.valeur_estimee) || 0,
        notes: createForm.notes.trim() || undefined,
      });
      setCreateOpen(false);
      setCreateForm(emptyCreateForm());
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Création impossible.");
    } finally {
      setCreateBusy(false);
    }
  }

  async function handleMoveNext(prospect: Prospect) {
    const next = nextStatut(prospect.statut);
    if (!next) return;
    setBusyId(prospect.id);
    try {
      await moveStatut(prospect.id, next);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Déplacement impossible.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(prospect: Prospect) {
    if (!window.confirm(`Supprimer « ${prospect.nom} » ?`)) return;
    setBusyId(prospect.id);
    try {
      await deleteProspect(prospect.id);
      if (detail?.id === prospect.id) setDetail(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suppression impossible.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDetailStatutChange(statut: ProspectStatut) {
    if (!detail) return;
    setDetailBusy(true);
    try {
      const updated = await moveStatut(detail.id, statut);
      setDetail(updated);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Statut impossible.");
    } finally {
      setDetailBusy(false);
    }
  }

  async function handleSaveNotes() {
    if (!detail) return;
    setDetailBusy(true);
    try {
      const updated = await updateProspect(detail.id, { notes: detailNotes });
      setDetail(updated);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sauvegarde impossible.");
    } finally {
      setDetailBusy(false);
    }
  }

  async function handleSaveDemoUrl() {
    if (!detail) return;
    setDetailBusy(true);
    try {
      const updated = await updateProspect(detail.id, { demo_url: demoUrl });
      setDetail(updated);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "URL démo impossible.");
    } finally {
      setDetailBusy(false);
    }
  }

  async function handleAddInteraction() {
    if (!detail) return;
    setDetailBusy(true);
    try {
      await addInteraction(detail.id, interactionType, interactionNotes.trim() || undefined);
      setInteractionNotes("");
      setInteractions(await fetchInteractions(detail.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Interaction impossible.");
    } finally {
      setDetailBusy(false);
    }
  }

  return (
    <div className="relative mx-auto max-w-[1400px] space-y-8 pb-20">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#d4a843]/80">
            <i className="ti ti-chart-arrows-vertical text-base" aria-hidden />
            Commercial CapCore
          </p>
          <h1 className="flex items-center gap-2 text-2xl font-semibold text-white">
            <i className="ti ti-chart-arrows-vertical text-[#d4a843]" aria-hidden />
            Pipeline
          </h1>
          <p className="mt-2 text-sm text-white/50">
            Suivi Kanban des prospects — de la prise de contact à la signature.
          </p>
        </div>
        {stats ? (
          <Badge variant="gold" size="md">
            {stats.total_prospects} prospect{stats.total_prospects > 1 ? "s" : ""}
          </Badge>
        ) : null}
      </header>

      <nav className="flex flex-wrap gap-1">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`${TAB_BASE} rounded-control ${tab === item.id ? TAB_ACTIVE : ""}`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {error ? (
        <p className="rounded-lg border border-red-500/30 bg-red-950/20 px-4 py-3 text-sm text-red-300">
          {error}
        </p>
      ) : null}

      {tab === "kanban" ? (
        <section>
          {loading ? (
            <p className="animate-pulse py-16 text-center text-sm text-white/50">
              Chargement du pipeline…
            </p>
          ) : (
            <div className="flex gap-4 overflow-x-auto pb-4">
              {PROSPECT_STATUTS.map((statut) => {
                const column = byStatut[statut];
                const valeurCol = column.reduce(
                  (sum, p) => sum + (Number(p.valeur_estimee) || 0),
                  0,
                );
                return (
                  <div
                    key={statut}
                    className="flex w-[260px] shrink-0 flex-col rounded-card border border-white/10 bg-white/[0.02]"
                  >
                    <header
                      className={`border-b px-3 py-3 ${STATUT_HEADER_COLORS[statut]}`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-semibold tracking-wide">
                          {STATUT_COLUMN_LABELS[statut]}
                        </span>
                        <Badge variant="gray" size="sm">
                          {column.length}
                        </Badge>
                      </div>
                      {valeurCol > 0 ? (
                        <p className="mt-1 text-[11px] opacity-80">
                          {formatEuro(valeurCol)}
                        </p>
                      ) : null}
                    </header>
                    <ul className="flex min-h-[200px] flex-col gap-2 p-2">
                      {column.map((prospect) => (
                        <li key={prospect.id}>
                          <Card
                            className="border-white/10 bg-white/[0.03] backdrop-blur-xl"
                            padding="sm"
                          >
                            <p className="text-sm font-medium text-white">
                              {prospect.nom}
                            </p>
                            {prospect.entreprise ? (
                              <p className="mt-0.5 text-xs text-white/50">
                                {prospect.entreprise}
                              </p>
                            ) : null}
                            <div className="mt-2 flex flex-wrap items-center gap-1.5">
                              {prospect.secteur ? (
                                <Badge variant="gray" size="sm">
                                  {prospect.secteur}
                                </Badge>
                              ) : null}
                              {Number(prospect.valeur_estimee) > 0 ? (
                                <span className="text-xs font-semibold text-cf-gold">
                                  {formatEuro(Number(prospect.valeur_estimee))}
                                </span>
                              ) : null}
                            </div>
                            <p className="mt-2 text-[11px] text-white/35">
                              {formatRelativeDate(prospect.created_at)}
                            </p>
                            <div className="mt-3 flex flex-wrap gap-1">
                              {nextStatut(prospect.statut) ? (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  loading={busyId === prospect.id}
                                  onClick={() => void handleMoveNext(prospect)}
                                >
                                  Étape →
                                </Button>
                              ) : null}
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => void openDetail(prospect)}
                              >
                                Détail
                              </Button>
                              <Button
                                size="sm"
                                variant="danger"
                                loading={busyId === prospect.id}
                                onClick={() => void handleDelete(prospect)}
                              >
                                ×
                              </Button>
                            </div>
                          </Card>
                        </li>
                      ))}
                    </ul>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      ) : null}

      {tab === "stats" && stats ? (
        <section className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { label: "Total prospects", value: String(stats.total_prospects) },
              {
                label: "Valeur pipeline",
                value: formatEuro(stats.valeur_pipeline),
              },
              {
                label: "Taux conversion",
                value: `${stats.taux_conversion}%`,
              },
              {
                label: "Prospects ce mois",
                value: String(stats.prospects_ce_mois),
              },
            ].map((kpi) => (
              <Card key={kpi.label} className="border-white/10 bg-white/[0.03]">
                <p className="text-xs uppercase tracking-widest text-white/40">
                  {kpi.label}
                </p>
                <p className="mt-2 text-2xl font-semibold text-[#d4a843]">
                  {kpi.value}
                </p>
              </Card>
            ))}
          </div>

          <div className={`${GLASS_SECTION}`}>
            <h3 className="mb-4 text-sm font-semibold text-white">
              Répartition par statut
            </h3>
            <StatBars stats={stats} />
          </div>

          <div className={`${GLASS_SECTION}`}>
            <h3 className="mb-4 text-sm font-semibold text-white">
              Meilleurs prospects
            </h3>
            {topProspects.length === 0 ? (
              <p className="text-sm text-white/40">Aucun prospect pour l&apos;instant.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-wide text-white/40">
                    <th className="pb-2">Nom</th>
                    <th className="pb-2">Entreprise</th>
                    <th className="pb-2">Statut</th>
                    <th className="pb-2 text-right">Valeur</th>
                  </tr>
                </thead>
                <tbody>
                  {topProspects.map((p) => (
                    <tr key={p.id} className="border-t border-white/5">
                      <td className="py-2 text-white">{p.nom}</td>
                      <td className="py-2 text-white/60">{p.entreprise ?? "—"}</td>
                      <td className="py-2">
                        <Badge variant="gray" size="sm">
                          {STATUT_LABELS[p.statut]}
                        </Badge>
                      </td>
                      <td className="py-2 text-right text-cf-gold">
                        {formatEuro(Number(p.valeur_estimee) || 0)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      ) : null}

      {tab === "kanban" ? (
        <button
          type="button"
          aria-label="Nouveau prospect"
          className="fixed bottom-8 right-8 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-[#d4a843] text-2xl font-light text-black shadow-lg transition hover:bg-[#d4a843]/90"
          onClick={() => setCreateOpen(true)}
        >
          +
        </button>
      ) : null}

      <Modal
        isOpen={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Nouveau prospect"
        subtitle="Ajouter au pipeline commercial"
        icon="ti ti-user-plus"
        footer={
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCreateOpen(false)}>
              Annuler
            </Button>
            <Button
              variant="primary"
              loading={createBusy}
              onClick={() => void handleCreate()}
            >
              Créer
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <Input
            label="Nom"
            required
            value={createForm.nom}
            onChange={(v) => setCreateForm((f) => ({ ...f, nom: v }))}
          />
          <Input
            label="Entreprise"
            value={createForm.entreprise}
            onChange={(v) => setCreateForm((f) => ({ ...f, entreprise: v }))}
          />
          <Input
            label="Email"
            value={createForm.email}
            onChange={(v) => setCreateForm((f) => ({ ...f, email: v }))}
          />
          <Input
            label="Téléphone"
            value={createForm.telephone}
            onChange={(v) => setCreateForm((f) => ({ ...f, telephone: v }))}
          />
          <Input
            label="Secteur"
            value={createForm.secteur}
            onChange={(v) => setCreateForm((f) => ({ ...f, secteur: v }))}
          />
          <Input
            label="Valeur estimée (€)"
            value={createForm.valeur_estimee}
            onChange={(v) => setCreateForm((f) => ({ ...f, valeur_estimee: v }))}
          />
          <label className="block space-y-1">
            <span className="text-xs uppercase tracking-widest text-white/50">
              Source
            </span>
            <select
              value={createForm.source}
              onChange={(e) =>
                setCreateForm((f) => ({ ...f, source: e.target.value }))
              }
              className="w-full rounded-[var(--cf-radius-control)] border border-white/10 bg-white/5 px-3 py-2 text-sm text-white"
            >
              {PROSPECT_SOURCES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-xs uppercase tracking-widest text-white/50">
              Notes
            </span>
            <textarea
              value={createForm.notes}
              onChange={(e) =>
                setCreateForm((f) => ({ ...f, notes: e.target.value }))
              }
              rows={3}
              className="w-full rounded-[var(--cf-radius-control)] border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-white"
            />
          </label>
        </div>
      </Modal>

      <Modal
        isOpen={Boolean(detail)}
        onClose={() => setDetail(null)}
        title={detail?.nom ?? ""}
        subtitle={detail?.entreprise ?? undefined}
        icon="ti ti-briefcase"
        size="lg"
        footer={
          detail ? (
            <Badge variant="teal">{STATUT_LABELS[detail.statut]}</Badge>
          ) : undefined
        }
      >
        {detail ? (
          <div className="space-y-6">
            <section className="grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-xs text-white/40">Email</p>
                <p className="text-sm text-white">{detail.email ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-white/40">Téléphone</p>
                <p className="text-sm text-white">{detail.telephone ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-white/40">Secteur</p>
                <p className="text-sm text-white">{detail.secteur ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-white/40">Valeur estimée</p>
                <p className="text-sm text-cf-gold">
                  {formatEuro(Number(detail.valeur_estimee) || 0)}
                </p>
              </div>
            </section>

            <section>
              <p className="mb-2 text-xs uppercase tracking-widest text-white/40">
                Notes
              </p>
              <textarea
                value={detailNotes}
                onChange={(e) => setDetailNotes(e.target.value)}
                rows={4}
                className="w-full rounded-[var(--cf-radius-control)] border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-white"
              />
              <Button
                className="mt-2"
                size="sm"
                variant="ghost"
                loading={detailBusy}
                onClick={() => void handleSaveNotes()}
              >
                Enregistrer les notes
              </Button>
            </section>

            <section>
              <p className="mb-2 text-xs uppercase tracking-widest text-white/40">
                Statut pipeline
              </p>
              <select
                value={detail.statut}
                disabled={detailBusy}
                onChange={(e) =>
                  void handleDetailStatutChange(e.target.value as ProspectStatut)
                }
                className="w-full rounded-[var(--cf-radius-control)] border border-white/10 bg-white/5 px-3 py-2 text-sm text-white"
              >
                {PROSPECT_STATUTS.map((s) => (
                  <option key={s} value={s}>
                    {STATUT_LABELS[s]}
                  </option>
                ))}
              </select>
            </section>

            <section>
              <p className="mb-2 text-xs uppercase tracking-widest text-white/40">
                Lier une démo
              </p>
              <div className="flex gap-2">
                <Input
                  value={demoUrl}
                  onChange={setDemoUrl}
                  placeholder="https://…"
                  className="flex-1"
                />
                <Button
                  variant="ghost"
                  loading={detailBusy}
                  onClick={() => void handleSaveDemoUrl()}
                >
                  Lier
                </Button>
              </div>
            </section>

            <section>
              <p className="mb-3 text-xs uppercase tracking-widest text-white/40">
                Interactions
              </p>
              <ul className="mb-4 max-h-40 space-y-2 overflow-y-auto">
                {interactions.length === 0 ? (
                  <li className="text-sm text-white/40">Aucune interaction.</li>
                ) : (
                  interactions.map((item) => (
                    <li
                      key={item.id}
                      className="rounded-control border border-white/10 bg-white/[0.02] px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <Badge variant="gray" size="sm">
                          {item.type}
                        </Badge>
                        <span className="text-[11px] text-white/35">
                          {formatRelativeDate(item.created_at)}
                        </span>
                      </div>
                      {item.notes ? (
                        <p className="mt-1 text-xs text-white/60">{item.notes}</p>
                      ) : null}
                    </li>
                  ))
                )}
              </ul>
              <div className="flex flex-wrap gap-2">
                <select
                  value={interactionType}
                  onChange={(e) => setInteractionType(e.target.value)}
                  className="rounded-[var(--cf-radius-control)] border border-white/10 bg-white/5 px-3 py-2 text-sm text-white"
                >
                  {INTERACTION_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <textarea
                  value={interactionNotes}
                  onChange={(e) => setInteractionNotes(e.target.value)}
                  rows={2}
                  placeholder="Notes…"
                  className="min-w-[200px] flex-1 rounded-[var(--cf-radius-control)] border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-white"
                />
                <Button
                  variant="primary"
                  loading={detailBusy}
                  onClick={() => void handleAddInteraction()}
                >
                  Ajouter
                </Button>
              </div>
            </section>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import { copyTextToClipboard } from "@/lib/generation-export";
import {
  fetchToolboxComposants,
  fetchToolboxSecteurs,
  generateToolboxSeoMeta,
  searchToolboxIcones,
  searchToolboxIllustrations,
  searchToolboxPhotos,
  type SectorData,
  type SeoMetaPayload,
  type SeoMetaResult,
  type ToolboxComposant,
  type ToolboxIcon,
  type ToolboxIllustration,
  type ToolboxPhoto,
} from "@/lib/toolbox-api";
import {
  importToolboxPhotoToMedia,
  importToolboxSvgToMedia,
} from "@/lib/toolbox-media-import";
import { ToolboxCompetitorTab } from "@/components/ToolboxCompetitorTab";

type MainTab = "palettes" | "visuels" | "composants" | "seo" | "concurrents";
type VisuelSubTab = "photos" | "icones" | "illustrations";

const MAIN_TABS: { id: MainTab; label: string }[] = [
  { id: "palettes", label: "Palettes" },
  { id: "visuels", label: "Visuels" },
  { id: "composants", label: "Composants" },
  { id: "seo", label: "SEO" },
  { id: "concurrents", label: "Analyse concurrents" },
];

const VISUEL_TABS: { id: VisuelSubTab; label: string }[] = [
  { id: "photos", label: "Photos" },
  { id: "icones", label: "Icônes" },
  { id: "illustrations", label: "Illustrations" },
];

const SECTOR_DISPLAY: Record<string, string> = {
  restauration: "Restauration",
  nautisme: "Nautisme",
  immobilier: "Immobilier",
  sante: "Santé",
  artisanat: "Artisanat",
  beaute: "Beauté",
  sport: "Sport",
  technologie: "Technologie",
  education: "Éducation",
  commerce: "Commerce",
};

function sectorLabel(nom: string): string {
  return SECTOR_DISPLAY[nom] ?? nom;
}

function CopyButton({
  label,
  text,
  className = "",
}: {
  label: string;
  text: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await copyTextToClipboard(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }

  return (
    <button
      type="button"
      onClick={() => void handleCopy()}
      className={`rounded-control border border-cf-border-input bg-cf-secondary px-3 py-1.5 text-xs text-cf-text transition hover:border-cf-gold/50 hover:text-cf-gold ${className}`}
    >
      {copied ? "Copié !" : label}
    </button>
  );
}

function ComposantPreview({ categorie }: { categorie: string }) {
  const layouts: Record<string, string> = {
    layout: "flex h-20 flex-col gap-1 p-2",
    content: "grid h-20 grid-cols-3 gap-1 p-2",
    conversion: "flex h-20 items-center justify-center p-2",
    "social-proof": "grid h-20 grid-cols-2 gap-1 p-2",
    media: "h-20 p-2",
    commerce: "grid h-20 grid-cols-2 gap-1 p-2",
  };
  const layout = layouts[categorie] ?? layouts.content;

  return (
    <div
      className={`overflow-hidden rounded-control border border-cf-border-input bg-cf-main ${layout}`}
      aria-hidden
    >
      <div className="rounded-sm bg-cf-gold/30" />
      <div className="rounded-sm bg-cf-gold/15" />
      <div className="rounded-sm bg-cf-gold/40" />
    </div>
  );
}

function PalettesTab({ secteurs }: { secteurs: SectorData[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {secteurs.map((s) => {
        const paletteText = `${s.palette.primary}, ${s.palette.secondary}, ${s.palette.accent}`;
        return (
          <article
            key={s.nom}
            className="rounded-card border border-cf-border-input bg-cf-card p-4 shadow-card"
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold text-cf-text">{sectorLabel(s.nom)}</h3>
              <CopyButton label="Copier palette" text={paletteText} />
            </div>

            <div className="mt-3 flex gap-2">
              {(
                [
                  ["primary", s.palette.primary],
                  ["secondary", s.palette.secondary],
                  ["accent", s.palette.accent],
                ] as const
              ).map(([key, hex]) => (
                <div key={key} className="flex-1 text-center">
                  <div
                    className="h-12 w-full rounded-control border border-cf-border-input"
                    style={{ backgroundColor: hex }}
                    title={hex}
                  />
                  <p className="mt-1 font-mono text-[10px] text-cf-muted">{hex}</p>
                </div>
              ))}
            </div>

            <p className="mt-3 text-xs text-cf-muted">
              <span className="text-cf-label">Titres :</span> {s.typo.heading}
              <br />
              <span className="text-cf-label">Corps :</span> {s.typo.body}
            </p>

            <div className="mt-3">
              <p className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
                Composants recommandés
              </p>
              <div className="mt-1.5 flex flex-wrap gap-1">
                {s.composants.map((c) => (
                  <span
                    key={c}
                    className="rounded border border-cf-gold/25 bg-cf-gold-subtle px-2 py-0.5 text-[10px] text-cf-gold"
                  >
                    {c}
                  </span>
                ))}
              </div>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function VisuelsTab({ secteurs }: { secteurs: SectorData[] }) {
  const [subTab, setSubTab] = useState<VisuelSubTab>("photos");
  const [search, setSearch] = useState("");
  const [secteur, setSecteur] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [photos, setPhotos] = useState<ToolboxPhoto[]>([]);
  const [icones, setIcones] = useState<ToolboxIcon[]>([]);
  const [illustrations, setIllustrations] = useState<ToolboxIllustration[]>([]);
  const [importBusyId, setImportBusyId] = useState<string | null>(null);
  const [importOk, setImportOk] = useState<string | null>(null);

  const runSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    setImportOk(null);
    try {
      if (subTab === "photos") {
        const res = await searchToolboxPhotos({
          query: search,
          secteur: secteur || undefined,
          per_page: 12,
        });
        if (!res.ok || !res.data) {
          setError(apiErrorMessage(res, "Recherche photos impossible."));
          setPhotos([]);
          return;
        }
        setPhotos(res.data.photos);
      } else if (subTab === "icones") {
        const res = await searchToolboxIcones({ query: search, limit: 24 });
        if (!res.ok || !res.data) {
          setError(apiErrorMessage(res, "Recherche icônes impossible."));
          setIcones([]);
          return;
        }
        setIcones(res.data.icones);
      } else {
        const res = await searchToolboxIllustrations({ query: search, limit: 12 });
        if (!res.ok || !res.data) {
          setError(apiErrorMessage(res, "Recherche illustrations impossible."));
          setIllustrations([]);
          return;
        }
        setIllustrations(res.data.illustrations);
      }
    } finally {
      setLoading(false);
    }
  }, [search, secteur, subTab]);

  useEffect(() => {
    void runSearch();
  }, [subTab]);

  async function handleImportPhoto(photo: ToolboxPhoto) {
    setImportBusyId(photo.id);
    setImportOk(null);
    const tags = ["toolbox", "photo", photo.source, secteur || "general"].filter(Boolean).join(",");
    const res = await importToolboxPhotoToMedia(photo, tags);
    setImportBusyId(null);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Ajout médiathèque impossible."));
      return;
    }
    setImportOk(photo.id);
    window.setTimeout(() => setImportOk(null), 2000);
  }

  async function handleImportSvg(
    id: string,
    svgUrl: string,
    filename: string,
    kind: "icone" | "illustration",
  ) {
    setImportBusyId(id);
    setImportOk(null);
    const tags = ["toolbox", kind, search || secteur || "general"].filter(Boolean).join(",");
    const res = await importToolboxSvgToMedia(svgUrl, filename, tags);
    setImportBusyId(null);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Ajout médiathèque impossible."));
      return;
    }
    setImportOk(id);
    window.setTimeout(() => setImportOk(null), 2000);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 rounded-card border border-cf-border-input bg-cf-card p-4 sm:flex-row sm:flex-wrap sm:items-end">
        <label className="min-w-[200px] flex-1 space-y-1">
          <span className="text-[10px] uppercase tracking-wider text-cf-label">Recherche</span>
          <input
            className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Mot-clé en anglais ou français…"
            onKeyDown={(e) => e.key === "Enter" && void runSearch()}
          />
        </label>
        <label className="min-w-[160px] space-y-1">
          <span className="text-[10px] uppercase tracking-wider text-cf-label">Secteur</span>
          <select
            className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
            value={secteur}
            onChange={(e) => setSecteur(e.target.value)}
          >
            <option value="">Tous / mot-clé libre</option>
            {secteurs.map((s) => (
              <option key={s.nom} value={s.nom}>
                {sectorLabel(s.nom)}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => void runSearch()}
          disabled={loading}
          className="rounded-control border border-cf-gold/50 bg-cf-active px-4 py-2 text-sm font-medium text-cf-gold hover:border-cf-gold disabled:opacity-50"
        >
          {loading ? "Recherche…" : "Rechercher"}
        </button>
      </div>

      <div className="cf-subtabs">
        {VISUEL_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setSubTab(t.id)}
            className={`cf-subtab ${subTab === t.id ? "cf-subtab-active" : ""}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error ? (
        <p className="rounded-card border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {subTab === "photos" ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {photos.map((p) => (
            <article
              key={p.id}
              className="overflow-hidden rounded-card border border-cf-border-input bg-cf-card shadow-card"
            >
              <img
                src={p.url_thumb}
                alt=""
                className="aspect-[4/3] w-full object-cover"
                loading="lazy"
              />
              <div className="space-y-2 p-3">
                <p className="text-[10px] uppercase text-cf-muted">
                  {p.source}
                  {p.author ? ` · ${p.author}` : ""}
                </p>
                <button
                  type="button"
                  disabled={importBusyId === p.id}
                  onClick={() => void handleImportPhoto(p)}
                  className="w-full rounded-control border border-cf-gold/40 bg-cf-active py-1.5 text-xs text-cf-gold hover:border-cf-gold disabled:opacity-50"
                >
                  {importOk === p.id
                    ? "Ajouté !"
                    : importBusyId === p.id
                      ? "Import…"
                      : "Ajouter à la Médiathèque"}
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : null}

      {subTab === "icones" ? (
        <div className="grid gap-3 grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8">
          {icones.map((icon) => (
            <article
              key={icon.name}
              className="flex flex-col items-center rounded-card border border-cf-border-input bg-cf-card p-3 shadow-card"
            >
              <img
                src={icon.svg_url}
                alt={icon.name}
                className="h-12 w-12 object-contain"
                loading="lazy"
              />
              <p className="mt-2 line-clamp-2 text-center font-mono text-[9px] text-cf-muted">
                {icon.name}
              </p>
              <button
                type="button"
                disabled={importBusyId === icon.name}
                onClick={() =>
                  void handleImportSvg(
                    icon.name,
                    icon.svg_url,
                    `toolbox-icon-${icon.prefix}-${icon.icon}.svg`,
                    "icone",
                  )
                }
                className="mt-2 w-full rounded-control border border-cf-border-input py-1 text-[10px] text-cf-gold hover:border-cf-gold/50 disabled:opacity-50"
              >
                {importOk === icon.name ? "OK" : "Médiathèque"}
              </button>
            </article>
          ))}
        </div>
      ) : null}

      {subTab === "illustrations" ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {illustrations.map((ill) => (
            <article
              key={ill.id}
              className="rounded-card border border-cf-border-input bg-cf-card p-4 shadow-card"
            >
              <div className="flex aspect-[16/10] items-center justify-center rounded-control bg-cf-main p-4">
                <img
                  src={ill.svg_url}
                  alt={ill.title}
                  className="max-h-full max-w-full object-contain"
                  loading="lazy"
                />
              </div>
              <p className="mt-2 text-sm font-medium text-cf-text">{ill.title}</p>
              <button
                type="button"
                disabled={importBusyId === ill.id}
                onClick={() =>
                  void handleImportSvg(
                    ill.id,
                    ill.svg_url,
                    `toolbox-illustration-${ill.id}.svg`,
                    "illustration",
                  )
                }
                className="mt-2 w-full rounded-control border border-cf-gold/40 bg-cf-active py-1.5 text-xs text-cf-gold hover:border-cf-gold disabled:opacity-50"
              >
                {importOk === ill.id ? "Ajouté !" : "Ajouter à la Médiathèque"}
              </button>
            </article>
          ))}
        </div>
      ) : null}

      {!loading &&
      ((subTab === "photos" && photos.length === 0) ||
        (subTab === "icones" && icones.length === 0) ||
        (subTab === "illustrations" && illustrations.length === 0)) ? (
        <p className="text-center text-sm text-cf-muted">Aucun résultat. Lancez une recherche.</p>
      ) : null}
    </div>
  );
}

function ComposantsTab({ composants }: { composants: ToolboxComposant[] }) {
  const [categorie, setCategorie] = useState<string>("all");
  const categories = useMemo(() => {
    const set = new Set(composants.map((c) => c.categorie));
    return ["all", ...Array.from(set).sort()];
  }, [composants]);

  const filtered = useMemo(() => {
    if (categorie === "all") return composants;
    return composants.filter((c) => c.categorie === categorie);
  }, [composants, categorie]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-cf-muted">Catégorie :</span>
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => setCategorie(cat)}
            className={`rounded-full border px-3 py-1 text-xs transition ${
              categorie === cat
                ? "border-cf-gold/50 bg-cf-active text-cf-gold"
                : "border-cf-border-input text-cf-muted hover:text-cf-text"
            }`}
          >
            {cat === "all" ? "Toutes" : cat}
          </button>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {filtered.map((c) => (
          <article
            key={c.id}
            className="rounded-card border border-cf-border-input bg-cf-card p-4 shadow-card"
          >
            <div className="flex gap-4">
              <div className="w-28 shrink-0">
                <ComposantPreview categorie={c.categorie} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-sm font-semibold text-cf-text">{c.label}</h3>
                    <p className="text-[10px] uppercase text-cf-gold">{c.id}</p>
                  </div>
                  <CopyButton label="Copier le code" text={c.snippet} />
                </div>
                <p className="mt-2 text-xs text-cf-muted">{c.description}</p>
                <p className="mt-2 text-[10px] text-cf-label">
                  {c.categorie} · {c.dependances.join(", ")}
                </p>
              </div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function SeoTab({ secteurs }: { secteurs: SectorData[] }) {
  const [form, setForm] = useState<SeoMetaPayload>({
    secteur: "restauration",
    nom_entreprise: "",
    ville: "",
    description_courte: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SeoMetaResult | null>(null);

  const schemaJson = useMemo(
    () => (result ? JSON.stringify(result.schema_org, null, 2) : ""),
    [result],
  );

  async function handleGenerate(event: React.FormEvent) {
    event.preventDefault();
    if (!form.nom_entreprise.trim() || !form.ville.trim() || !form.description_courte.trim()) {
      setError("Remplissez tous les champs.");
      return;
    }
    setBusy(true);
    setError(null);
    const res = await generateToolboxSeoMeta({
      secteur: form.secteur,
      nom_entreprise: form.nom_entreprise.trim(),
      ville: form.ville.trim(),
      description_courte: form.description_courte.trim(),
    });
    setBusy(false);
    if (!res.ok || !res.data) {
      setError(apiErrorMessage(res, "Génération SEO impossible."));
      return;
    }
    setResult(res.data);
  }

  const fields: { key: keyof SeoMetaResult; label: string; multiline?: boolean }[] = [
    { key: "title", label: "Title (≤ 60)" },
    { key: "meta_description", label: "Meta description (≤ 155)" },
    { key: "og_title", label: "OG title" },
    { key: "og_description", label: "OG description" },
  ];

  return (
    <div className="space-y-6">
      <form
        onSubmit={(e) => void handleGenerate(e)}
        className="grid gap-4 rounded-card border border-cf-border-input bg-cf-card p-5 sm:grid-cols-2"
      >
        <label className="space-y-1 sm:col-span-2">
          <span className="text-[10px] uppercase tracking-wider text-cf-label">Secteur</span>
          <select
            className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text"
            value={form.secteur}
            onChange={(e) => setForm((f) => ({ ...f, secteur: e.target.value }))}
          >
            {secteurs.map((s) => (
              <option key={s.nom} value={s.nom}>
                {sectorLabel(s.nom)}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-[10px] uppercase tracking-wider text-cf-label">Nom entreprise</span>
          <input
            className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text"
            value={form.nom_entreprise}
            onChange={(e) => setForm((f) => ({ ...f, nom_entreprise: e.target.value }))}
            required
          />
        </label>
        <label className="space-y-1">
          <span className="text-[10px] uppercase tracking-wider text-cf-label">Ville</span>
          <input
            className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text"
            value={form.ville}
            onChange={(e) => setForm((f) => ({ ...f, ville: e.target.value }))}
            required
          />
        </label>
        <label className="space-y-1 sm:col-span-2">
          <span className="text-[10px] uppercase tracking-wider text-cf-label">
            Description courte
          </span>
          <textarea
            className="w-full resize-y rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text"
            rows={3}
            value={form.description_courte}
            onChange={(e) => setForm((f) => ({ ...f, description_courte: e.target.value }))}
            required
          />
        </label>
        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={busy}
            className="rounded-control border border-cf-gold bg-cf-gold px-6 py-2.5 text-sm font-medium text-cf-main hover:bg-cf-gold-hover disabled:opacity-50"
          >
            {busy ? "Génération…" : "Générer"}
          </button>
        </div>
      </form>

      {error ? (
        <p className="rounded-card border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="space-y-4">
          {fields.map(({ key, label }) => (
            <div
              key={key}
              className="rounded-card border border-cf-border-input bg-cf-card p-4"
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
                  {label}
                </span>
                <CopyButton label="Copier" text={String(result[key])} />
              </div>
              <p className="text-sm text-cf-text">{String(result[key])}</p>
            </div>
          ))}

          <div className="rounded-card border border-cf-border-input bg-cf-card p-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
                Mots-clés (10)
              </span>
              <CopyButton label="Copier" text={result.keywords.join(", ")} />
            </div>
            <div className="flex flex-wrap gap-1">
              {result.keywords.map((kw) => (
                <span
                  key={kw}
                  className="rounded border border-cf-border-input bg-cf-secondary px-2 py-0.5 text-xs text-cf-text"
                >
                  {kw}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-card border border-cf-border-input bg-cf-card p-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
                JSON-LD (schema.org)
              </span>
              <CopyButton label="Copier JSON-LD" text={schemaJson} />
            </div>
            <pre className="max-h-80 overflow-auto rounded-control border border-cf-border-input bg-cf-main p-3 font-mono text-[11px] leading-relaxed text-cf-gold">
              {schemaJson}
            </pre>
          </div>
        </div>
      ) : null}
    </div>
  );
}

/**
 * Boîte à outils — palettes sectorielles, visuels, composants UI et SEO.
 */
export function ToolboxPage() {
  const [tab, setTab] = useState<MainTab>("palettes");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [secteurs, setSecteurs] = useState<SectorData[]>([]);
  const [composants, setComposants] = useState<ToolboxComposant[]>([]);
  const [secteursLoaded, setSecteursLoaded] = useState(false);
  const [composantsLoaded, setComposantsLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadSecteurs() {
      if (secteursLoaded) return;
      setLoading(true);
      setError(null);
      const res = await fetchToolboxSecteurs();
      if (cancelled) return;
      setLoading(false);
      if (!res.ok || !res.data) {
        setError(apiErrorMessage(res, "Impossible de charger les secteurs."));
        return;
      }
      setSecteurs(res.data.secteurs);
      setSecteursLoaded(true);
    }

    async function loadComposants() {
      if (composantsLoaded) return;
      setLoading(true);
      setError(null);
      const res = await fetchToolboxComposants();
      if (cancelled) return;
      setLoading(false);
      if (!res.ok || !res.data) {
        setError(apiErrorMessage(res, "Impossible de charger les composants."));
        return;
      }
      setComposants(res.data.composants);
      setComposantsLoaded(true);
    }

    if (tab === "composants") {
      void loadComposants();
    } else {
      void loadSecteurs();
    }

    return () => {
      cancelled = true;
    };
  }, [tab, secteursLoaded, composantsLoaded]);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header>
        <p className="cf-section-label">CapCore</p>
        <h1 className="cf-page-title mt-1">Toolbox</h1>
        <p className="mt-2 max-w-2xl text-sm text-cf-muted">
          Palettes par secteur, banques visuelles, snippets shadcn/ui + Framer Motion et
          métadonnées SEO générées par IA.
        </p>
      </header>

      <nav className="cf-subtabs border-b border-cf-border-input pb-1">
        {MAIN_TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`cf-subtab mb-1 ${tab === item.id ? "cf-subtab-active" : ""}`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {loading ? (
        <p className="animate-pulse text-sm text-cf-muted">Chargement de la toolbox…</p>
      ) : null}

      {error ? (
        <p className="rounded-card border border-red-500/30 bg-red-950/30 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      {!loading && tab === "palettes" ? <PalettesTab secteurs={secteurs} /> : null}
      {!loading && tab === "visuels" ? <VisuelsTab secteurs={secteurs} /> : null}
      {!loading && tab === "composants" ? <ComposantsTab composants={composants} /> : null}
      {!loading && tab === "seo" ? <SeoTab secteurs={secteurs} /> : null}
      {!loading && tab === "concurrents" ? (
        <ToolboxCompetitorTab secteurs={secteurs} />
      ) : null}
    </div>
  );
}

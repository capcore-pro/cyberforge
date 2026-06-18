import { useEffect, useState } from "react";
import { apiClient, resolveApiBaseUrl } from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface VideoClientOrder {
  id: string;
  client_name: string;
  client_email: string;
  client_company?: string;
  secteur: string;
  objectif: string;
  ton: string;
  status: string;
  prix_estime_min: number;
  prix_estime_max: number;
  created_at: string;
}

interface VideoClientOrderFull extends VideoClientOrder {
  client_phone?: string;
  produits_services?: string;
  public_cible?: string;
  slogan?: string;
  couleurs_marque?: string;
  duree_souhaitee: number;
  exemples_references?: string;
  notes_libres?: string;
  nb_scenes: number;
  musique_premium: boolean;
  overlay_texte: boolean;
  livraison_express: boolean;
  scenes_data?: ClientScene[];
  video_project_id?: string;
}

interface ClientScene {
  description_fr: string;
  prompt_en: string;
}

interface GeneratedScenes {
  order_id: string;
  client_name: string;
  secteur: string;
  scenes: ClientScene[];
  nb_scenes: number;
  duree_souhaitee: number;
  slogan: string;
}

interface BriefForm {
  client_name: string;
  client_email: string;
  client_company: string;
  client_phone: string;
  secteur: string;
  objectif: string;
  ton: string;
  produits_services: string;
  public_cible: string;
  slogan: string;
  couleurs_marque: string;
  duree_souhaitee: number;
  exemples_references: string;
  notes_libres: string;
  nb_scenes: number;
  musique_premium: boolean;
  overlay_texte: boolean;
  livraison_express: boolean;
}

const SECTEURS = [
  { value: "restaurant", label: "🍽️ Restaurant" },
  { value: "immobilier", label: "🏠 Immobilier" },
  { value: "fitness", label: "💪 Fitness" },
  { value: "mode", label: "👗 Mode" },
  { value: "automobile", label: "🚗 Automobile" },
  { value: "hotel", label: "🏨 Hôtel" },
  { value: "medical", label: "🏥 Médical" },
  { value: "tech", label: "💻 Tech" },
  { value: "artisan", label: "🔨 Artisan" },
  { value: "beaute", label: "💄 Beauté" },
];

const TONS = [
  { value: "professionnel", label: "👔 Professionnel" },
  { value: "dynamique", label: "⚡ Dynamique" },
  { value: "emotionnel", label: "❤️ Émotionnel" },
  { value: "luxe", label: "✨ Luxe" },
];

const OBJECTIFS = [
  "Notoriété de marque",
  "Lancement produit",
  "Promotion événement",
  "Recrutement",
  "Réseaux sociaux",
  "Site web / landing page",
  "Publicité TV / YouTube",
];

const INITIAL_FORM: BriefForm = {
  client_name: "",
  client_email: "",
  client_company: "",
  client_phone: "",
  secteur: "restaurant",
  objectif: "Notoriété de marque",
  ton: "professionnel",
  produits_services: "",
  public_cible: "",
  slogan: "",
  couleurs_marque: "",
  duree_souhaitee: 30,
  exemples_references: "",
  notes_libres: "",
  nb_scenes: 5,
  musique_premium: false,
  overlay_texte: true,
  livraison_express: false,
};

// ─── Estimateur de prix ───────────────────────────────────────────────────────

function calculatePrice(
  nb_scenes: number,
  duree: number,
  musique_premium: boolean,
  overlay_texte: boolean,
  livraison_express: boolean,
) {
  let base = nb_scenes * 100;
  if (duree > 30) base += (duree - 30) * 10;
  if (musique_premium) base += 150;
  if (overlay_texte) base += 50;
  if (livraison_express) base += 200;
  return { min: base, max: Math.round(base * 1.6) };
}

function orderToBriefForm(order: VideoClientOrderFull): BriefForm {
  return {
    client_name: order.client_name,
    client_email: order.client_email,
    client_company: order.client_company ?? "",
    client_phone: order.client_phone ?? "",
    secteur: order.secteur,
    objectif: order.objectif,
    ton: order.ton,
    produits_services: order.produits_services ?? "",
    public_cible: order.public_cible ?? "",
    slogan: order.slogan ?? "",
    couleurs_marque: order.couleurs_marque ?? "",
    duree_souhaitee: order.duree_souhaitee,
    exemples_references: order.exemples_references ?? "",
    notes_libres: order.notes_libres ?? "",
    nb_scenes: order.nb_scenes,
    musique_premium: order.musique_premium,
    overlay_texte: order.overlay_texte,
    livraison_express: order.livraison_express,
  };
}

// ─── Composant principal ──────────────────────────────────────────────────────

export default function VideoClient() {
  const [tab, setTab] = useState<"nouveau" | "commandes">("nouveau");
  const [orders, setOrders] = useState<VideoClientOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [generatedScenes, setGeneratedScenes] = useState<GeneratedScenes | null>(
    null,
  );
  const [editedScenes, setEditedScenes] = useState<ClientScene[]>([]);
  const [orderId, setOrderId] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [launchLoading, setLaunchLoading] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [form, setForm] = useState<BriefForm>(INITIAL_FORM);
  const [selectedOrder, setSelectedOrder] = useState<VideoClientOrderFull | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [crmSuccess, setCrmSuccess] = useState(false);
  const [relaunchLoading, setRelaunchLoading] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [editForm, setEditForm] = useState<Partial<BriefForm>>({});
  const [backClientId, setBackClientId] = useState<string | null>(null);

  const prix = calculatePrice(
    form.nb_scenes,
    form.duree_souhaitee,
    form.musique_premium,
    form.overlay_texte,
    form.livraison_express,
  );

  const fetchOrders = async () => {
    try {
      const data = await apiClient.get<VideoClientOrder[]>("/video-client/orders");
      setOrders(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (tab === "commandes") void fetchOrders();
  }, [tab]);

  useEffect(() => {
    const prefill = sessionStorage.getItem("prefill_video_client");
    if (prefill) {
      const data = JSON.parse(prefill) as Partial<BriefForm>;
      setForm((prev) => ({ ...prev, ...data }));
      sessionStorage.removeItem("prefill_video_client");
      setTab("nouveau");
    }
  }, []);

  useEffect(() => {
    const backId = sessionStorage.getItem("video_client_back_id");
    if (backId) {
      setBackClientId(backId);
      sessionStorage.removeItem("video_client_back_id");
    }
  }, []);

  const handleChange = <K extends keyof BriefForm>(field: K, value: BriefForm[K]) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleGeneratePdf = async () => {
    if (!form.client_name || !form.client_email) {
      alert("Nom et email client requis pour générer le PDF.");
      return;
    }
    setPdfLoading(true);
    try {
      const base = resolveApiBaseUrl();
      const response = await fetch(`${base}/api/video-client/generate-pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_name: form.client_name,
          client_email: form.client_email,
          client_company: form.client_company,
          secteur: form.secteur,
        }),
      });
      if (!response.ok) throw new Error("Erreur génération PDF");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Brief_Video_${form.client_name.replace(/\s+/g, "_")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Erreur génération PDF");
    } finally {
      setPdfLoading(false);
    }
  };

  const handleGenerateScenes = async () => {
    if (!form.client_name || !form.client_email || !form.secteur) {
      alert("Nom, email et secteur requis.");
      return;
    }
    setLoading(true);
    setGeneratedScenes(null);
    setOrderId(null);
    try {
      const order = await apiClient.post<{ order_id: string }>(
        "/video-client/orders",
        form,
      );
      setOrderId(order.order_id);

      try {
        await apiClient.post(`/video-client/orders/${order.order_id}/sync-crm`, {});
      } catch (e) {
        console.warn("Sync CRM échouée silencieusement", e);
      }

      const scenes = await apiClient.post<GeneratedScenes>(
        `/video-client/orders/${order.order_id}/generate`,
        {},
      );
      setGeneratedScenes(scenes);
      setEditedScenes(scenes.scenes);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch {
      alert("Erreur génération scènes");
    } finally {
      setLoading(false);
    }
  };

  const handleLaunchKling = async () => {
    if (!orderId || !editedScenes.some((s) => s.prompt_en.trim())) return;
    setLaunchLoading(true);
    try {
      const result = await apiClient.post<{ video_project_id: string }>(
        `/video-client/orders/${orderId}/launch`,
        { scenes: editedScenes },
      );
      window.location.hash = `#/video-builder?project_id=${result.video_project_id}`;
    } catch {
      alert("Erreur lancement Kling");
    } finally {
      setLaunchLoading(false);
    }
  };

  const handleOpenDrawer = async (orderId: string) => {
    setDrawerLoading(true);
    setDrawerOpen(true);
    setEditMode(false);
    setDeleteConfirm(null);
    setCrmSuccess(false);
    try {
      const data = await apiClient.get<VideoClientOrderFull>(
        `/video-client/orders/${orderId}`,
      );
      setSelectedOrder(data);
      setEditForm(orderToBriefForm(data));
    } catch {
      alert("Erreur chargement fiche");
      setDrawerOpen(false);
    } finally {
      setDrawerLoading(false);
    }
  };

  const handleEditChange = <K extends keyof BriefForm>(field: K, value: BriefForm[K]) => {
    setEditForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveEdit = async () => {
    if (!selectedOrder) return;
    try {
      const payload: BriefForm = {
        ...orderToBriefForm(selectedOrder),
        ...editForm,
      };
      const updated = await apiClient.put<VideoClientOrderFull>(
        `/video-client/orders/${selectedOrder.id}`,
        payload,
      );
      setSelectedOrder(updated);
      setEditForm(orderToBriefForm(updated));
      setEditMode(false);
      void fetchOrders();
    } catch {
      alert("Erreur mise à jour");
    }
  };

  const handleToggleEditMode = () => {
    if (editMode && selectedOrder) {
      setEditForm(orderToBriefForm(selectedOrder));
    }
    setEditMode((prev) => !prev);
  };

  const handleDeleteOrder = async (orderId: string) => {
    try {
      await apiClient.delete(`/video-client/orders/${orderId}`);
      setOrders((prev) => prev.filter((o) => o.id !== orderId));
      setDrawerOpen(false);
      setSelectedOrder(null);
      setDeleteConfirm(null);
    } catch {
      alert("Erreur suppression");
    }
  };

  const handleSyncCrm = async (orderId: string) => {
    try {
      await apiClient.post(`/video-client/orders/${orderId}/sync-crm`, {});
      setCrmSuccess(true);
      setTimeout(() => setCrmSuccess(false), 3000);
    } catch {
      alert("Erreur sync CRM");
    }
  };

  const handleDownloadRecap = async (orderId: string, clientName: string) => {
    try {
      const baseUrl = resolveApiBaseUrl();
      const response = await fetch(
        `${baseUrl}/api/video-client/orders/${orderId}/pdf-recap`,
      );
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Recap_Video_${clientName.replace(" ", "_")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Erreur téléchargement PDF");
    }
  };

  const handleRelaunchKling = async (order: VideoClientOrderFull) => {
    if (order.video_project_id) {
      window.location.hash = `#/video-builder?project_id=${order.video_project_id}`;
      return;
    }
    if (!order.scenes_data?.length) {
      alert("Aucune scène disponible — régénère les scènes d'abord.");
      return;
    }
    setRelaunchLoading(true);
    try {
      const result = await apiClient.post<{ video_project_id: string }>(
        `/video-client/orders/${order.id}/launch`,
        { scenes: order.scenes_data },
      );
      window.location.hash = `#/video-builder?project_id=${result.video_project_id}`;
    } catch {
      alert("Erreur lancement Video Builder");
    } finally {
      setRelaunchLoading(false);
    }
  };

  const statusLabel = (status: string) => {
    const map: Record<string, { label: string; color: string }> = {
      brief_recu: { label: "Brief reçu", color: "bg-blue-500/20 text-blue-400" },
      en_generation: {
        label: "En génération",
        color: "bg-yellow-500/20 text-yellow-400",
      },
      livre: { label: "Livré", color: "bg-green-500/20 text-green-400" },
    };
    return map[status] || { label: status, color: "bg-gray-500/20 text-gray-400" };
  };

  return (
    <div className="min-h-screen bg-[#0f1117] p-6 text-white">
      {backClientId && (
        <button
          type="button"
          onClick={() => {
            sessionStorage.setItem("open_client_id", backClientId);
            window.location.hash = "#/clients";
          }}
          className="mb-4 flex items-center gap-2 text-sm text-gray-400 transition-colors hover:text-white"
        >
          ← Retour à la fiche client
        </button>
      )}

      <div className="mb-8">
        <h1 className="flex items-center gap-3 text-3xl font-bold text-white">
          🎬 <span>Vidéos Clients</span>
        </h1>
        <p className="mt-1 text-gray-400">
          Générez des vidéos publicitaires premium adaptées à chaque secteur client.
        </p>
      </div>

      <div className="mb-8 flex gap-2">
        {(
          [
            { key: "nouveau", label: "✨ Nouveau brief" },
            { key: "commandes", label: "📋 Commandes" },
          ] as const
        ).map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`rounded-lg px-5 py-2 text-sm font-medium transition-all ${
              tab === t.key
                ? "bg-[#f5c842] text-black"
                : "bg-white/5 text-gray-400 hover:bg-white/10"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "nouveau" && (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <div className="space-y-6 xl:col-span-2">
            <div className="rounded-xl border border-white/10 bg-white/5 p-6">
              <h2 className="mb-4 text-lg font-semibold text-[#f5c842]">
                👤 Identité client
              </h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {(
                  [
                    { field: "client_name", label: "Nom complet *", placeholder: "Jean Dupont" },
                    { field: "client_email", label: "Email *", placeholder: "jean@entreprise.fr" },
                    { field: "client_company", label: "Entreprise", placeholder: "CapCore Studio" },
                    { field: "client_phone", label: "Téléphone", placeholder: "+33 6 00 00 00 00" },
                  ] as const
                ).map(({ field, label, placeholder }) => (
                  <div key={field}>
                    <label className="mb-1 block text-sm text-gray-400">{label}</label>
                    <input
                      type="text"
                      value={form[field]}
                      onChange={(e) => handleChange(field, e.target.value)}
                      placeholder={placeholder}
                      className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white transition-colors focus:border-[#f5c842] focus:outline-none"
                    />
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-white/5 p-6">
              <h2 className="mb-4 text-lg font-semibold text-[#f5c842]">🎯 Brief vidéo</h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm text-gray-400">Secteur *</label>
                  <select
                    value={form.secteur}
                    onChange={(e) => handleChange("secteur", e.target.value)}
                    className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-[#f5c842] focus:outline-none"
                  >
                    {SECTEURS.map((s) => (
                      <option key={s.value} value={s.value} className="bg-[#0f1117]">
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-sm text-gray-400">Objectif *</label>
                  <select
                    value={form.objectif}
                    onChange={(e) => handleChange("objectif", e.target.value)}
                    className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-[#f5c842] focus:outline-none"
                  >
                    {OBJECTIFS.map((o) => (
                      <option key={o} value={o} className="bg-[#0f1117]">
                        {o}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="md:col-span-2">
                  <label className="mb-2 block text-sm text-gray-400">Ton souhaité *</label>
                  <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                    {TONS.map((t) => (
                      <button
                        key={t.value}
                        type="button"
                        onClick={() => handleChange("ton", t.value)}
                        className={`rounded-lg border px-3 py-2 text-sm font-medium transition-all ${
                          form.ton === t.value
                            ? "border-[#f5c842] bg-[#f5c842]/20 text-[#f5c842]"
                            : "border-white/10 bg-white/5 text-gray-400 hover:border-white/30"
                        }`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="mt-4 space-y-4">
                {(
                  [
                    {
                      field: "produits_services",
                      label: "Produits / services à mettre en avant",
                      placeholder:
                        "Notre spécialité maison, le menu dégustation 7 services...",
                    },
                    {
                      field: "public_cible",
                      label: "Public cible",
                      placeholder:
                        "Couples 30-50 ans, CSP+, amateurs de gastronomie...",
                    },
                    {
                      field: "slogan",
                      label: "Slogan / tagline",
                      placeholder: "L'excellence à chaque bouchée",
                    },
                    {
                      field: "couleurs_marque",
                      label: "Couleurs de marque",
                      placeholder: "#1a1a1a, or, blanc cassé",
                    },
                    {
                      field: "exemples_references",
                      label: "Références vidéos aimées (liens)",
                      placeholder: "https://youtube.com/...",
                    },
                  ] as const
                ).map(({ field, label, placeholder }) => (
                  <div key={field}>
                    <label className="mb-1 block text-sm text-gray-400">{label}</label>
                    <input
                      type="text"
                      value={form[field]}
                      onChange={(e) => handleChange(field, e.target.value)}
                      placeholder={placeholder}
                      className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white transition-colors focus:border-[#f5c842] focus:outline-none"
                    />
                  </div>
                ))}

                <div>
                  <label className="mb-1 block text-sm text-gray-400">
                    Notes complémentaires
                  </label>
                  <textarea
                    value={form.notes_libres}
                    onChange={(e) => handleChange("notes_libres", e.target.value)}
                    placeholder="Toute information utile pour la création..."
                    rows={3}
                    className="w-full resize-none rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white transition-colors focus:border-[#f5c842] focus:outline-none"
                  />
                </div>
              </div>
            </div>

            {generatedScenes && (
              <div className="rounded-xl border border-[#f5c842]/30 bg-white/5 p-6">
                <h2 className="mb-2 text-lg font-semibold text-[#f5c842]">
                  🎬 Scènes générées — modifiables
                </h2>
                <p className="mb-4 text-sm text-gray-400">
                  Adaptées au secteur{" "}
                  <strong className="text-white">{generatedScenes.secteur}</strong> pour{" "}
                  <strong className="text-white">{generatedScenes.client_name}</strong>.
                  Modifie chaque scène si besoin avant de lancer Kling.
                </p>
                <div className="space-y-4">
                  {editedScenes.map((scene, i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-white/10 bg-black/20 p-4"
                    >
                      <label className="mb-1 block text-xs font-medium text-[#f5c842]">
                        Scène {i + 1} — Description client (FR)
                      </label>
                      <textarea
                        value={scene.description_fr}
                        onChange={(e) => {
                          const updated = [...editedScenes];
                          updated[i] = {
                            ...updated[i],
                            description_fr: e.target.value,
                          };
                          setEditedScenes(updated);
                        }}
                        rows={2}
                        className="mb-3 w-full resize-none rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white transition-colors focus:border-[#f5c842] focus:outline-none"
                      />
                      <label className="mb-1 block text-xs text-gray-500">
                        Prompt Kling (EN)
                      </label>
                      <textarea
                        value={scene.prompt_en}
                        onChange={(e) => {
                          const updated = [...editedScenes];
                          updated[i] = {
                            ...updated[i],
                            prompt_en: e.target.value,
                          };
                          setEditedScenes(updated);
                        }}
                        rows={2}
                        className="w-full resize-none rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-gray-400 transition-colors focus:border-[#f5c842] focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => void handleLaunchKling()}
                  disabled={launchLoading || !orderId}
                  className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-[#f5c842] py-3 font-bold text-black transition-colors hover:bg-[#e5b832] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {launchLoading ? (
                    <span className="flex items-center gap-2">
                      <span className="animate-spin">⚡</span> Lancement...
                    </span>
                  ) : (
                    "🚀 Lancer la génération Kling avec ces scènes"
                  )}
                </button>
              </div>
            )}
          </div>

          <div className="space-y-6">
            <div className="rounded-xl border border-white/10 bg-white/5 p-6">
              <h2 className="mb-4 text-lg font-semibold text-[#f5c842]">⚙️ Options</h2>
              <div className="space-y-4">
                <div>
                  <label className="mb-2 block text-sm text-gray-400">
                    Nombre de scènes —{" "}
                    <span className="font-medium text-white">{form.nb_scenes}</span>
                  </label>
                  <input
                    type="range"
                    min={3}
                    max={10}
                    value={form.nb_scenes}
                    onChange={(e) => handleChange("nb_scenes", Number(e.target.value))}
                    className="w-full accent-[#f5c842]"
                  />
                  <div className="mt-1 flex justify-between text-xs text-gray-500">
                    <span>3</span>
                    <span>10</span>
                  </div>
                </div>

                <div>
                  <label className="mb-2 block text-sm text-gray-400">
                    Durée —{" "}
                    <span className="font-medium text-white">{form.duree_souhaitee}s</span>
                  </label>
                  <div className="grid grid-cols-4 gap-1">
                    {[15, 30, 45, 60].map((d) => (
                      <button
                        key={d}
                        type="button"
                        onClick={() => handleChange("duree_souhaitee", d)}
                        className={`rounded-lg border py-2 text-sm transition-all ${
                          form.duree_souhaitee === d
                            ? "border-[#f5c842] bg-[#f5c842]/20 text-[#f5c842]"
                            : "border-white/10 bg-white/5 text-gray-400"
                        }`}
                      >
                        {d}s
                      </button>
                    ))}
                  </div>
                </div>

                {(
                  [
                    { field: "musique_premium", label: "Musique premium", detail: "+150€" },
                    { field: "overlay_texte", label: "Overlay texte", detail: "+50€" },
                    { field: "livraison_express", label: "Livraison express", detail: "+200€" },
                  ] as const
                ).map(({ field, label, detail }) => (
                  <div key={field} className="flex items-center justify-between">
                    <div>
                      <span className="text-sm text-white">{label}</span>
                      <span className="ml-2 text-xs text-gray-500">{detail}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleChange(field, !form[field])}
                      className={`relative h-6 w-12 rounded-full transition-all ${
                        form[field] ? "bg-[#f5c842]" : "bg-white/20"
                      }`}
                    >
                      <span
                        className={`absolute top-1 h-4 w-4 rounded-full bg-white transition-all ${
                          form[field] ? "left-7" : "left-1"
                        }`}
                      />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-[#f5c842]/30 bg-[#f5c842]/10 p-6">
              <h2 className="mb-4 text-lg font-semibold text-[#f5c842]">
                💰 Estimation de prix
              </h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between text-gray-400">
                  <span>{form.nb_scenes} scènes × 100€</span>
                  <span>{form.nb_scenes * 100}€</span>
                </div>
                {form.duree_souhaitee > 30 && (
                  <div className="flex justify-between text-gray-400">
                    <span>Durée supplémentaire</span>
                    <span>+{(form.duree_souhaitee - 30) * 10}€</span>
                  </div>
                )}
                {form.musique_premium && (
                  <div className="flex justify-between text-gray-400">
                    <span>Musique premium</span>
                    <span>+150€</span>
                  </div>
                )}
                {form.overlay_texte && (
                  <div className="flex justify-between text-gray-400">
                    <span>Overlay texte</span>
                    <span>+50€</span>
                  </div>
                )}
                {form.livraison_express && (
                  <div className="flex justify-between text-gray-400">
                    <span>Livraison express</span>
                    <span>+200€</span>
                  </div>
                )}
                <div className="mt-2 border-t border-[#f5c842]/30 pt-3">
                  <div className="flex justify-between">
                    <span className="text-lg font-bold text-white">Total estimé</span>
                    <span className="text-lg font-bold text-[#f5c842]">
                      {prix.min}€ – {prix.max}€
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <button
                type="button"
                onClick={() => void handleGeneratePdf()}
                disabled={pdfLoading}
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-white/20 bg-white/10 py-3 font-medium text-white transition-colors hover:bg-white/20"
              >
                {pdfLoading ? "Génération..." : "📄 Télécharger PDF brief"}
              </button>

              <button
                type="button"
                onClick={() => void handleGenerateScenes()}
                disabled={loading}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#f5c842] py-3 font-bold text-black transition-colors hover:bg-[#e5b832]"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="animate-spin">⚡</span> Génération en cours...
                  </span>
                ) : (
                  "🎬 Générer les scènes"
                )}
              </button>

              {saveSuccess && (
                <div className="rounded-lg border border-green-500/30 bg-green-500/20 p-3 text-center text-sm text-green-400">
                  ✅ Brief sauvegardé — scènes prêtes à éditer
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {tab === "commandes" && (
        <div className="space-y-3">
          {orders.length === 0 ? (
            <div className="py-16 text-center text-gray-500">
              Aucune commande client pour l&apos;instant.
            </div>
          ) : (
            orders.map((order) => {
              const s = statusLabel(order.status);
              return (
                <div
                  key={order.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => void handleOpenDrawer(order.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      void handleOpenDrawer(order.id);
                    }
                  }}
                  className="group flex cursor-pointer items-center justify-between rounded-xl border border-white/10 bg-white/5 p-5 transition-all hover:border-[#f5c842]/40 hover:bg-white/[0.08]"
                >
                  <div>
                    <div className="mb-1 flex items-center gap-3">
                      <span className="font-semibold text-white transition-colors group-hover:text-[#f5c842]">
                        {order.client_name}
                      </span>
                      <span className={`rounded-full px-2 py-0.5 text-xs ${s.color}`}>
                        {s.label}
                      </span>
                    </div>
                    <div className="text-sm text-gray-400">
                      {order.client_email} ·{" "}
                      {SECTEURS.find((s) => s.value === order.secteur)?.label ||
                        order.secteur}
                    </div>
                    <div className="mt-1 text-xs text-gray-500">
                      {new Date(order.created_at).toLocaleDateString("fr-FR")}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-[#f5c842]">
                      {order.prix_estime_min}€ – {order.prix_estime_max}€
                    </div>
                    <div className="mt-1 text-xs text-gray-500">{order.objectif}</div>
                    <div className="mt-1 text-xs text-gray-600 transition-colors group-hover:text-gray-400">
                      → Voir la fiche
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {drawerOpen && (
        <div className="fixed inset-0 z-50 flex">
          <div
            className="flex-1 bg-black/60 backdrop-blur-sm"
            onClick={() => setDrawerOpen(false)}
            aria-hidden
          />
          <div className="flex w-full max-w-lg flex-col overflow-y-auto border-l border-white/10 bg-[#0f1117]">
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-white/10 bg-[#0f1117] p-6">
              <div>
                <h2 className="text-xl font-bold text-white">
                  {drawerLoading ? "Chargement..." : selectedOrder?.client_name}
                </h2>
                {selectedOrder && (
                  <p className="mt-0.5 text-sm text-gray-400">
                    {selectedOrder.client_company && `${selectedOrder.client_company} · `}
                    {selectedOrder.client_email}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {selectedOrder && !drawerLoading && (
                  <button
                    type="button"
                    onClick={handleToggleEditMode}
                    className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${
                      editMode
                        ? "border-white/20 bg-white/10 text-white"
                        : "border-[#f5c842]/30 bg-[#f5c842]/10 text-[#f5c842]"
                    }`}
                  >
                    {editMode ? "✕ Annuler" : "✏️ Modifier"}
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setDrawerOpen(false)}
                  className="ml-2 text-2xl text-gray-400 transition-colors hover:text-white"
                >
                  ✕
                </button>
              </div>
            </div>

            {drawerLoading ? (
              <div className="flex flex-1 items-center justify-center text-gray-500">
                <span className="mr-2 animate-spin">⚡</span> Chargement...
              </div>
            ) : selectedOrder ? (
              <div className="flex-1 space-y-6 p-6">
                <div className="flex items-center justify-between">
                  <span
                    className={`rounded-full px-3 py-1 text-sm ${statusLabel(selectedOrder.status).color}`}
                  >
                    {statusLabel(selectedOrder.status).label}
                  </span>
                  <span className="text-lg font-bold text-[#f5c842]">
                    {selectedOrder.prix_estime_min}€ – {selectedOrder.prix_estime_max}€
                  </span>
                </div>

                <div className="space-y-3 rounded-xl border border-white/10 bg-white/5 p-4">
                  <h3 className="mb-2 text-sm font-semibold text-[#f5c842]">🎯 Brief</h3>

                  {editMode ? (
                    <div className="space-y-3">
                      {(
                        [
                          { field: "client_name", label: "Nom complet" },
                          { field: "client_email", label: "Email" },
                          { field: "client_company", label: "Entreprise" },
                          { field: "client_phone", label: "Téléphone" },
                          { field: "produits_services", label: "Produits / services" },
                          { field: "public_cible", label: "Public cible" },
                          { field: "slogan", label: "Slogan" },
                          { field: "couleurs_marque", label: "Couleurs de marque" },
                          { field: "exemples_references", label: "Références vidéos" },
                        ] as const
                      ).map(({ field, label }) => (
                        <div key={field}>
                          <label className="mb-1 block text-xs text-gray-500">{label}</label>
                          <input
                            type="text"
                            value={editForm[field] ?? ""}
                            onChange={(e) => handleEditChange(field, e.target.value)}
                            className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white transition-colors focus:border-[#f5c842] focus:outline-none"
                          />
                        </div>
                      ))}

                      <div>
                        <label className="mb-1 block text-xs text-gray-500">Secteur</label>
                        <select
                          value={editForm.secteur ?? selectedOrder.secteur}
                          onChange={(e) => handleEditChange("secteur", e.target.value)}
                          className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white focus:border-[#f5c842] focus:outline-none"
                        >
                          {SECTEURS.map((s) => (
                            <option key={s.value} value={s.value} className="bg-[#0f1117]">
                              {s.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="mb-1 block text-xs text-gray-500">Ton</label>
                        <div className="grid grid-cols-2 gap-1">
                          {TONS.map((t) => (
                            <button
                              key={t.value}
                              type="button"
                              onClick={() => handleEditChange("ton", t.value)}
                              className={`rounded-lg border px-2 py-2 text-xs font-medium transition-all ${
                                (editForm.ton ?? selectedOrder.ton) === t.value
                                  ? "border-[#f5c842] bg-[#f5c842]/20 text-[#f5c842]"
                                  : "border-white/10 bg-white/5 text-gray-400"
                              }`}
                            >
                              {t.label}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div>
                        <label className="mb-1 block text-xs text-gray-500">
                          Notes complémentaires
                        </label>
                        <textarea
                          value={editForm.notes_libres ?? ""}
                          onChange={(e) => handleEditChange("notes_libres", e.target.value)}
                          rows={3}
                          className="w-full resize-none rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-white transition-colors focus:border-[#f5c842] focus:outline-none"
                        />
                      </div>

                      <button
                        type="button"
                        onClick={() => void handleSaveEdit()}
                        className="w-full rounded-lg bg-[#f5c842] py-3 font-bold text-black transition-colors hover:bg-[#e5b832]"
                      >
                        💾 Sauvegarder les modifications
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {[
                        {
                          label: "Secteur",
                          value: SECTEURS.find((s) => s.value === selectedOrder.secteur)?.label,
                        },
                        { label: "Objectif", value: selectedOrder.objectif },
                        {
                          label: "Ton",
                          value: TONS.find((t) => t.value === selectedOrder.ton)?.label,
                        },
                        { label: "Produits / services", value: selectedOrder.produits_services },
                        { label: "Public cible", value: selectedOrder.public_cible },
                        { label: "Slogan", value: selectedOrder.slogan },
                        { label: "Couleurs", value: selectedOrder.couleurs_marque },
                        { label: "Durée", value: `${selectedOrder.duree_souhaitee}s` },
                        { label: "Nb scènes", value: selectedOrder.nb_scenes },
                        { label: "Références", value: selectedOrder.exemples_references },
                        { label: "Notes", value: selectedOrder.notes_libres },
                      ]
                        .filter((f) => f.value)
                        .map(({ label, value }) => (
                          <div key={label} className="flex gap-3 text-sm">
                            <span className="w-32 shrink-0 text-gray-500">{label}</span>
                            <span className="text-white">{String(value)}</span>
                          </div>
                        ))}
                    </div>
                  )}
                </div>

                <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                  <h3 className="mb-3 text-sm font-semibold text-[#f5c842]">⚙️ Options</h3>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    {[
                      { label: "Musique premium", value: selectedOrder.musique_premium },
                      { label: "Overlay texte", value: selectedOrder.overlay_texte },
                      { label: "Express", value: selectedOrder.livraison_express },
                    ].map(({ label, value }) => (
                      <div
                        key={label}
                        className={`rounded-lg py-2 text-center text-xs ${
                          value
                            ? "bg-[#f5c842]/20 text-[#f5c842]"
                            : "bg-white/5 text-gray-500"
                        }`}
                      >
                        {value ? "✓" : "✗"} {label}
                      </div>
                    ))}
                  </div>
                </div>

                {selectedOrder.scenes_data && selectedOrder.scenes_data.length > 0 && (
                  <div className="rounded-xl border border-white/10 bg-white/5 p-4">
                    <h3 className="mb-3 text-sm font-semibold text-[#f5c842]">
                      🎬 Scènes générées ({selectedOrder.scenes_data.length})
                    </h3>
                    <div className="space-y-2">
                      {selectedOrder.scenes_data.map((scene, i) => (
                        <div
                          key={i}
                          className="rounded-lg border border-white/5 bg-black/30 p-3 text-xs"
                        >
                          <div className="mb-1 text-gray-400">Scène {i + 1}</div>
                          <div className="text-white">
                            {typeof scene === "string"
                              ? scene
                              : scene.description_fr || scene.prompt_en}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="space-y-2 pt-2">
                  <button
                    type="button"
                    onClick={() => void handleRelaunchKling(selectedOrder)}
                    disabled={relaunchLoading}
                    className="w-full rounded-lg bg-[#f5c842] py-3 font-bold text-black transition-colors hover:bg-[#e5b832] disabled:opacity-50"
                  >
                    {relaunchLoading
                      ? "⚡ Lancement..."
                      : "🚀 Relancer dans le Video Builder"}
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      void handleDownloadRecap(selectedOrder.id, selectedOrder.client_name)
                    }
                    className="w-full rounded-lg border border-white/20 bg-white/10 py-3 font-medium text-white transition-colors hover:bg-white/20"
                  >
                    📄 Télécharger la fiche + estimation prix
                  </button>

                  <button
                    type="button"
                    onClick={() => void handleSyncCrm(selectedOrder.id)}
                    className="w-full rounded-lg border border-white/20 bg-white/10 py-3 font-medium text-white transition-colors hover:bg-white/20"
                  >
                    👥 Ajouter à mes clients CyberForge
                  </button>
                  {crmSuccess && (
                    <div className="rounded-lg border border-green-500/30 bg-green-500/20 p-2 text-center text-xs text-green-400">
                      ✅ Client synchronisé dans le CRM
                    </div>
                  )}

                  {deleteConfirm === selectedOrder.id ? (
                    <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3">
                      <p className="mb-2 text-center text-sm text-red-400">
                        Confirmer la suppression ?
                      </p>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => void handleDeleteOrder(selectedOrder.id)}
                          className="flex-1 rounded-lg bg-red-500 py-2 text-sm font-medium text-white transition-colors hover:bg-red-600"
                        >
                          Supprimer
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeleteConfirm(null)}
                          className="flex-1 rounded-lg bg-white/10 py-2 text-sm font-medium text-white transition-colors hover:bg-white/20"
                        >
                          Annuler
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setDeleteConfirm(selectedOrder.id)}
                      className="w-full rounded-lg border border-red-500/20 bg-red-500/10 py-3 text-sm font-medium text-red-400 transition-colors hover:bg-red-500/20"
                    >
                      🗑️ Supprimer cette fiche
                    </button>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

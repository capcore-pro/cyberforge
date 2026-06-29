import { useState, useEffect, useRef, useCallback } from "react";
import type { Client, Site } from "../App";
import {
  getMyFeatures,
  delegateToCapcore,
  sendModificationRequest,
  fetchPortalMedia,
  uploadPortalMedia,
  deletePortalMedia,
  type ClientFeatures,
  type MediaItem,
} from "../lib/portal-api";
import { openCustomerPortal } from "../lib/stripe-api";

const PLAN_LABELS: Record<string, string> = {
  trial: "Essai gratuit",
  essentiel: "Essentiel",
  business: "Business",
  studio: "Studio",
  none: "Aucun plan",
};

const PLAN_COLORS: Record<string, string> = {
  trial: "#f59e0b",
  essentiel: "#6366f1",
  business: "#06b6d4",
  studio: "#8b5cf6",
  none: "#6b7280",
};

const TYPE_MODIFICATIONS = [
  "Modification de texte",
  "Remplacement de photo",
  "Ajout de contenu",
  "Modification couleurs",
  "Changement de section",
  "Autre",
];

const MAX_MEDIA_BYTES = 5 * 1024 * 1024;

function formatMediaSize(bytes: number | null): string {
  if (bytes == null) return "";
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

interface DashboardProps {
  client: Client;
  sites: Site[];
  onEdit: (site: Site) => void;
  onLogout: () => void;
  onClientUpdate: (client: Client) => void;
}

export default function Dashboard({
  client,
  sites,
  onEdit,
  onLogout,
  onClientUpdate,
}: DashboardProps) {
  const [features, setFeatures] = useState<ClientFeatures | null>(null);
  const [showDelegateConfirm, setShowDelegateConfirm] = useState(false);
  const [delegating, setDelegating] = useState(false);
  const [showModifForm, setShowModifForm] = useState(false);
  const [modifSiteId, setModifSiteId] = useState(sites[0]?.id || "");
  const [modifType, setModifType] = useState(TYPE_MODIFICATIONS[0]);
  const [modifDesc, setModifDesc] = useState("");
  const [modifPriorite, setModifPriorite] = useState<"normale" | "urgente">(
    "normale",
  );
  const [modifSending, setModifSending] = useState(false);
  const [modifSent, setModifSent] = useState(false);
  const [mediaList, setMediaList] = useState<MediaItem[]>([]);
  const [mediaCount, setMediaCount] = useState(0);
  const [mediaLimit, setMediaLimit] = useState(10);
  const [mediaUploading, setMediaUploading] = useState(false);
  const [mediaError, setMediaError] = useState<string | null>(null);
  const [mediaDragOver, setMediaDragOver] = useState(false);
  const [copiedMediaId, setCopiedMediaId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isGere = client.management_plan === "gere";
  const planLabel = PLAN_LABELS[client.plan] || client.plan;
  const planColor = PLAN_COLORS[client.plan] || "#6b7280";

  useEffect(() => {
    if (!isGere) {
      void getMyFeatures(client.id).then(setFeatures);
    }
  }, [client.id, isGere]);

  const loadMedia = useCallback(async () => {
    if (!client.id || isGere) return;
    try {
      const data = await fetchPortalMedia(client.id);
      setMediaList(data.media);
      setMediaCount(data.count);
      setMediaLimit(data.limit);
    } catch {
      /* ignore */
    }
  }, [client.id, isGere]);

  useEffect(() => {
    void loadMedia();
  }, [loadMedia]);

  const handleMediaFile = async (file: File | null | undefined) => {
    if (!file || mediaUploading) return;
    setMediaError(null);

    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setMediaError("Format non supporté — JPEG, PNG ou WebP uniquement");
      return;
    }
    if (file.size > MAX_MEDIA_BYTES) {
      setMediaError("Fichier trop lourd — maximum 5Mo");
      return;
    }

    setMediaUploading(true);
    try {
      await uploadPortalMedia(client.id, file, sites[0]?.id);
      await loadMedia();
    } catch (err) {
      setMediaError(err instanceof Error ? err.message : "Erreur upload photo");
    } finally {
      setMediaUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDeleteMedia = async (mediaId: string) => {
    if (!window.confirm("Supprimer cette photo ?")) return;
    setMediaError(null);
    try {
      await deletePortalMedia(mediaId);
      await loadMedia();
    } catch (err) {
      setMediaError(
        err instanceof Error ? err.message : "Erreur suppression photo",
      );
    }
  };

  const handleCopyMediaUrl = async (item: MediaItem) => {
    try {
      await navigator.clipboard.writeText(item.r2_url);
      setCopiedMediaId(item.id);
      window.setTimeout(() => setCopiedMediaId(null), 2000);
    } catch {
      setMediaError("Impossible de copier l'URL");
    }
  };

  const isStudioPlan = client.plan === "studio";
  const mediaAtLimit = !isStudioPlan && mediaCount >= mediaLimit;
  const mediaProgressPct = isStudioPlan
    ? 0
    : Math.min(100, (mediaCount / Math.max(mediaLimit, 1)) * 100);

  const handleDelegate = async () => {
    if (!sites[0]) return;
    setDelegating(true);
    const res = await delegateToCapcore(client.id, sites[0].id);
    if (res.success) {
      onClientUpdate({ ...client, management_plan: "gere", plan: "none" });
    }
    setDelegating(false);
    setShowDelegateConfirm(false);
  };

  const handleModifSubmit = async () => {
    if (!modifDesc.trim()) return;
    setModifSending(true);
    const res = await sendModificationRequest({
      client_id: client.id,
      site_id: modifSiteId,
      type_modification: modifType,
      description: modifDesc,
      priorite: modifPriorite,
    });
    if (res.success) {
      setModifSent(true);
      setModifDesc("");
      setTimeout(() => {
        setModifSent(false);
        setShowModifForm(false);
      }, 3000);
    }
    setModifSending(false);
  };

  return (
    <div className="min-h-screen bg-[#0f0f13] text-white">
      <div className="border-b border-white/10 px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-medium">
            Bonjour, {client.full_name.split(" ")[0]} 👋
          </h1>
          <div className="flex items-center gap-2 mt-1">
            <span
              className="text-xs px-2 py-0.5 rounded-full font-medium"
              style={{ background: planColor + "22", color: planColor }}
            >
              {isGere ? "🛠️ Géré par CapCore" : planLabel}
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={onLogout}
          className="text-sm text-white/40 hover:text-white transition-colors"
        >
          Déconnexion
        </button>
      </div>

      <div className="max-w-3xl mx-auto px-6 py-8 space-y-8">
        {isGere && (
          <div className="space-y-4">
            <div className="bg-cyan-400/5 border border-cyan-400/20 rounded-xl p-5">
              <h2 className="text-sm font-medium text-cyan-400 mb-1">
                🛠️ Votre site est géré par CapCore
              </h2>
              <p className="text-sm text-white/50">
                Mat s&apos;occupe de toutes les modifications. Utilisez le
                formulaire ci-dessous pour soumettre vos demandes.
              </p>
            </div>

            {!showModifForm ? (
              <button
                type="button"
                onClick={() => setShowModifForm(true)}
                className="w-full py-3 rounded-xl bg-cyan-400 text-black font-medium hover:bg-cyan-300 transition-colors"
              >
                📝 Demander une modification
              </button>
            ) : (
              <div className="bg-white/5 border border-white/10 rounded-xl p-5 space-y-4">
                <h3 className="text-sm font-medium text-white">
                  Nouvelle demande
                </h3>

                {sites.length > 1 && (
                  <div>
                    <label className="block text-xs text-white/50 mb-1">
                      Site concerné
                    </label>
                    <select
                      value={modifSiteId}
                      onChange={(e) => setModifSiteId(e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-400"
                    >
                      {sites.map((s) => (
                        <option
                          key={s.id}
                          value={s.id}
                          className="bg-[#0f0f13]"
                        >
                          {s.site_name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div>
                  <label className="block text-xs text-white/50 mb-1">
                    Type de modification
                  </label>
                  <select
                    value={modifType}
                    onChange={(e) => setModifType(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-400"
                  >
                    {TYPE_MODIFICATIONS.map((t) => (
                      <option key={t} value={t} className="bg-[#0f0f13]">
                        {t}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs text-white/50 mb-1">
                    Description détaillée
                  </label>
                  <textarea
                    value={modifDesc}
                    onChange={(e) => setModifDesc(e.target.value)}
                    placeholder="Décrivez précisément ce que vous souhaitez modifier..."
                    rows={4}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-white/20 focus:outline-none focus:border-cyan-400 resize-none"
                  />
                </div>

                <div>
                  <label className="block text-xs text-white/50 mb-2">
                    Priorité
                  </label>
                  <div className="flex gap-2">
                    {(["normale", "urgente"] as const).map((p) => (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setModifPriorite(p)}
                        className={`flex-1 py-2 rounded-lg text-sm transition-colors capitalize ${
                          modifPriorite === p
                            ? p === "urgente"
                              ? "bg-red-500 text-white"
                              : "bg-cyan-400 text-black"
                            : "bg-white/5 text-white/50 hover:text-white"
                        }`}
                      >
                        {p === "urgente" ? "🔴 Urgente" : "🔵 Normale"}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => void handleModifSubmit()}
                    disabled={modifSending || !modifDesc.trim()}
                    className="flex-1 py-2.5 rounded-lg bg-cyan-400 text-black font-medium text-sm hover:bg-cyan-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    {modifSent
                      ? "✅ Envoyé !"
                      : modifSending
                        ? "Envoi..."
                        : "Envoyer la demande"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowModifForm(false)}
                    className="px-4 py-2.5 rounded-lg bg-white/5 text-white/50 text-sm hover:text-white transition-colors"
                  >
                    Annuler
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {!isGere && (
          <div>
            <h2 className="text-sm font-medium text-white/60 mb-3">
              Mes sites ({sites.length})
            </h2>
            <div className="space-y-3">
              {sites.map((site) => (
                <div
                  key={site.id}
                  className="bg-white/5 border border-white/10 rounded-xl p-4 flex items-center justify-between"
                >
                  <div>
                    <p className="text-sm font-medium text-white">
                      {site.site_name}
                    </p>
                    {site.site_url ? (
                      <a
                        href={site.site_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-cyan-400 hover:underline"
                      >
                        {site.site_url}
                      </a>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    onClick={() => onEdit(site)}
                    className="px-4 py-2 rounded-lg bg-cyan-400 text-black text-sm font-medium hover:bg-cyan-300 transition-colors"
                  >
                    ✏️ Modifier
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {!isGere && (
          <div className="border border-white/10 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-medium text-white">📸 Mes photos</h2>
              {isStudioPlan ? (
                <span className="text-xs text-cyan-400">Illimité</span>
              ) : (
                <span className="text-xs text-white/50">
                  {mediaCount} / {mediaLimit} photos utilisées
                </span>
              )}
            </div>

            {!isStudioPlan && (
              <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full rounded-full bg-cyan-400 transition-all"
                  style={{ width: `${mediaProgressPct}%` }}
                />
              </div>
            )}

            <div
              role="button"
              tabIndex={0}
              onClick={() => !mediaAtLimit && fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  if (!mediaAtLimit) fileInputRef.current?.click();
                }
              }}
              onDragOver={(e) => {
                e.preventDefault();
                if (!mediaAtLimit) setMediaDragOver(true);
              }}
              onDragLeave={() => setMediaDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setMediaDragOver(false);
                if (mediaAtLimit) return;
                void handleMediaFile(e.dataTransfer.files[0]);
              }}
              className={`rounded-xl border border-dashed p-6 text-center transition-colors ${
                mediaAtLimit
                  ? "border-white/10 bg-white/3 opacity-50 cursor-not-allowed"
                  : mediaDragOver
                    ? "border-cyan-400/60 bg-cyan-400/5 cursor-pointer"
                    : "border-white/20 bg-white/3 hover:border-white/30 cursor-pointer"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                disabled={mediaAtLimit || mediaUploading}
                onChange={(e) => void handleMediaFile(e.target.files?.[0])}
              />
              <p className="text-sm text-white/70">
                {mediaUploading
                  ? "Envoi en cours..."
                  : mediaAtLimit
                    ? "Limite atteinte — passez au forfait supérieur"
                    : "Glissez une photo ici ou cliquez pour parcourir"}
              </p>
              <p className="text-xs text-white/30 mt-1">
                JPEG, PNG ou WebP — max 5 Mo
              </p>
            </div>

            {mediaError ? (
              <p className="text-xs text-red-400">{mediaError}</p>
            ) : null}

            {mediaList.length > 0 ? (
              <div className="grid grid-cols-3 gap-3">
                {mediaList.map((item) => (
                  <div key={item.id} className="group">
                    <div className="relative aspect-square rounded-lg overflow-hidden bg-white/5 border border-white/10">
                      <img
                        src={item.r2_url}
                        alt={item.file_name}
                        className="w-full h-full object-cover"
                      />
                      <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                        <button
                          type="button"
                          onClick={() => void handleCopyMediaUrl(item)}
                          className="px-2 py-1 rounded-md bg-white/10 text-white text-xs hover:bg-white/20 transition-colors"
                        >
                          {copiedMediaId === item.id ? "Copié ✓" : "Copier URL"}
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleDeleteMedia(item.id)}
                          className="px-2 py-1 rounded-md bg-red-500/20 text-red-300 text-xs hover:bg-red-500/30 transition-colors"
                          aria-label="Supprimer"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                    <p className="text-[10px] text-white/30 mt-1 truncate">
                      {formatMediaSize(item.file_size_bytes)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-white/30 text-center">
                Aucune photo pour le moment
              </p>
            )}
          </div>
        )}

        {!isGere && features && (
          <div className="bg-white/3 border border-white/5 rounded-xl p-4">
            <p className="text-xs text-white/40 mb-3 uppercase tracking-wide">
              Fonctionnalités de votre plan
            </p>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Couleurs", ok: features.can_edit_colors },
                { label: "Fonts", ok: features.can_edit_fonts },
                { label: "Sections", ok: features.can_edit_sections },
              ].map((f) => (
                <div
                  key={f.label}
                  className={`text-center p-2 rounded-lg text-xs ${
                    f.ok
                      ? "bg-cyan-400/10 text-cyan-400"
                      : "bg-white/3 text-white/20"
                  }`}
                >
                  {f.ok ? "✅" : "🔒"} {f.label}
                </div>
              ))}
            </div>
            {(!features.can_edit_colors || !features.can_edit_fonts) && (
              <button
                type="button"
                onClick={() =>
                  void openCustomerPortal(client.id).then((url) =>
                    window.open(url, "_blank"),
                  )
                }
                className="w-full mt-3 py-2 rounded-lg bg-white/5 text-white/50 text-xs hover:bg-white/10 hover:text-white transition-colors"
              >
                Upgrader mon plan →
              </button>
            )}
          </div>
        )}

        {!isGere && sites.length > 0 && (
          <div className="border border-white/10 rounded-xl p-5">
            <h3 className="text-sm font-medium text-white mb-1">
              Déléguer la gestion à CapCore
            </h3>
            <p className="text-xs text-white/40 mb-4">
              Mat gère votre site à votre place — 2 modifications par mois
              incluses — 49€/mois. Votre abonnement actuel sera annulé
              automatiquement.
            </p>
            {!showDelegateConfirm ? (
              <button
                type="button"
                onClick={() => setShowDelegateConfirm(true)}
                className="px-4 py-2 rounded-lg bg-white/5 text-white/60 text-sm hover:bg-white/10 hover:text-white transition-colors"
              >
                🛠️ Déléguer à CapCore
              </button>
            ) : (
              <div className="bg-amber-400/10 border border-amber-400/20 rounded-lg p-4 space-y-3">
                <p className="text-sm text-amber-400">
                  ⚠️ Votre abonnement Stripe actuel sera annulé. Vous passerez à
                  49€/mois en gestion déléguée. Confirmer ?
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => void handleDelegate()}
                    disabled={delegating}
                    className="flex-1 py-2 rounded-lg bg-amber-400 text-black text-sm font-medium hover:bg-amber-300 disabled:opacity-40 transition-colors"
                  >
                    {delegating ? "En cours..." : "Confirmer"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowDelegateConfirm(false)}
                    className="flex-1 py-2 rounded-lg bg-white/5 text-white/50 text-sm hover:text-white transition-colors"
                  >
                    Annuler
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

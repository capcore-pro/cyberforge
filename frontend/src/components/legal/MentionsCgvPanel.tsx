import { useState } from "react";
import type { ProjectRecord } from "@shared/types";
import {
  GLASS_SECTION,
  GOLD_BTN,
  SELECT,
  logAccountingApiError,
  shouldSilenceApiError,
} from "@/components/accounting/accounting-theme";
import { AccountingToast } from "@/components/accounting/AccountingToast";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  fetchProjectsForLegal,
  generateMentionsLegales,
  generateOrGetCgv,
  resolveLegalUrl,
} from "@/lib/legal-api";

export function MentionsCgvPanel() {
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [mentionsBusy, setMentionsBusy] = useState(false);
  const [cgvBusy, setCgvBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [lastPdfUrl, setLastPdfUrl] = useState<string | null>(null);

  async function ensureProjects() {
    if (projects.length) return;
    const res = await fetchProjectsForLegal();
    if (res.ok && Array.isArray(res.data)) {
      setProjects(res.data);
      if (!selectedProjectId && res.data[0]) {
        setSelectedProjectId(res.data[0].id);
      }
    }
  }

  async function handleMentions() {
    if (!selectedProjectId) {
      setToast("Sélectionnez un projet.");
      return;
    }
    setMentionsBusy(true);
    const res = await generateMentionsLegales(selectedProjectId);
    setMentionsBusy(false);
    if (!res.ok) {
      const msg = apiErrorMessage(res, "Génération des mentions légales impossible.");
      if (shouldSilenceApiError(msg)) logAccountingApiError("Mentions légales", msg);
      else setToast(msg);
      return;
    }
    const url = resolveLegalUrl(res.data?.pdf_url ?? "");
    setLastPdfUrl(url);
    window.open(url, "_blank", "noopener,noreferrer");
  }

  async function handleCgv() {
    setCgvBusy(true);
    const res = await generateOrGetCgv();
    setCgvBusy(false);
    if (!res.ok) {
      const msg = apiErrorMessage(res, "Génération des CGV impossible.");
      if (shouldSilenceApiError(msg)) logAccountingApiError("CGV", msg);
      else setToast(msg);
      return;
    }
    const url = resolveLegalUrl(res.data?.pdf_url ?? "");
    setLastPdfUrl(url);
    window.open(url, "_blank", "noopener,noreferrer");
  }

  return (
    <div className="max-w-xl space-y-6">
      <p className="text-sm text-white/50">
        Générez les documents juridiques standards pour vos livrables web. Les PDF
        sont enregistrés sur le serveur et ouverts dans un nouvel onglet.
      </p>

      <div className={`${GLASS_SECTION} space-y-4`}>
        <h3 className="text-xs font-semibold uppercase tracking-widest text-[#d4a843]">
          Mentions légales
        </h3>
        <p className="text-xs text-white/50">
          Éditeur, hébergeur (Vercel / Railway selon le type de projet), SIRET et
          contact.
        </p>
        <select
          className={SELECT}
          value={selectedProjectId}
          onFocus={() => void ensureProjects()}
          onChange={(e) => setSelectedProjectId(e.target.value)}
        >
          <option value="">— Projet CyberForge —</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.title}
            </option>
          ))}
        </select>
        <button
          type="button"
          className={GOLD_BTN}
          disabled={mentionsBusy}
          onClick={() => void handleMentions()}
        >
          {mentionsBusy ? "Génération…" : "Générer mentions légales"}
        </button>
      </div>

      <div className={`${GLASS_SECTION} space-y-4`}>
        <h3 className="text-xs font-semibold uppercase tracking-widest text-[#d4a843]">
          CGV
        </h3>
        <p className="text-xs text-white/50">
          Conditions générales de vente globales (micro-entrepreneur prestataire
          digital). Un seul document CGV est conservé.
        </p>
        <button
          type="button"
          className={GOLD_BTN}
          disabled={cgvBusy}
          onClick={() => void handleCgv()}
        >
          {cgvBusy ? "Génération…" : "Générer / télécharger les CGV"}
        </button>
      </div>

      {lastPdfUrl ? (
        <p className="text-xs text-white/45">
          Dernier PDF :{" "}
          <a
            href={lastPdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#d4a843] hover:underline"
          >
            ouvrir
          </a>
        </p>
      ) : null}

      <AccountingToast message={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}

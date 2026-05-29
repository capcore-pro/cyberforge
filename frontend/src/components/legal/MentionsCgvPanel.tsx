import { useState } from "react";
import type { ProjectRecord } from "@shared/types";
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
  const [error, setError] = useState<string | null>(null);
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
      setError("Sélectionnez un projet.");
      return;
    }
    setMentionsBusy(true);
    setError(null);
    const res = await generateMentionsLegales(selectedProjectId);
    setMentionsBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Génération des mentions légales impossible."));
      return;
    }
    const url = resolveLegalUrl(res.data?.pdf_url ?? "");
    setLastPdfUrl(url);
    window.open(url, "_blank", "noopener,noreferrer");
  }

  async function handleCgv() {
    setCgvBusy(true);
    setError(null);
    const res = await generateOrGetCgv();
    setCgvBusy(false);
    if (!res.ok) {
      setError(apiErrorMessage(res, "Génération des CGV impossible."));
      return;
    }
    const url = resolveLegalUrl(res.data?.pdf_url ?? "");
    setLastPdfUrl(url);
    window.open(url, "_blank", "noopener,noreferrer");
  }

  return (
    <div className="max-w-xl space-y-6">
      <p className="text-sm text-cyber-muted">
        Générez les documents juridiques standards pour vos livrables web. Les PDF
        sont enregistrés sur le serveur et ouverts dans un nouvel onglet.
      </p>

      {error ? (
        <p className="rounded border border-red-500/40 bg-red-950/30 px-3 py-2 text-sm text-red-200">
          {error}
        </p>
      ) : null}

      <div className="cyber-panel space-y-4 border-cyber-border p-5">
        <h3 className="text-sm font-bold uppercase tracking-wider text-cyber-neon">
          Mentions légales
        </h3>
        <p className="text-xs text-cyber-muted">
          Éditeur, hébergeur (Vercel / Railway selon le type de projet), SIRET et
          contact.
        </p>
        <select
          className="cyber-input w-full"
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
          className="cyber-action-btn cyber-action-btn-primary text-xs"
          disabled={mentionsBusy}
          onClick={() => void handleMentions()}
        >
          {mentionsBusy ? "Génération…" : "Générer mentions légales"}
        </button>
      </div>

      <div className="cyber-panel space-y-4 border-cyber-border p-5">
        <h3 className="text-sm font-bold uppercase tracking-wider text-cyber-neon">
          CGV
        </h3>
        <p className="text-xs text-cyber-muted">
          Conditions générales de vente globales (micro-entrepreneur prestataire
          digital). Un seul document CGV est conservé.
        </p>
        <button
          type="button"
          className="cyber-action-btn cyber-action-btn-primary text-xs"
          disabled={cgvBusy}
          onClick={() => void handleCgv()}
        >
          {cgvBusy ? "Génération…" : "Générer / télécharger les CGV"}
        </button>
      </div>

      {lastPdfUrl ? (
        <p className="text-xs text-cyber-muted">
          Dernier PDF :{" "}
          <a
            href={lastPdfUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-cyber-neon underline"
          >
            ouvrir
          </a>
        </p>
      ) : null}
    </div>
  );
}

import { useEffect, useState } from "react";
import { BackButton } from "@/components/BackButton";
import { modifyUnifiedProject, renameUnifiedProject, type UnifiedProject } from "@/lib/unified-projects";

interface ProjectEditViewProps {
  project: UnifiedProject;
  onBack: () => void;
  onSaved: () => void;
}

export function ProjectEditView({ project, onBack, onSaved }: ProjectEditViewProps) {
  const [projectName, setProjectName] = useState(project.name);
  const [modificationPrompt, setModificationPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    setProjectName(project.name);
    setModificationPrompt("");
    setError(null);
    setSuccess(null);
  }, [project.key, project.name]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmedMod = modificationPrompt.trim();
    if (trimmedMod.length < 10) {
      setError("Décrivez la modification en au moins 10 caractères.");
      return;
    }

    setBusy(true);
    setError(null);
    setSuccess(null);

    const nameTrimmed = projectName.trim();
    if (nameTrimmed && nameTrimmed !== project.name) {
      const rename = await renameUnifiedProject(project, nameTrimmed);
      if (!rename.ok) {
        setBusy(false);
        setError(rename.error ?? "Échec mise à jour du nom.");
        return;
      }
    }

    const result = await modifyUnifiedProject(project, trimmedMod, nameTrimmed || project.name);
    setBusy(false);

    if (!result.ok) {
      setError(result.error ?? "Modification impossible.");
      return;
    }

    setSuccess("Modification lancée avec succès. Le projet sera mis à jour sous peu.");
    setTimeout(() => {
      onSaved();
    }, 1200);
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header className="space-y-3">
        <BackButton onClick={onBack} />
        <p className="cf-section-label">Modifier le projet</p>
        <h1 className="cf-page-title">{project.name}</h1>
        <p className="text-sm text-cf-muted">
          Décrivez ce que vous souhaitez changer — le pipeline reçoit le contexte du projet
          existant.
        </p>
      </header>

      <form
        onSubmit={(e) => void handleSubmit(e)}
        className="space-y-5 rounded-card border border-cf-border-input bg-cf-card p-6 shadow-card"
      >
        <div>
          <label htmlFor="project-edit-name" className="mb-2 block text-sm font-medium text-cf-text">
            Nom du projet
          </label>
          <input
            id="project-edit-name"
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text focus:border-cf-gold/50 focus:outline-none"
            placeholder="Nom affiché dans l'onglet Projets"
          />
        </div>

        <div>
          <label
            htmlFor="project-edit-modification"
            className="mb-2 block text-sm font-medium text-cf-text"
          >
            Décrivez ce que vous voulez modifier
          </label>
          <textarea
            id="project-edit-modification"
            value={modificationPrompt}
            onChange={(e) => setModificationPrompt(e.target.value)}
            rows={6}
            className="w-full rounded-control border border-cf-border-input bg-cf-secondary px-3 py-2 text-sm text-cf-text placeholder:text-cf-muted focus:border-cf-gold/50 focus:outline-none"
            placeholder="Ex : Remplace la couleur principale par du bleu marine"
          />
        </div>

        {project.prompt ? (
          <div className="rounded-control border border-cf-border-input/60 bg-cf-secondary/30 px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wider text-cf-label">
              Contexte transmis au pipeline
            </p>
            <p className="mt-1 line-clamp-4 text-xs text-cf-muted">{project.prompt}</p>
          </div>
        ) : null}

        {error ? (
          <p className="rounded-control border border-red-500/30 bg-red-950/30 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        ) : null}

        {success ? (
          <p className="rounded-control border border-cf-gold/30 bg-cf-active px-3 py-2 text-sm text-cf-gold">
            {success}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={busy}
          className="rounded-control border border-cf-gold/50 bg-cf-active px-4 py-2 text-sm font-medium text-cf-gold hover:border-cf-gold disabled:opacity-50"
        >
          {busy ? "Modification en cours…" : "Appliquer la modification"}
        </button>
      </form>
    </div>
  );
}

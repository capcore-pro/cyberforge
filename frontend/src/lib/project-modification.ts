/** Construit le brief de contexte pour une modification de projet existant. */

export function buildProjectModificationContext(
  projectName: string,
  originalPrompt: string,
): string {
  const parts = [
    "## Contexte du projet existant",
    "",
    `Nom du projet : ${projectName.trim() || "Sans titre"}`,
  ];
  if (originalPrompt.trim()) {
    parts.push("", "Prompt / description d'origine :", originalPrompt.trim());
  }
  parts.push(
    "",
    "Conserve la structure et les fonctionnalités existantes sauf indication contraire.",
  );
  return parts.join("\n");
}

export function buildModificationPipelinePrompt(
  modificationPrompt: string,
  projectName: string,
  originalPrompt: string,
): { prompt: string; inspirationBrief: string } {
  const trimmed = modificationPrompt.trim();
  const context = buildProjectModificationContext(projectName, originalPrompt);
  return {
    prompt: trimmed,
    inspirationBrief: `${context}\n\n## Modification demandée\n\n${trimmed}`,
  };
}

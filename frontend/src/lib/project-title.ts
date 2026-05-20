/** Titre affichable pour un projet / une démo (première ligne du prompt). */
export function projectTitleFromPrompt(prompt: string, maxLen = 80): string {
  const line = prompt.trim().split("\n", 1)[0]?.trim() ?? "";
  if (!line) return "Démo CyberForge";
  if (line.length <= maxLen) return line;
  return `${line.slice(0, maxLen - 1).trim()}…`;
}

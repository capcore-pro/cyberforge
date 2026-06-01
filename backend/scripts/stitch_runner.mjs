/**
 * Google Stitch — génération de maquettes (HTML + screenshots).
 * Lit un JSON sur stdin, écrit le résultat sur stdout.
 *
 * STITCH_API_KEY doit être défini dans l'environnement.
 */
import { readFileSync } from "node:fs";
import { stitch } from "@google/stitch-sdk";

function readStdin() {
  try {
    return readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function progress(message) {
  console.error(JSON.stringify({ type: "stitch_progress", message }));
}

async function main() {
  const raw = readStdin().trim();
  if (!raw) {
    console.log(JSON.stringify({ success: false, error: "Entrée JSON vide" }));
    process.exit(1);
  }

  let input;
  try {
    input = JSON.parse(raw);
  } catch (err) {
    console.log(
      JSON.stringify({
        success: false,
        error: `JSON invalide: ${err?.message || err}`,
      }),
    );
    process.exit(1);
  }

  if (!process.env.STITCH_API_KEY?.trim()) {
    console.log(
      JSON.stringify({
        success: false,
        error: "STITCH_API_KEY manquante",
      }),
    );
    process.exit(1);
  }

  const screens = Array.isArray(input.screens) ? input.screens : [];
  if (!screens.length) {
    console.log(
      JSON.stringify({ success: false, error: "Aucun écran à générer" }),
    );
    process.exit(1);
  }

  const projectTitle =
    input.project_title?.trim() ||
    `CyberForge — ${input.client_name || "projet"}`;

  let projectId = input.project_id?.trim() || null;
  let project;

  try {
    if (projectId) {
      project = stitch.project(projectId);
      progress(`Projet Stitch ${projectId}`);
    } else {
      progress(`Création projet Stitch « ${projectTitle} »…`);
      project = await stitch.createProject(projectTitle);
      projectId = project.id || project.projectId || null;
    }

    const mockups = [];
    for (let i = 0; i < screens.length; i += 1) {
      const spec = screens[i];
      const name = spec.name || `Écran ${i + 1}`;
      const prompt = spec.prompt || "";
      const deviceType = spec.device_type === "MOBILE" ? "MOBILE" : "DESKTOP";

      progress(`Génération maquette ${i + 1}/${screens.length} : ${name}…`);
      const screen = await project.generate(prompt, deviceType);
      const htmlUrl = await screen.getHtml();
      const imageUrl = await screen.getImage();
      mockups.push({
        name,
        html_url: htmlUrl || "",
        image_url: imageUrl || "",
        screen_id: screen.id || null,
      });
    }

    console.log(
      JSON.stringify({
        success: true,
        project_id: projectId,
        mockups,
      }),
    );
  } catch (err) {
    console.log(
      JSON.stringify({
        success: false,
        project_id: projectId,
        error: err?.message || String(err),
        mockups: [],
      }),
    );
    process.exit(1);
  }
}

main();

/**
 * Google Stitch — génération de maquettes (HTML + screenshots).
 * Lit un JSON sur stdin, écrit le résultat sur stdout.
 *
 * STITCH_API_KEY doit être défini dans l'environnement.
 */
console.error("[Stitch] Démarrage runner");
import { readFileSync } from "node:fs";
import { readSync } from "node:fs";
import dotenv from "dotenv";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { Stitch, StitchToolClient } from "@google/stitch-sdk";

console.error("[Stitch] Imports terminés");

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
dotenv.config({ path: join(__dirname, "../.env") });
console.error("[Stitch] Clé API présente:", !!process.env.STITCH_API_KEY);

setTimeout(() => {
  console.error("[Stitch] TIMEOUT 60s");
  process.exit(1);
}, 60000);

function readStdin() {
  try {
    if (process.stdin.isTTY) {
      return "";
    }
    try {
      // Unix / POSIX pipes
      return readFileSync(0, "utf8");
    } catch {
      // Windows fallback (fd 0)
      try {
        const buf = Buffer.alloc(65536);
        const bytesRead = readSync(0, buf, 0, buf.length, null);
        if (!bytesRead) return "";
        return buf.slice(0, bytesRead).toString("utf8");
      } catch {
        return "";
      }
    }
  } catch {
    return "";
  }
}

function progress(message) {
  console.error(JSON.stringify({ type: "stitch_progress", message }));
}

async function main() {
  try {
    const inputFromArgs = process.argv[2]
      ? {
          screens: [{ name: "Accueil", prompt: process.argv[2] }],
          project_type: process.argv[3] || "vitrine_next",
          sector: process.argv[4] || "general",
          client_name: process.argv[2],
        }
      : null;

    const raw = (inputFromArgs ? "" : readStdin()).trim();
    if (!raw && !inputFromArgs) {
      console.log(JSON.stringify({ success: false, error: "Entrée JSON vide" }));
      process.exit(1);
    }

    let input = inputFromArgs;
    if (!input) {
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

    console.error("[Stitch] Avant appel SDK");
    console.error("[Stitch] Chargement SDK...");
    const client = new StitchToolClient({
      apiKey: process.env.STITCH_API_KEY,
    });
    const stitch = new Stitch(client);
    console.error("[Stitch] SDK chargé");
    console.error("[Stitch] Après appel SDK");

    let projectId = input.project_id?.trim() || null;
    let project;
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
      // Appel MCP direct (évite surprises de projection opaque)
      const raw = await client.callTool("generate_screen_from_text", {
        projectId: project.id,
        prompt,
        deviceType,
      });
      console.error(
        "[Stitch] Réponse tool generate_screen_from_text keys:",
        raw && typeof raw === "object" ? Object.keys(raw) : typeof raw,
      );
      const projected =
        raw?.outputComponents?.find((c) => c?.design?.screens != null)?.design
          ?.screens?.[0] || null;
      if (!projected) {
        console.error(
          "[Stitch] Erreur: réponse API inattendue (pas de design.screens[0])",
        );
        try {
          console.error(
            "[Stitch] Réponse brute (1200 chars):",
            JSON.stringify(raw).slice(0, 1200),
          );
        } catch {}
        process.exit(1);
      }
      // Screen handle (permet getHtml/getImage)
      const screenId =
        projected.id ||
        (typeof projected.name === "string" && projected.name.includes("/screens/")
          ? projected.name.split("/screens/")[1]
          : null);
      const screen = project.screen(screenId);
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
        project_title: projectTitle,
        mockups,
      }),
    );
  } catch (e) {
    console.error("[Stitch] Erreur:", e?.message || String(e));
    console.log(
      JSON.stringify({
        success: false,
        project_id: null,
        error: e?.message || String(e),
        mockups: [],
      }),
    );
    process.exit(1);
  }
}

main();

import type { StudioSection } from "@/lib/studio-types";

export const STUDIO_VIDEO_DRAFT_KEY = "cyberforge.studioVideoDraft";

export interface StudioVideoDraft {
  projectName: string;
  sector: string | null;
  sceneSections: Array<{
    description_fr: string;
    duree_secondes: string;
    style: string;
    ordre: string;
  }>;
  musicSection?: {
    style_musical: string;
    bpm: string;
    ambiance: string;
  };
}

export function buildStudioVideoDraft(
  projectName: string,
  sector: string | null,
  sections: StudioSection[],
): StudioVideoDraft {
  const sceneSections = sections
    .filter((s) => s.type === "scene_video")
    .sort((a, b) => a.order - b.order)
    .map((s) => ({
      description_fr: s.fields.description_fr ?? "",
      duree_secondes: s.fields.duree_secondes ?? "5",
      style: s.fields.style ?? "",
      ordre: s.fields.ordre ?? "1",
    }));

  const music = sections.find((s) => s.type === "musique_video");

  return {
    projectName,
    sector,
    sceneSections,
    musicSection: music
      ? {
          style_musical: music.fields.style_musical ?? "",
          bpm: music.fields.bpm ?? "Moyen",
          ambiance: music.fields.ambiance ?? "",
        }
      : undefined,
  };
}

import type { ProjectType } from "@shared/types";
import {
  buildGeneratorPipelinePrompt,
  getGeneratorKind,
  resolveGenerationMode,
  type DeployMode,
  type GeneratorKindId,
} from "@/lib/generator-kinds";
import type { StudioProjectKind, StudioSection } from "@/lib/studio-types";

export function slugifyProjectName(title: string): string {
  return title
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

export function resolveProjectTypeFromKind(
  kind: StudioProjectKind,
): ProjectType {
  if (kind === "video") return "application_web";
  return getGeneratorKind(kind as GeneratorKindId).projectType;
}

export function resolveStudioGenerationMode(
  kind: StudioProjectKind,
  deployMode: DeployMode,
  isPersonal: boolean,
) {
  if (kind === "video") return "real_app" as const;
  return resolveGenerationMode(kind as GeneratorKindId, deployMode, isPersonal);
}

function formatSectionFields(section: StudioSection): string {
  const pairs = Object.entries(section.fields)
    .filter(([, v]) => v.trim())
    .map(([k, v]) => `${k}="${v.replace(/"/g, "'")}"`);
  return pairs.join(", ");
}

export function buildBrief(
  sections: StudioSection[],
  projectType: StudioProjectKind,
  sector: string | null,
  projectName: string,
): string {
  const sorted = [...sections].sort((a, b) => a.order - b.order);
  const sectionLines = sorted.map((s) => {
    const tag = s.type.toUpperCase();
    const fields = formatSectionFields(s);
    const anim = s.animationClass ? ` animation="${s.animationClass}"` : "";
    const img = s.imageUrl ? ` image="${s.imageUrl}"` : "";
    return `- ${tag}: ${fields}${anim}${img}`;
  });

  let body = [
    `TYPE: ${projectType}`,
    sector ? `SECTEUR: ${sector}` : "",
    `NOM: ${projectName}`,
    "SECTIONS:",
    ...sectionLines,
  ]
    .filter(Boolean)
    .join("\n");

  if (projectType !== "video") {
    body = buildGeneratorPipelinePrompt(
      projectType as GeneratorKindId,
      body,
    );
  } else {
    body = `TYPE: video_kling\n${body}`;
  }

  return body;
}

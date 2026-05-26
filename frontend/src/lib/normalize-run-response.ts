import type {
  ComplexityLevel,
  CoreMindResponse,
  CoreMindRunResponse,
  GeneratedFile,
  GenerationMetrics,
  ProjectType,
} from "@shared/types";
import { unwrapGenerationPayload } from "@/lib/unwrap-generation";

const COMPLEXITY_LEVELS: ComplexityLevel[] = ["faible", "moyenne", "elevee"];
const PROJECT_TYPES: ProjectType[] = [
  "site_web",
  "landing_page",
  "application_web",
  "application_mobile",
  "extension_navigateur",
  "api_backend",
  "application_desktop",
  "saas_dashboard",
  "projet_generique",
];

const DEFAULT_METRICS: GenerationMetrics = {
  model: "—",
  provider: "—",
  complexity: "moyenne",
  complexity_score: 5,
  duration_ms: 0,
  estimated_cost_usd: 0,
  project_type_selected: null,
};

/** Normalise une réponse CoreMind (historique local parfois incomplet ou JSON enveloppé). */
export function normalizeRunResponse(
  raw: CoreMindRunResponse | null | undefined,
): CoreMindRunResponse | null {
  if (!raw || typeof raw !== "object") return null;

  const generation = raw.generation;
  if (!generation || typeof generation !== "object") return null;

  let code = typeof generation.code === "string" ? generation.code : "";
  let files: GeneratedFile[] = Array.isArray(generation.files)
    ? generation.files.filter(
        (f) => f && typeof f.path === "string" && typeof f.content === "string",
      )
    : [];

  const isPremiumPipeline =
    generation.provider === "cyberforge" &&
    (generation.model === "cyberforge-premium" ||
      generation.model === "taskflow-premium");

  if (isPremiumPipeline && code.trim()) {
    files = [{ path: "index.html", content: code }];
  } else {
    const unwrapped = unwrapGenerationPayload(files, code);
    code = unwrapped.code;
    files = unwrapped.files.length > 0 ? unwrapped.files : files;
    if (!files.length && code.trim()) {
      const isHtml =
        code.trimStart().toLowerCase().startsWith("<!") ||
        /<html[\s>]/i.test(code.slice(0, 800));
      files = [
        {
          path: isHtml ? "index.html" : "src/App.tsx",
          content: code,
        },
      ];
    }
  }
  if (!code && files.length > 0) {
    code = files[0].content;
  }
  if (!code.trim() && !files.length) return null;

  const analysis = normalizeAnalysis(raw.analysis, raw.metrics);
  const metrics = normalizeMetrics(raw.metrics, analysis);

  let preview_html =
    typeof raw.preview_html === "string" && raw.preview_html.trim()
      ? raw.preview_html.trim()
      : null;
  if (!preview_html && isPremiumPipeline && code.trim().includes("saas-shell")) {
    preview_html = code.trim();
  }

  const vision_screenshot_url =
    typeof raw.vision_screenshot_url === "string" && raw.vision_screenshot_url.trim()
      ? raw.vision_screenshot_url.trim()
      : null;
  const vision_preview_source =
    raw.vision_preview_source === "replicate" || raw.vision_preview_source === "local"
      ? raw.vision_preview_source
      : null;

  const validation_status =
    raw.validation_status === "validated" || raw.validation_status === "corrected"
      ? raw.validation_status
      : null;
  const testpilot_passed =
    typeof raw.testpilot_passed === "boolean" ? raw.testpilot_passed : null;
  const testpilot_summary =
    typeof raw.testpilot_summary === "string" ? raw.testpilot_summary : null;
  const production_url =
    typeof raw.production_url === "string" && raw.production_url.trim()
      ? raw.production_url.trim()
      : null;
  const export_provider =
    raw.export_provider === "cloudflare" || raw.export_provider === "railway"
      ? raw.export_provider
      : null;
  const github_export_url =
    typeof raw.github_export_url === "string" && raw.github_export_url.trim()
      ? raw.github_export_url.trim()
      : null;
  const unlock_url =
    typeof raw.unlock_url === "string" && raw.unlock_url.trim()
      ? raw.unlock_url.trim()
      : null;
  const demo_token =
    typeof raw.demo_token === "string" ? raw.demo_token : null;
  const demo_password =
    typeof raw.demo_password === "string" ? raw.demo_password : null;
  const export_manifest =
    raw.export_manifest && typeof raw.export_manifest === "object"
      ? (raw.export_manifest as Record<string, unknown>)
      : null;

  return {
    ...raw,
    preview_html,
    vision_screenshot_url,
    vision_preview_source,
    validation_status,
    testpilot_passed,
    testpilot_summary,
    production_url,
    export_provider,
    github_export_url,
    unlock_url,
    demo_token,
    demo_password,
    export_manifest,
    analysis,
    generation: {
      ...generation,
      code,
      files,
      stack: Array.isArray(generation.stack) ? generation.stack : [],
      summary:
        typeof generation.summary === "string" ? generation.summary : "",
      model: typeof generation.model === "string" ? generation.model : metrics.model,
      provider:
        typeof generation.provider === "string"
          ? generation.provider
          : metrics.provider,
      demo_seed:
        generation.demo_seed && typeof generation.demo_seed === "object"
          ? generation.demo_seed
          : null,
    },
    metrics,
    planned_models: Array.isArray(raw.planned_models)
      ? raw.planned_models.map(String)
      : [],
  };
}

function normalizeAnalysis(
  raw: CoreMindResponse | undefined,
  metrics: GenerationMetrics | undefined,
): CoreMindResponse {
  const src = raw && typeof raw === "object" ? raw : ({} as Partial<CoreMindResponse>);
  const projectType = coerceProjectType(
    src.project_type ?? metrics?.project_type_selected,
  );
  const complexity = coerceComplexity(src.complexity ?? metrics?.complexity);

  return {
    agent_id: typeof src.agent_id === "string" ? src.agent_id : "coremind",
    agent_name: typeof src.agent_name === "string" ? src.agent_name : "CoreMindAI",
    project_type: projectType,
    project_type_label:
      typeof src.project_type_label === "string"
        ? src.project_type_label
        : projectType,
    recommended_tool:
      src.recommended_tool === "v0" || src.recommended_tool === "deepseek"
        ? src.recommended_tool
        : "v0",
    tool_rationale:
      typeof src.tool_rationale === "string" ? src.tool_rationale : "",
    complexity,
    complexity_score:
      typeof src.complexity_score === "number"
        ? src.complexity_score
        : typeof metrics?.complexity_score === "number"
          ? metrics.complexity_score
          : 5,
    next_steps: Array.isArray(src.next_steps)
      ? src.next_steps.map(String)
      : [],
    summary: typeof src.summary === "string" ? src.summary : "",
  };
}

function normalizeMetrics(
  raw: GenerationMetrics | undefined,
  analysis: CoreMindResponse,
): GenerationMetrics {
  const src: Partial<GenerationMetrics> =
    raw && typeof raw === "object" ? raw : {};
  return {
    model: typeof src.model === "string" && src.model ? src.model : DEFAULT_METRICS.model,
    provider:
      typeof src.provider === "string" && src.provider
        ? src.provider
        : DEFAULT_METRICS.provider,
    complexity: coerceComplexity(src.complexity ?? analysis.complexity),
    complexity_score:
      typeof src.complexity_score === "number"
        ? src.complexity_score
        : analysis.complexity_score,
    duration_ms:
      typeof src.duration_ms === "number" ? src.duration_ms : DEFAULT_METRICS.duration_ms,
    estimated_cost_usd:
      typeof src.estimated_cost_usd === "number"
        ? src.estimated_cost_usd
        : DEFAULT_METRICS.estimated_cost_usd,
    project_type_selected:
      typeof src.project_type_selected === "string"
        ? src.project_type_selected
        : null,
  };
}

function coerceComplexity(value: unknown): ComplexityLevel {
  if (typeof value === "string") {
    const lower = value.toLowerCase() as ComplexityLevel;
    if (COMPLEXITY_LEVELS.includes(lower)) return lower;
  }
  return "moyenne";
}

function coerceProjectType(value: unknown): ProjectType {
  if (typeof value === "string" && PROJECT_TYPES.includes(value as ProjectType)) {
    return value as ProjectType;
  }
  return "site_web";
}

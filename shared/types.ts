/**
 * Types partagés — contrats de données entre frontend et backend.
 */

/** Réponse standard du point de contrôle santé */
export interface HealthResponse {
  status: "ok" | "degraded";
  app: string;
  version: string;
}

/** Métadonnées d'un agent IA (sans clés ni credentials) */
export interface AgentInfo {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
}

/** Statut d'un agent — GET /api/agents/status */
export interface AgentStatusItem {
  id: string;
  name: string;
  description: string;
  status: "active" | "standby";
  in_pipeline: boolean;
}

/** Réponse GET /api/agents/status */
export interface AgentsStatusResponse {
  total_agents: number;
  active_count: number;
  pipeline_agent_ids: string[];
  agents: AgentStatusItem[];
}

/** Types de projet détectés par CoreMindAI */
export type ProjectType =
  | "site_web"
  | "landing_page"
  | "application_web"
  | "application_mobile"
  | "extension_navigateur"
  | "api_backend"
  | "application_desktop"
  | "saas_dashboard"
  | "projet_generique";

/** Outils de génération recommandés */
export type RecommendedTool = "v0" | "deepseek";

/** Niveau de complexité estimé */
export type ComplexityLevel = "faible" | "moyenne" | "elevee";

/**
 * Mode de génération :
 * - `client_demo`   : pipeline démo HTML premium TaskFlow (défaut)
 * - `real_app`      : génération d'une vraie application React/Next.js déployable
 * - `vitrine_next`  : scaffold Next.js fixe + contenu JSON (Phase 4 vitrine)
 */
export type GenerationMode = "client_demo" | "real_app" | "vitrine_next";

/** Requête POST /api/agents/coremind */
export interface CoreMindRequest {
  prompt: string;
  project_type?: ProjectType | null;
  generation_mode?: GenerationMode | null;
  /** Suivi coûts API (cost_tracker) — UUID client ou id projet Supabase */
  project_id?: string | null;
  /** Brief Firecrawl (clone-inspiration) transmis à ArchitectAI */
  inspiration_brief?: string | null;
  /** Palette / couleurs / images Firecrawl pour DesignSystemAI */
  firecrawl_result?: Record<string, unknown> | null;
  /** Projet perso — déploiement Cloudflare Pages dédié en mode vraie app */
  personal_project?: boolean;
  /** Slug projet Pages (ex. capcore-pro-site) */
  pages_project_slug?: string | null;
  /** Titre du projet pour l'export */
  project_title?: string | null;
  /** OpenHands — projets complexes (≥ 7/10) real_app / application_web */
  openhands_enabled?: boolean | null;
  /** Tests Playwright E2E après TestPilotAI */
  playwright_enabled?: boolean | null;
  /** Audit Lighthouse après Playwright */
  lighthouse_enabled?: boolean | null;
  /** ResearchAI Brave + Exa après ArchitectAI */
  research_enabled?: boolean | null;
}

/** Tarification ArchitectAI (SSE ou GET /projects/{id}/costs) */
export interface ArchitectPlanCosts {
  complexity_score: number;
  complexity_label: string;
  market_price_min: number;
  market_price_max: number;
  suggested_price_min: number;
  suggested_price_max: number;
}

/** GET /api/projects/{project_id}/costs */
export interface ProjectCostsResponse {
  project_id: string;
  total_eur: number;
  by_service: Record<string, number>;
  architect_plan: ArchitectPlanCosts | null;
  margin_multiplier: number | null;
  updated_at: string;
}

/** DELETE /api/projects/{project_id}/costs */
export interface ResetProjectCostsResponse {
  status: string;
}

/** Métriques de génération (page Générateur) */
export interface GenerationMetrics {
  model: string;
  provider: string;
  complexity: ComplexityLevel;
  complexity_score: number;
  duration_ms: number;
  estimated_cost_usd: number;
  project_type_selected: string | null;
}

/** Réponse structurée de CoreMindAI */
export interface CoreMindResponse {
  agent_id: string;
  agent_name: string;
  project_type: ProjectType;
  project_type_label: string;
  recommended_tool: RecommendedTool;
  tool_rationale: string;
  complexity: ComplexityLevel;
  complexity_score: number;
  next_steps: string[];
  summary: string;
  /** Schéma Supabase généré (DatabaseAI) — stocké dans analysis Supabase. */
  database_schema?: unknown;
  /** Schéma Auth/RLS généré (AuthAI) — stocké dans analysis Supabase. */
  auth_schema?: unknown;
  /** Configuration Stripe générée (PaymentAI) — stocké dans analysis Supabase. */
  payment_config?: unknown;
}

/** Fichier généré par CoreMindAI (Claude) */
export interface GeneratedFile {
  path: string;
  content: string;
}

/** Requête POST /api/agents/coremind/generate */
export interface CoreMindGenerateRequest {
  prompt: string;
}

/** Réponse POST /api/agents/coremind/generate */
export interface DemoSeedTask {
  text: string;
  completed: boolean;
}

export interface DemoSeedStats {
  total: number;
  active: number;
  done: number;
}

export interface DemoSeedPayload {
  template?: string;
  title?: string;
  subtitle?: string;
  brand_name?: string;
  brand_tag?: string;
  user_name?: string;
  user_role?: string;
  user_initials?: string;
  tasks?: DemoSeedTask[];
  llm_personalized?: boolean;
  /** Couleur principale (#RRGGBB) pour l'aperçu / démo TaskFlow. */
  primary_color?: string;
  /** Couleur secondaire (#RRGGBB) pour dégradés et accents. */
  secondary_color?: string;
  /** Logo client (data URL PNG/JPG) affiché dans le header de la démo. */
  logo_data_url?: string | null;
  /** Stats KPI (Total, En cours, Terminées) — prioritaire sur le calcul live. */
  stats?: DemoSeedStats | null;
}

export interface CoreMindGenerateResponse {
  summary: string;
  code: string;
  files: GeneratedFile[];
  stack: string[];
  model: string;
  provider: string;
  demo_seed?: DemoSeedPayload | null;
}

/** Identifiants Supabase après sauvegarde */
export interface PersistenceResult {
  project_id: string;
  generation_id: string;
  storage: string;
}

/** Pipeline démo unique (TaskFlow + seed) */
export interface DemoPipelineSummary {
  template: string;
  seed_personalized: boolean;
  html_bytes: number;
  single_file: string;
}

/** Identifiants des agents du pipeline LangGraph */
export type PipelineAgentId =
  | "architect"
  | "research"
  | "openhands"
  | "builder"
  | "extension_build"
  | "coremind"
  | "visionui"
  | "bughunter"
  | "autofix"
  | "testpilot"
  | "playwright"
  | "lighthouse"
  | "export"
  | "finalize";

export type ExportProvider = "cloudflare" | "railway" | "zip";

export type ValidationStatus = "validated" | "corrected";

export type VisionPreviewSource = "replicate" | "local";

export type PipelineStepPhase = "start" | "done" | "error";

/** Événement SSE step_* pendant POST /api/agents/coremind/run/stream */
export interface PipelineStepEvent {
  type: `step_${PipelineStepPhase}` | "pipeline_start" | "pipeline_end" | "result" | "error";
  agent?: PipelineAgentId;
  agent_name?: string;
  message?: string;
  ok?: boolean;
  template?: string;
  loop?: number;
  vision_screenshot_url?: string | null;
  vision_preview_source?: VisionPreviewSource | null;
  vision_local_html?: string | null;
  /** HTML déverrouillé (aperçu iframe interne après BuilderAI). */
  preview_html?: string | null;
  validation_status?: ValidationStatus | null;
  validation_badge?: string | null;
  testpilot_passed?: boolean | null;
  production_url?: string | null;
  export_provider?: ExportProvider | string | null;
  artifact_download_url?: string | null;
  github_export_url?: string | null;
  unlock_url?: string | null;
  demo_token?: string | null;
  demo_password?: string | null;
  playwright_score?: number | null;
  playwright_passed?: string[] | null;
  playwright_failed?: string[] | null;
  lighthouse_score_global?: number | null;
  lighthouse_performance?: number | null;
  lighthouse_seo?: number | null;
  lighthouse_accessibility?: number | null;
  lighthouse_best_practices?: number | null;
  lighthouse_recommendations?: string[] | null;
  complexity_score?: number;
  complexity_label?: string;
  market_price_min?: number;
  market_price_max?: number;
  suggested_price_min?: number;
  suggested_price_max?: number;
  pricing_category?: string;
}

/** Réponse POST /api/agents/coremind/run — flow complet */
export interface CoreMindRunResponse {
  analysis: CoreMindResponse;
  generation: CoreMindGenerateResponse;
  metrics: GenerationMetrics;
  planned_models: string[];
  persistence?: PersistenceResult | null;
  demo_pipeline?: DemoPipelineSummary | null;
  /** HTML aperçu serveur (aligné sur le livrable corrigé) */
  preview_html?: string | null;
  /** Capture VisionUI (Replicate ou placeholder local) */
  vision_screenshot_url?: string | null;
  vision_preview_source?: VisionPreviewSource | null;
  testpilot_passed?: boolean | null;
  validation_status?: ValidationStatus | null;
  testpilot_summary?: string | null;
  export_manifest?: Record<string, unknown> | null;
  production_url?: string | null;
  export_provider?: ExportProvider | string | null;
  artifact_download_url?: string | null;
  github_export_url?: string | null;
  demo_token?: string | null;
  demo_password?: string | null;
  unlock_url?: string | null;
  playwright_score?: number | null;
  playwright_report?: PlaywrightReportSummary | null;
  lighthouse_score_global?: number | null;
  lighthouse_report?: LighthouseReportSummary | null;
}

/** Rapport Playwright (passed / failed / score) */
export interface PlaywrightReportSummary {
  passed: string[];
  failed: string[];
  score: number;
  ok?: boolean;
  skipped?: boolean;
  skip_reason?: string | null;
  target_url?: string;
}

/** Rapport Lighthouse (4 scores + score global) */
export interface LighthouseReportSummary {
  performance: number;
  seo: number;
  accessibility: number;
  best_practices: number;
  score_global: number;
  ok?: boolean;
  skipped?: boolean;
  skip_reason?: string | null;
  recommendations?: string[];
  target_url?: string;
  full_report?: Record<string, unknown> | null;
}

/** Projet enregistré dans Supabase */
export interface ProjectRecord {
  id: string;
  title: string;
  prompt: string;
  project_type: ProjectType;
  summary: string | null;
  created_at: string;
  updated_at: string;
  generation_count: number;
  latest_model: string | null;
  latest_estimated_cost_usd: number | null;
  preview_html: string | null;
}

/** Projet géré par CyberForge (V1) — vitrines Next.js */
export interface ManagedProjectRecord {
  id: string;
  type: string;
  slug: string;
  title: string | null;
  prompt_original: string;
  prompt_last: string;
  status: string;
  provider: string;
  github_repo: string;
  github_branch: string;
  vercel_project_id: string | null;
  vercel_frontend_project_id: string | null;
  vercel_deployment_id_last: string | null;
  url_preview: string | null;
  url_production: string | null;
  url_backend: string | null;
  railway_project_id: string | null;
  railway_service_id: string | null;
  error_last: string | null;
  cms_enabled?: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

/** Run d'exécution (create/update/delete) pour un projet géré */
export interface ManagedProjectRunRecord {
  id: string;
  project_id: string;
  action: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  error: string | null;
  artifacts: Record<string, unknown>;
}

/** Génération enregistrée dans Supabase */
export interface GenerationRecord {
  id: string;
  project_id: string;
  prompt: string;
  project_type: ProjectType;
  model: string;
  provider: string;
  complexity: ComplexityLevel;
  complexity_score: number;
  duration_ms: number;
  estimated_cost_usd: number;
  code: string;
  files: GeneratedFile[];
  stack: string[];
  analysis: CoreMindResponse;
  generation_summary: string | null;
  planned_models: string[];
  created_at: string;
}

/** Détail projet + historique des générations */
export interface ProjectDetailResponse {
  project: ProjectRecord;
  generations: GenerationRecord[];
}

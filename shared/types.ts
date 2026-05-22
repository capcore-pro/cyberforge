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
export type RecommendedTool = "bolt.new" | "lovable" | "v0";

/** Niveau de complexité estimé */
export type ComplexityLevel = "faible" | "moyenne" | "elevee";

/** Requête POST /api/agents/coremind */
export interface CoreMindRequest {
  prompt: string;
  project_type?: ProjectType | null;
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
export interface CoreMindGenerateResponse {
  summary: string;
  code: string;
  files: GeneratedFile[];
  stack: string[];
  model: string;
  provider: string;
}

/** Identifiants Supabase après sauvegarde */
export interface PersistenceResult {
  project_id: string;
  generation_id: string;
  storage: string;
}

/** Qualité livrable (BugHunterAI / AutoFixAI) */
export interface DemoQualitySummary {
  ok: boolean;
  issue_codes: string[];
  fix_attempts: number;
  autofix_applied: boolean;
  taskflow_fallback: boolean;
}

/** Réponse POST /api/agents/coremind/run — flow complet */
export interface CoreMindRunResponse {
  analysis: CoreMindResponse;
  generation: CoreMindGenerateResponse;
  metrics: GenerationMetrics;
  planned_models: string[];
  persistence?: PersistenceResult | null;
  demo_quality?: DemoQualitySummary | null;
  /** HTML aperçu serveur (aligné sur le livrable corrigé) */
  preview_html?: string | null;
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

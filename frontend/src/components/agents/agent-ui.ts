import type { AgentRegistryEntry } from "@/lib/agents-api";
import type { VaultConfiguredFlags } from "@/lib/secrets-api";

const CATEGORY_ICON: Record<string, string> = {
  supervision: "ti ti-shield-check",
  generation: "ti ti-wand",
  ingestion: "ti ti-file-text",
  design: "ti ti-palette",
  deployment: "ti ti-rocket",
  database: "ti ti-database",
  security: "ti ti-lock",
  payment: "ti ti-credit-card",
  communication: "ti ti-mail",
  media: "ti ti-photo",
  desktop: "ti ti-device-desktop",
};

const CATEGORY_BADGE: Record<string, string> = {
  supervision: "border-amber-400/35 bg-amber-500/15 text-amber-200",
  generation: "border-violet-400/35 bg-violet-500/15 text-violet-200",
  ingestion: "border-blue-400/35 bg-blue-500/15 text-blue-200",
  design: "border-pink-400/35 bg-pink-500/15 text-pink-200",
  deployment: "border-cyan-400/35 bg-cyan-500/15 text-cyan-200",
  database: "border-teal-400/35 bg-teal-500/15 text-teal-200",
  security: "border-red-400/35 bg-red-500/15 text-red-200",
  payment: "border-emerald-400/35 bg-emerald-500/15 text-emerald-200",
  communication: "border-sky-400/35 bg-sky-500/15 text-sky-200",
  media: "border-fuchsia-400/35 bg-fuchsia-500/15 text-fuchsia-200",
  desktop: "border-white/20 bg-white/10 text-white/70",
};

export function agentCategoryIcon(category: string): string {
  return CATEGORY_ICON[category] ?? "ti ti-robot";
}

export function agentCategoryBadgeClass(category: string): string {
  return CATEGORY_BADGE[category] ?? "border-white/20 bg-white/10 text-white/70";
}

export function agentCategoryLabel(category: string): string {
  return category.replace(/_/g, " ");
}

export function isKeyConfigured(
  requiresKey: string | null,
  configured: VaultConfiguredFlags | undefined,
): boolean {
  if (!requiresKey) return true;
  const key = requiresKey.toLowerCase();
  if (!configured) return false;
  const mapping: Record<string, keyof VaultConfiguredFlags> = {
    anthropic: "anthropic",
    openai: "openai",
    deepseek: "deepseek",
    replicate: "replicate",
    stripe: "stripe",
    brevo: "brevo",
    cloudflare: "cloudflare",
    pexels: "pexels",
    firecrawl: "firecrawl",
  };
  const flag = mapping[key];
  if (flag && flag in configured) {
    return Boolean(configured[flag]);
  }
  return false;
}

export function agentRuntimeActive(
  agent: AgentRegistryEntry,
  statusMap: Map<string, string>,
): boolean {
  const runtime = statusMap.get(agent.agent_id);
  if (runtime) return runtime === "active";
  return agent.enabled;
}

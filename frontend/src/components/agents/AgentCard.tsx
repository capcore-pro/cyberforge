import type { AgentRegistryEntry } from "@/lib/agents-api";
import {
  agentCategoryBadgeClass,
  agentCategoryIcon,
  agentCategoryLabel,
  agentRuntimeActive,
} from "@/components/agents/agent-ui";

interface AgentCardProps {
  agent: AgentRegistryEntry;
  statusMap: Map<string, string>;
  keyConfigured: boolean;
  onOpenDetails: (agent: AgentRegistryEntry) => void;
}

export function AgentCard({
  agent,
  statusMap,
  keyConfigured,
  onOpenDetails,
}: AgentCardProps) {
  const active = agentRuntimeActive(agent, statusMap);
  const iconClass = agentCategoryIcon(agent.category);

  return (
    <article className="relative flex flex-col rounded-xl border border-white/10 bg-white/[0.03] p-4 transition-all duration-200 hover:border-[#d4a843]/30">
      <div className="absolute right-3 top-3 flex flex-col items-end gap-1">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${
            active
              ? "border-emerald-400/35 bg-emerald-500/15 text-emerald-300"
              : "border-white/20 bg-white/10 text-white/45"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              active ? "bg-emerald-400" : "bg-white/30"
            }`}
            aria-hidden
          />
          {active ? "Actif" : "Inactif"}
        </span>
        {agent.in_pipeline ? (
          <span className="rounded-full border border-[#d4a843]/40 bg-[#d4a843]/15 px-2 py-0.5 text-[10px] font-semibold uppercase text-[#d4a843]">
            Pipeline
          </span>
        ) : null}
      </div>

      <div className="mb-3 flex items-start gap-3 pr-20">
        <span
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-lg text-[#d4a843]"
          aria-hidden
        >
          <i className={iconClass} />
        </span>
        <div className="min-w-0">
          <h3 className="font-medium text-white">{agent.name}</h3>
          <span
            className={`mt-1 inline-block rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${agentCategoryBadgeClass(agent.category)}`}
          >
            {agentCategoryLabel(agent.category)}
          </span>
        </div>
      </div>

      <p className="mb-3 line-clamp-3 flex-1 text-sm text-white/60">
        {agent.description}
      </p>

      {agent.model ? (
        <p className="mb-2 text-xs text-white/40">Modèle : {agent.model}</p>
      ) : null}

      {agent.requires_key ? (
        <span
          className={`mb-3 inline-flex w-fit rounded-full border px-2 py-0.5 text-[10px] font-medium ${
            keyConfigured
              ? "border-teal-400/35 bg-teal-500/15 text-teal-200"
              : "border-amber-400/35 bg-amber-500/15 text-amber-200"
          }`}
        >
          {keyConfigured
            ? "Clé configurée"
            : `Clé requise : ${agent.requires_key}`}
        </span>
      ) : null}

      <footer className="mt-auto flex items-center justify-between gap-2 border-t border-white/10 pt-3">
        <span className="text-xs text-white/30">v{agent.version}</span>
        <button
          type="button"
          onClick={() => onOpenDetails(agent)}
          className="rounded-control border border-white/15 bg-white/5 px-3 py-1.5 text-xs text-white/70 transition hover:border-[#d4a843]/40 hover:text-[#d4a843]"
        >
          Détails
        </button>
      </footer>
    </article>
  );
}

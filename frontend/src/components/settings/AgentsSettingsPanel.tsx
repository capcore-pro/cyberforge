import { useCallback, useEffect, useMemo, useState } from "react";
import { GLASS_CARD, GLASS_SECTION } from "@/components/settings/settings-theme";
import { useAgentsStatus } from "@/context/AgentsStatusContext";
import { formatRelativeDate } from "@/lib/client-page-utils";
import {
  isLighthouseEnabled,
  setLighthouseEnabled,
} from "@/lib/lighthouse-preferences";
import {
  isPlaywrightEnabled,
  setPlaywrightEnabled,
} from "@/lib/playwright-preferences";
import {
  isSupervisorEnabled,
  setSupervisorEnabled,
} from "@/lib/supervisor-preferences";
import { fetchSystemNotifications } from "@/lib/system-notifications-api";

interface PipelineAgentDef {
  id: string;
  name: string;
  role: string;
  model: string;
  cost: string;
}

const PIPELINE_AGENTS: PipelineAgentDef[] = [
  {
    id: "brief",
    name: "BriefAI",
    role: "Enrichit le brief via Firecrawl + Claude Haiku",
    model: "Claude Haiku 4",
    cost: "~$0.02 / brief",
  },
  {
    id: "supervisor",
    name: "SupervisorAI",
    role: "Valide chaque étape, dictateur qualité",
    model: "Claude Haiku 4",
    cost: "~$0.01 / étape",
  },
  {
    id: "generator",
    name: "GeneratorAI",
    role: "Génère le HTML premium",
    model: "Claude Sonnet 4",
    cost: "~$0.15 / génération",
  },
  {
    id: "deploy",
    name: "DeployAI",
    role: "Injecte photos Pexels + déploie sur Cloudflare",
    model: "—",
    cost: "~$0.00",
  },
  {
    id: "database",
    name: "DatabaseAI",
    role: "Génère schéma Supabase",
    model: "Claude Sonnet 4",
    cost: "~$0.05 / schéma",
  },
  {
    id: "auth",
    name: "AuthAI",
    role: "Configure authentification Supabase",
    model: "Claude Sonnet 4",
    cost: "~$0.04 / config",
  },
  {
    id: "payment",
    name: "PaymentAI",
    role: "Configure Stripe client",
    model: "Claude Sonnet 4",
    cost: "~$0.04 / config",
  },
  {
    id: "electron",
    name: "ElectronAI",
    role: "Package en .exe Windows",
    model: "—",
    cost: "~$0.00",
  },
];

function PipelineToggle({
  enabled,
  onChange,
}: {
  enabled: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={() => onChange(!enabled)}
      className={`relative h-7 w-12 shrink-0 rounded-full border transition ${
        enabled
          ? "border-[#d4a843] bg-[#d4a843]"
          : "border-white/20 bg-white/10"
      }`}
    >
      <span
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-[#0a0a0a] transition ${
          enabled ? "left-[22px]" : "left-0.5"
        }`}
      />
    </button>
  );
}

export function AgentsSettingsPanel() {
  const { status, loading } = useAgentsStatus();
  const [lastUsed, setLastUsed] = useState<Record<string, string>>({});
  const [supervisorOn, setSupervisorOn] = useState(isSupervisorEnabled);
  const [playwrightOn, setPlaywrightOn] = useState(isPlaywrightEnabled);
  const [lighthouseOn, setLighthouseOn] = useState(isLighthouseEnabled);

  const loadNotifications = useCallback(async () => {
    const res = await fetchSystemNotifications();
    if (!res.ok || !res.data?.items) return;
    const map: Record<string, string> = {};
    for (const item of res.data.items) {
      const hay = `${item.title} ${item.message ?? ""}`;
      for (const agent of PIPELINE_AGENTS) {
        if (hay.includes(agent.name) && !map[agent.id]) {
          map[agent.id] = item.created_at;
        }
      }
    }
    setLastUsed(map);
  }, []);

  useEffect(() => {
    void loadNotifications();
  }, [loadNotifications]);

  const statusById = useMemo(() => {
    const map = new Map<string, string>();
    for (const a of status?.agents ?? []) {
      map.set(a.id, a.status);
    }
    return map;
  }, [status]);

  const activeCount = useMemo(
    () =>
      PIPELINE_AGENTS.filter(
        (a) => (statusById.get(a.id) ?? "standby") === "active",
      ).length,
    [statusById],
  );

  return (
    <div className="space-y-6">
      <div className={GLASS_SECTION}>
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-white/45">
            Statut pipeline v2
          </h3>
          <span className="text-xs text-white/50">
            {loading ? "…" : `${activeCount} / ${PIPELINE_AGENTS.length} actifs`}
          </span>
        </div>

        {loading && !status ? (
          <p className="animate-pulse text-sm text-white/50">Chargement…</p>
        ) : (
          <ul className="grid gap-3 lg:grid-cols-2">
            {PIPELINE_AGENTS.map((agent) => {
              const apiStatus = statusById.get(agent.id) ?? "standby";
              const active = apiStatus === "active";
              const usedAt = lastUsed[agent.id];
              return (
                <li key={agent.id} className={GLASS_CARD}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-white">
                        {agent.name}
                      </p>
                      <p className="mt-1 text-xs text-white/55">{agent.role}</p>
                    </div>
                    <span
                      className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${
                        active
                          ? "border-emerald-400/35 bg-emerald-500/15 text-emerald-300"
                          : "border-white/20 bg-white/10 text-white/45"
                      }`}
                    >
                      {active ? "Actif" : "Inactif"}
                    </span>
                  </div>
                  <dl className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
                    <div>
                      <dt className="text-white/35">Modèle</dt>
                      <dd className="text-[#d4a843]/90">{agent.model}</dd>
                    </div>
                    <div>
                      <dt className="text-white/35">Coût estimé</dt>
                      <dd className="text-white/60">{agent.cost}</dd>
                    </div>
                  </dl>
                  <p className="mt-2 text-[10px] text-white/35">
                    Dernière utilisation :{" "}
                    {usedAt ? formatRelativeDate(usedAt) : "—"}
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className={GLASS_SECTION}>
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-widest text-white/45">
          Options pipeline
        </h3>
        <ul className="space-y-3">
          <li className={`${GLASS_CARD} flex items-center justify-between gap-4`}>
            <div>
              <p className="text-sm font-medium text-white">SupervisorAI</p>
              <p className="mt-1 text-xs text-white/50">
                Validation binaire à chaque étape du pipeline.
              </p>
            </div>
            <PipelineToggle
              enabled={supervisorOn}
              onChange={(next) => {
                setSupervisorEnabled(next);
                setSupervisorOn(next);
              }}
            />
          </li>
          <li className={`${GLASS_CARD} flex items-center justify-between gap-4`}>
            <div>
              <p className="text-sm font-medium text-white">Tests Playwright</p>
              <p className="mt-1 text-xs text-white/50">
                Tests E2E Chromium — liens, formulaires, responsive.
              </p>
            </div>
            <PipelineToggle
              enabled={playwrightOn}
              onChange={(next) => {
                setPlaywrightEnabled(next);
                setPlaywrightOn(next);
              }}
            />
          </li>
          <li className={`${GLASS_CARD} flex items-center justify-between gap-4`}>
            <div>
              <p className="text-sm font-medium text-white">Lighthouse</p>
              <p className="mt-1 text-xs text-white/50">
                Audit Performance, SEO et accessibilité.
              </p>
            </div>
            <PipelineToggle
              enabled={lighthouseOn}
              onChange={(next) => {
                setLighthouseEnabled(next);
                setLighthouseOn(next);
              }}
            />
          </li>
        </ul>
      </div>
    </div>
  );
}

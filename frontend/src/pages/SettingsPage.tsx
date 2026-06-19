import { useState } from "react";
import { GOLD_BTN, GLASS_SECTION } from "@/components/settings/settings-theme";
import { ApiKeysSettingsPanel } from "@/components/settings/ApiKeysSettingsPanel";
import { ProfileSettingsPanel } from "@/components/settings/ProfileSettingsPanel";
import { SystemSettingsPanel } from "@/components/settings/SystemSettingsPanel";
import { TAB_ACTIVE, TAB_BASE } from "@/components/settings/settings-theme";
import type { AppPage } from "@/lib/navigation";

type SettingsTab = "profile" | "keys" | "agents" | "system";

const TABS: { id: SettingsTab; label: string }[] = [
  { id: "profile", label: "Mon Profil" },
  { id: "keys", label: "Clés API" },
  { id: "agents", label: "Agents IA" },
  { id: "system", label: "Système" },
];

interface SettingsPageProps {
  onNavigate?: (page: AppPage) => void;
}

/**
 * Paramètres — profil, clés API, agents pipeline v2 et système.
 */
export function SettingsPage({ onNavigate }: SettingsPageProps) {
  const [tab, setTab] = useState<SettingsTab>("profile");

  return (
    <div className="mx-auto flex h-full min-h-0 max-w-4xl flex-col space-y-8">
      <header>
        <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-[#d4a843]/80">
          Configuration
        </p>
        <h1 className="text-2xl font-semibold text-white">Paramètres</h1>
        <p className="mt-2 text-sm text-white/50">
          Profil CapCore, clés API, agents pipeline v2 et maintenance système.
        </p>
      </header>

      <nav className="flex flex-wrap gap-1 border-b border-white/10">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`${TAB_BASE} ${tab === item.id ? TAB_ACTIVE : ""}`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <section className="min-h-0 flex-1">
        {tab === "profile" ? <ProfileSettingsPanel /> : null}
        {tab === "keys" ? <ApiKeysSettingsPanel /> : null}
        {tab === "agents" ? (
          <div className={`${GLASS_SECTION} space-y-4`}>
            <p className="text-sm text-white/60">
              La gestion détaillée des agents (registre, modèles, métriques) est
              disponible sur la page dédiée Agents IA.
            </p>
            <button
              type="button"
              onClick={() => onNavigate?.("agents")}
              className={`${GOLD_BTN} inline-flex items-center gap-2`}
            >
              <i className="ti ti-robot" aria-hidden />
              Voir la page Agents IA
            </button>
          </div>
        ) : null}
        {tab === "system" ? <SystemSettingsPanel /> : null}
      </section>
    </div>
  );
}

import { useState } from "react";
import { AgentsSettingsPanel } from "@/components/settings/AgentsSettingsPanel";
import { ApiKeysSettingsPanel } from "@/components/settings/ApiKeysSettingsPanel";
import { ProfileSettingsPanel } from "@/components/settings/ProfileSettingsPanel";
import { SystemSettingsPanel } from "@/components/settings/SystemSettingsPanel";
import { TAB_ACTIVE, TAB_BASE } from "@/components/settings/settings-theme";

type SettingsTab = "profile" | "keys" | "agents" | "system";

const TABS: { id: SettingsTab; label: string }[] = [
  { id: "profile", label: "Mon Profil" },
  { id: "keys", label: "Clés API" },
  { id: "agents", label: "Agents IA" },
  { id: "system", label: "Système" },
];

/**
 * Paramètres — profil, clés API, agents pipeline v2 et système.
 */
export function SettingsPage() {
  const [tab, setTab] = useState<SettingsTab>("profile");

  return (
    <div className="mx-auto max-w-4xl space-y-8">
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

      <section>
        {tab === "profile" ? <ProfileSettingsPanel /> : null}
        {tab === "keys" ? <ApiKeysSettingsPanel /> : null}
        {tab === "agents" ? <AgentsSettingsPanel /> : null}
        {tab === "system" ? <SystemSettingsPanel /> : null}
      </section>
    </div>
  );
}

import { useState } from "react";
import { ApiKeysSettingsPanel } from "@/components/settings/ApiKeysSettingsPanel";
import { AgentsSettingsPanel } from "@/components/settings/AgentsSettingsPanel";
import { OpenHandsSettingsPanel } from "@/components/settings/OpenHandsSettingsPanel";
import { PlaywrightSettingsPanel } from "@/components/settings/PlaywrightSettingsPanel";
import { LighthouseSettingsPanel } from "@/components/settings/LighthouseSettingsPanel";
import { ResearchSettingsPanel } from "@/components/settings/ResearchSettingsPanel";
import { StitchSettingsPanel } from "@/components/settings/StitchSettingsPanel";
import { ProfileSettingsPanel } from "@/components/settings/ProfileSettingsPanel";
import { SystemSettingsPanel } from "@/components/settings/SystemSettingsPanel";

type SettingsTab = "profile" | "keys" | "agents" | "system";

const TABS: { id: SettingsTab; label: string }[] = [
  { id: "profile", label: "Mon profil" },
  { id: "keys", label: "Clés API" },
  { id: "agents", label: "Agents IA" },
  { id: "system", label: "Système" },
];

/**
 * Paramètres — profil, clés API, agents et système.
 */
export function SettingsPage() {
  const [tab, setTab] = useState<SettingsTab>("profile");

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <p className="cf-section-label mb-2">Configuration</p>
        <h1 className="cf-page-title">Paramètres</h1>
        <p className="mt-2 text-sm text-cf-muted">
          Profil CapCore, clés API, modules de génération et maintenance système.
        </p>
      </header>

      <nav className="flex flex-wrap gap-2 border-b border-cf-border-input pb-1">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`cf-subtab mb-1 ${tab === item.id ? "cf-subtab-active" : ""}`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <section className="rounded-card border border-cf-border-input bg-cf-card p-6 shadow-card">
        {tab === "profile" ? <ProfileSettingsPanel /> : null}
        {tab === "keys" ? <ApiKeysSettingsPanel /> : null}
        {tab === "agents" ? (
          <>
            <OpenHandsSettingsPanel />
            <ResearchSettingsPanel />
            <StitchSettingsPanel />
            <PlaywrightSettingsPanel />
            <LighthouseSettingsPanel />
            <AgentsSettingsPanel />
          </>
        ) : null}
        {tab === "system" ? <SystemSettingsPanel /> : null}
      </section>
    </div>
  );
}

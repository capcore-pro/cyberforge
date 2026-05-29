import type { ReactNode } from "react";
import { APP_NAME } from "@shared/constants";
import { BackendStatusBanner } from "@/components/BackendStatusBanner";
import { ContactNotificationToast } from "@/components/ContactNotificationToast";
import { useContactNotifications } from "@/context/ContactNotificationsContext";
import { useAgentsStatus } from "@/context/AgentsStatusContext";
import { enabledAgentCount } from "@/lib/agent-preferences";
import {
  PRIMARY_NAV_ITEMS,
  SETTINGS_NAV_ITEM,
  type AppPage,
} from "@/lib/navigation";

interface AppShellProps {
  currentPage: AppPage;
  onNavigate: (page: AppPage) => void;
  children: ReactNode;
  sidebarFooter?: ReactNode;
}

function NavButton({
  item,
  currentPage,
  unreadCount,
  onNavigate,
}: {
  item: (typeof PRIMARY_NAV_ITEMS)[number] | typeof SETTINGS_NAV_ITEM;
  currentPage: AppPage;
  unreadCount: number;
  onNavigate: (page: AppPage) => void;
}) {
  return (
    <button
      key={item.id}
      type="button"
      disabled={!item.enabled}
      onClick={() => item.enabled && onNavigate(item.id)}
      className={`cyber-nav-item w-full text-left ${
        currentPage === item.id ? "cyber-nav-item-active" : ""
      } ${!item.enabled ? "cursor-not-allowed opacity-40" : ""}`}
    >
      <span className="relative text-cf-gold" aria-hidden>
        {item.icon}
        {item.id === "clients" && unreadCount > 0 ? (
          <span
            className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-cf-alert px-1 text-[9px] font-bold text-black"
            aria-label={`${unreadCount} nouveau(x) contact(s)`}
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        ) : null}
      </span>
      {item.label}
    </button>
  );
}

/**
 * Mise en page avec barre latérale et zone de contenu principale.
 */
export function AppShell({
  currentPage,
  onNavigate,
  children,
  sidebarFooter,
}: AppShellProps) {
  const { unreadCount } = useContactNotifications();
  const { activeCount, totalAgents } = useAgentsStatus();
  const localEnabled = enabledAgentCount();

  return (
    <div className="flex h-full min-h-0 w-full">
      <aside className="cyber-sidebar">
        <div className="border-b border-cf-border px-4 py-5">
          <p className="cf-section-label">Navigation</p>
          <p className="mt-1 text-sm font-medium text-cf-text">{APP_NAME}</p>
        </div>

        <nav
          className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto p-3"
          aria-label="Navigation principale"
        >
          {PRIMARY_NAV_ITEMS.map((item) => (
            <NavButton
              key={item.id}
              item={item}
              currentPage={currentPage}
              unreadCount={unreadCount}
              onNavigate={onNavigate}
            />
          ))}

          <div className="mt-auto border-t border-cf-border pt-2">
            <NavButton
              item={SETTINGS_NAV_ITEM}
              currentPage={currentPage}
              unreadCount={unreadCount}
              onNavigate={onNavigate}
            />
          </div>
        </nav>

        {sidebarFooter ?? (
          <div className="border-t border-cf-border p-4">
            <p className="cf-section-label">Agents</p>
            <p className="mt-1 text-2xl font-medium tabular-nums text-cf-gold">
              {localEnabled} / {totalAgents}
            </p>
            <p className="text-[11px] text-cf-muted">
              {activeCount} actifs côté serveur
            </p>
          </div>
        )}
      </aside>

      <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden bg-cf-main">
        <ContactNotificationToast />
        <BackendStatusBanner />
        <div className="relative flex-1 overflow-y-auto p-6 md:p-8">{children}</div>
      </div>
    </div>
  );
}

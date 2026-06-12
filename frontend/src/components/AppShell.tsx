import { type ReactNode } from "react";
import { BackendStatusBanner } from "@/components/BackendStatusBanner";
import { ContactNotificationToast } from "@/components/ContactNotificationToast";
import { NotificationBell } from "@/components/NotificationBell";
import { useContactNotifications } from "@/context/ContactNotificationsContext";
import {
  formatAgentsCountDisplay,
  useAgentsStatus,
} from "@/context/AgentsStatusContext";
import { useBackendHealth } from "@/context/BackendHealthContext";
import {
  SETTINGS_NAV_ITEM,
  SIDEBAR_NAV_GROUPS,
  type AppPage,
  type NavItem,
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
  item: NavItem | typeof SETTINGS_NAV_ITEM;
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
        {item.iconClass ? <i className={item.iconClass} /> : item.icon}
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
  const { activeCount, totalAgents, agentsCountKnown, loading } =
    useAgentsStatus();
  const { status: backendStatus, health } = useBackendHealth();
  const version = window.cyberforge?.getVersion?.() ?? "—";

  return (
    <div className="flex h-full min-h-0 w-full">
      <aside className="cyber-sidebar">
        <div className="border-b border-cf-border px-4 py-5">
          <button
            type="button"
            onClick={() => onNavigate("dashboard")}
            className="block w-full text-left focus:outline-none focus-visible:ring-1 focus-visible:ring-cf-gold/50"
            aria-label="Accueil CapCore"
          >
            <img
              src="/logo-capcore-dark.svg"
              alt="CapCore Studio Digital"
              className="h-9 w-auto max-w-full"
              width={195}
              height={45}
            />
          </button>

          <div className="mt-5 flex items-center gap-3 rounded-control border border-white/10 bg-white/5 p-3 backdrop-blur-xl">
            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-cf-gold/25 bg-cf-gold/10 text-sm font-semibold text-cf-gold">
              MG
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-cf-text">
                Mat Gibiard
              </p>
              <p className="truncate text-[11px] text-cf-muted">
                Fondateur CapCore
              </p>
            </div>
          </div>
        </div>

        <nav
          className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto p-3"
          aria-label="Navigation principale"
        >
          {SIDEBAR_NAV_GROUPS.map((group, groupIndex) => (
            <div
              key={group.id}
              className={groupIndex > 0 ? "mt-2 border-t border-cf-border pt-2" : ""}
            >
              {group.items.map((item) => (
                <NavButton
                  key={item.id}
                  item={item}
                  currentPage={currentPage}
                  unreadCount={unreadCount}
                  onNavigate={onNavigate}
                />
              ))}
            </div>
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
          <div className="space-y-3 border-t border-cf-border p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
                Statut backend
              </p>
              <span className="inline-flex items-center gap-2 text-[11px] font-semibold text-cf-body">
                <span
                  className={[
                    "h-2.5 w-2.5 rounded-full",
                    backendStatus === "online"
                      ? "bg-emerald-400"
                      : backendStatus === "offline"
                        ? "bg-red-400"
                        : "bg-orange-300",
                  ].join(" ")}
                  aria-hidden
                />
                {backendStatus === "online"
                  ? "En ligne"
                  : backendStatus === "offline"
                    ? "Hors ligne"
                    : "Connexion…"}
              </span>
            </div>

            <div className="rounded-control border border-white/10 bg-white/5 p-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cf-muted">
                Agents
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-cf-gold">
                {formatAgentsCountDisplay({
                  activeCount,
                  totalAgents,
                  agentsCountKnown,
                  loading,
                })}
              </p>
              <p className="text-[11px] text-cf-muted">actifs côté serveur</p>
            </div>

            <div className="flex items-center justify-between gap-3 text-[11px] text-cf-muted">
              <span>v{health?.version ?? version}</span>
              <span className="truncate">{health?.app ?? "CapCore"}</span>
            </div>
          </div>
        )}
      </aside>

      <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden bg-cf-main">
        <header className="flex shrink-0 items-center justify-end border-b border-cf-border px-6 py-3 md:px-8">
          <NotificationBell />
        </header>
        <ContactNotificationToast />
        <BackendStatusBanner />
        <div className="relative flex-1 overflow-y-auto p-6 md:p-8">{children}</div>
      </div>
    </div>
  );
}

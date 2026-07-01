import { type ReactNode } from "react";
import { Film } from "lucide-react";
import { BackendStatusBanner } from "@/components/BackendStatusBanner";
import { ContactNotificationToast } from "@/components/ContactNotificationToast";
import { NotificationBell } from "@/components/NotificationBell";
import { useContactNotifications } from "@/context/ContactNotificationsContext";
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
  const isActive = currentPage === item.id;

  return (
    <button
      key={item.id}
      type="button"
      disabled={!item.enabled}
      onClick={() => item.enabled && onNavigate(item.id)}
      className={`cyber-nav-item w-full text-left ${
        isActive ? "cyber-nav-item-active" : ""
      } ${!item.enabled ? "cursor-not-allowed opacity-40" : ""}`}
    >
      <span
        className={`relative ${isActive ? "text-cf-cyan" : "text-cf-gold"}`}
        aria-hidden
      >
        {item.id === "video_builder" ? (
          <Film size={16} strokeWidth={2} />
        ) : item.iconClass ? (
          <i className={`iconClass ${item.iconClass}`} />
        ) : (
          item.icon
        )}
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

function CapcoreLogoMark({
  onClick,
}: {
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-3 text-left focus:outline-none focus-visible:ring-1 focus-visible:ring-cf-cyan/50"
      aria-label="Accueil CapCore"
    >
      <div
        style={{
          width: 36,
          height: 36,
          background: "linear-gradient(135deg, #00d4ff, #7c3aed)",
          borderRadius: 8,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 0 12px rgba(0,212,255,0.3)",
          fontFamily: "Space Grotesk, sans-serif",
          fontWeight: 700,
          fontSize: 14,
          color: "#030308",
          flexShrink: 0,
        }}
      >
        CF
      </div>
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-cf-text">CyberForge</p>
        <p className="truncate text-[10px] uppercase tracking-[0.18em] text-cf-muted">
          CapCore Studio
        </p>
      </div>
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

  return (
    <div className="flex h-full min-h-0 w-full">
      <aside className="cyber-sidebar">
        <div className="border-b border-cf-cyan-border px-4 py-5">
          <CapcoreLogoMark onClick={() => onNavigate("dashboard")} />

          <div className="mt-5 flex items-center gap-3 rounded-control border border-cf-cyan-border bg-cf-cyan-subtle p-3 backdrop-blur-xl">
            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-cf-cyan-border bg-cf-cyan-subtle text-sm font-semibold text-cf-cyan shadow-glow-cyan">
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
              className={
                groupIndex > 0 ? "mt-2 border-t border-cf-cyan-border pt-2" : ""
              }
            >
              {group.id === "builders" ? (
                <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-cf-muted">
                  Builders
                </p>
              ) : null}
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

          <div className="mt-auto border-t border-cf-cyan-border pt-2">
            <NavButton
              item={SETTINGS_NAV_ITEM}
              currentPage={currentPage}
              unreadCount={unreadCount}
              onNavigate={onNavigate}
            />
          </div>
        </nav>

        {sidebarFooter ?? null}
      </aside>

      <div className="cf-main-area relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex shrink-0 items-center justify-end border-b border-cf-cyan-border bg-[#0a0a12]/80 px-6 py-3 backdrop-blur-md md:px-8">
          <NotificationBell />
        </header>
        <ContactNotificationToast />
        <BackendStatusBanner />
        <div className="relative flex-1 overflow-y-auto p-6 md:p-8">{children}</div>
      </div>
    </div>
  );
}

import { Bell } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useBackendHealth } from "@/context/BackendHealthContext";
import {
  clearSystemNotifications,
  fetchSystemNotifications,
  fetchSystemUnreadCount,
  markAllSystemNotificationsRead,
  markSystemNotificationRead,
  type SystemNotification,
} from "@/lib/system-notifications-api";
import { connectSystemNotificationsStream } from "@/lib/system-notifications-stream";

function levelIcon(level: string): string {
  switch (level) {
    case "success":
      return "✅";
    case "error":
      return "❌";
    case "warning":
      return "⚠️";
    default:
      return "ℹ️";
  }
}

function formatRelativeTime(iso: string): string {
  try {
    const date = new Date(iso);
    const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (seconds < 10) return "à l'instant";
    if (seconds < 60) return `il y a ${seconds} s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `il y a ${minutes} min`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `il y a ${hours} h`;
    const days = Math.floor(hours / 24);
    return `il y a ${days} j`;
  } catch {
    return iso;
  }
}

export function NotificationBell() {
  const { status: backendStatus } = useBackendHealth();
  const [open, setOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [items, setItems] = useState<SystemNotification[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const refreshUnreadCount = useCallback(async () => {
    if (backendStatus !== "online") return;
    const res = await fetchSystemUnreadCount();
    if (res.ok && res.data) {
      setUnreadCount(res.data.count);
    }
  }, [backendStatus]);

  const loadNotifications = useCallback(async () => {
    if (backendStatus !== "online") return;
    setLoadingList(true);
    try {
      const res = await fetchSystemNotifications();
      if (res.ok && res.data) {
        setItems(res.data.items);
      }
    } finally {
      setLoadingList(false);
    }
  }, [backendStatus]);

  useEffect(() => {
    void refreshUnreadCount();
  }, [refreshUnreadCount]);

  useEffect(() => {
    if (!open) return;
    void loadNotifications();
  }, [open, loadNotifications]);

  useEffect(() => {
    if (backendStatus !== "online") return;

    const controller = new AbortController();
    let reconnectTimer: number | undefined;

    const connect = () => {
      void connectSystemNotificationsStream(
        {
          onEvent: (event) => {
            if (event.type === "notification" && !event.data.read) {
              setUnreadCount((prev) => prev + 1);
              setItems((prev) => {
                const exists = prev.some((item) => item.id === event.data.id);
                if (exists) {
                  return prev.map((item) =>
                    item.id === event.data.id ? event.data : item,
                  );
                }
                return [event.data, ...prev].slice(0, 50);
              });
            }
          },
        },
        controller.signal,
      ).catch(() => {
        if (!controller.signal.aborted) {
          reconnectTimer = window.setTimeout(connect, 5000);
        }
      });
    };

    connect();

    return () => {
      controller.abort();
      if (reconnectTimer !== undefined) {
        window.clearTimeout(reconnectTimer);
      }
    };
  }, [backendStatus]);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [open]);

  async function handleMarkRead(notification: SystemNotification) {
    if (notification.read) return;

    setItems((prev) =>
      prev.map((item) =>
        item.id === notification.id ? { ...item, read: true } : item,
      ),
    );
    setUnreadCount((prev) => Math.max(0, prev - 1));

    const res = await markSystemNotificationRead(notification.id);
    if (!res.ok) {
      void refreshUnreadCount();
      void loadNotifications();
    }
  }

  async function handleMarkAllRead() {
    const res = await markAllSystemNotificationsRead();
    if (res.ok) {
      setUnreadCount(0);
      setItems((prev) => prev.map((item) => ({ ...item, read: true })));
    }
  }

  async function handleClearHistory() {
    if (!window.confirm("Vider tout l'historique des notifications ?")) {
      return;
    }
    const res = await clearSystemNotifications();
    if (res.ok) {
      setItems([]);
      setUnreadCount(0);
    }
  }

  const badgeLabel =
    unreadCount > 99 ? "99+" : unreadCount > 0 ? String(unreadCount) : null;

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="relative flex h-9 w-9 items-center justify-center rounded-control border border-cf-border-input bg-cf-secondary text-cf-gold transition hover:border-cf-gold/50 hover:bg-cf-active focus:outline-none focus-visible:ring-1 focus-visible:ring-cf-gold/50"
        aria-label={
          unreadCount > 0
            ? `Notifications (${unreadCount} non lue${unreadCount > 1 ? "s" : ""})`
            : "Notifications"
        }
        aria-expanded={open}
        aria-haspopup="true"
      >
        <Bell className="h-[18px] w-[18px]" strokeWidth={1.75} aria-hidden />
        {badgeLabel ? (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[9px] font-bold text-white">
            {badgeLabel}
          </span>
        ) : null}
      </button>

      {open ? (
        <div
          className="absolute right-0 top-[calc(100%+8px)] z-50 w-[min(22rem,calc(100vw-2rem))] overflow-hidden rounded-card border border-cf-border-input bg-[#0D0D0D] shadow-card"
          role="dialog"
          aria-label="Notifications système"
        >
          <div className="flex items-center justify-between border-b border-cf-border px-4 py-3">
            <h2 className="text-sm font-medium text-cf-text">Notifications</h2>
            <button
              type="button"
              onClick={() => void handleMarkAllRead()}
              className="text-xs text-cf-gold transition hover:text-cf-gold-hover disabled:opacity-40"
              disabled={unreadCount === 0}
            >
              Tout marquer lu
            </button>
          </div>

          <div className="max-h-80 overflow-y-auto">
            {loadingList ? (
              <p className="px-4 py-6 text-center text-sm text-cf-muted">
                Chargement…
              </p>
            ) : items.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm text-cf-muted">
                Aucune notification
              </p>
            ) : (
              <ul className="divide-y divide-cf-border">
                {items.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => void handleMarkRead(item)}
                      className={`w-full px-4 py-3 text-left transition hover:bg-cf-secondary ${
                        item.read ? "bg-transparent" : "bg-cf-gold-subtle/60"
                      }`}
                    >
                      <div className="flex gap-3">
                        <span className="mt-0.5 shrink-0 text-base" aria-hidden>
                          {levelIcon(item.level)}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-start justify-between gap-2">
                            <p
                              className={`text-sm leading-snug ${
                                item.read ? "text-cf-body" : "font-medium text-cf-text"
                              }`}
                            >
                              {item.title}
                            </p>
                            <time
                              className="shrink-0 text-[10px] text-cf-muted"
                              dateTime={item.created_at}
                            >
                              {formatRelativeTime(item.created_at)}
                            </time>
                          </div>
                          {item.message ? (
                            <p className="mt-1 line-clamp-2 text-xs text-cf-muted">
                              {item.message}
                            </p>
                          ) : null}
                          {item.project_name ? (
                            <p className="mt-1 text-[11px] text-cf-gold/80">
                              {item.project_name}
                            </p>
                          ) : null}
                        </div>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="border-t border-cf-border px-4 py-2">
            <button
              type="button"
              onClick={() => void handleClearHistory()}
              className="w-full rounded-control py-2 text-xs text-cf-muted transition hover:bg-cf-secondary hover:text-cf-alert disabled:opacity-40"
              disabled={items.length === 0}
            >
              Vider l&apos;historique
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

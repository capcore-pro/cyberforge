import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  fetchContactNotifications,
  markContactNotificationsSeen,
  type ContactNotificationItem,
} from "@/lib/notifications-api";
import { useBackendHealth } from "@/context/BackendHealthContext";

const POLL_MS = 20_000;
const INITIAL_DELAY_MS = 2_000;

interface ContactNotificationsValue {
  unreadCount: number;
  items: ContactNotificationItem[];
  refresh: () => Promise<void>;
  markAllSeen: () => Promise<void>;
  latestToast: string | null;
  dismissToast: () => void;
}

const ContactNotificationsContext = createContext<ContactNotificationsValue | null>(
  null,
);

export function ContactNotificationsProvider({ children }: { children: ReactNode }) {
  const { status: backendStatus } = useBackendHealth();
  const [unreadCount, setUnreadCount] = useState(0);
  const [items, setItems] = useState<ContactNotificationItem[]>([]);
  const [latestToast, setLatestToast] = useState<string | null>(null);
  const prevCountRef = useRef(0);
  const initializedRef = useRef(false);

  const refresh = useCallback(async () => {
    if (backendStatus !== "online") return;
    try {
      const data = await fetchContactNotifications();
      const count = data.unread_count;
      setUnreadCount(count);
      setItems(data.items);

      if (initializedRef.current && count > prevCountRef.current && data.items.length > 0) {
        const newest = data.items[0];
        setLatestToast(`Nouveau contact : ${newest.title}`);
      }
      prevCountRef.current = count;
      initializedRef.current = true;
    } catch {
      /* backend indisponible — badge inchangé */
    }
  }, [backendStatus]);

  const markAllSeen = useCallback(async () => {
    try {
      await markContactNotificationsSeen();
      setUnreadCount(0);
      setItems([]);
      prevCountRef.current = 0;
    } catch {
      /* ignore */
    }
  }, []);

  const dismissToast = useCallback(() => setLatestToast(null), []);

  useEffect(() => {
    if (backendStatus !== "online") return;

    const initialTimer = window.setTimeout(() => {
      void refresh();
    }, INITIAL_DELAY_MS);

    const pollId = window.setInterval(() => void refresh(), POLL_MS);
    return () => {
      window.clearTimeout(initialTimer);
      window.clearInterval(pollId);
    };
  }, [refresh, backendStatus]);

  return (
    <ContactNotificationsContext.Provider
      value={{
        unreadCount,
        items,
        refresh,
        markAllSeen,
        latestToast,
        dismissToast,
      }}
    >
      {children}
    </ContactNotificationsContext.Provider>
  );
}

export function useContactNotifications(): ContactNotificationsValue {
  const ctx = useContext(ContactNotificationsContext);
  if (!ctx) {
    throw new Error("useContactNotifications doit être utilisé dans ContactNotificationsProvider");
  }
  return ctx;
}

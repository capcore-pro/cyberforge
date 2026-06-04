import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";
import type { ContactNotificationItem } from "@/lib/notifications-api";

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

/**
 * Notifications contacts désactivées (route /api/notifications/contacts retirée).
 */
export function ContactNotificationsProvider({ children }: { children: ReactNode }) {
  const [latestToast, setLatestToast] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    /* no-op */
  }, []);

  const markAllSeen = useCallback(async () => {
    /* no-op */
  }, []);

  const dismissToast = useCallback(() => setLatestToast(null), []);

  return (
    <ContactNotificationsContext.Provider
      value={{
        unreadCount: 0,
        items: [],
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

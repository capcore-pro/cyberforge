import { useEffect } from "react";
import { useContactNotifications } from "@/context/ContactNotificationsContext";

const AUTO_DISMISS_MS = 8000;

/**
 * Toast en haut à droite pour les nouveaux contacts démo.
 */
export function ContactNotificationToast() {
  const { latestToast, dismissToast } = useContactNotifications();

  useEffect(() => {
    if (!latestToast) return;
    const id = window.setTimeout(dismissToast, AUTO_DISMISS_MS);
    return () => window.clearTimeout(id);
  }, [latestToast, dismissToast]);

  if (!latestToast) return null;

  return (
    <div
      className="cyber-contact-toast"
      role="status"
      aria-live="polite"
    >
      <p className="text-sm font-medium text-cyber-text">{latestToast}</p>
      <button
        type="button"
        className="mt-2 text-xs text-cf-muted underline hover:text-cf-gold"
        onClick={dismissToast}
      >
        Fermer
      </button>
    </div>
  );
}

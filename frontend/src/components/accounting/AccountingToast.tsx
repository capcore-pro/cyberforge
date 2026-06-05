import { useEffect } from "react";

export function AccountingToast({
  message,
  onDismiss,
}: {
  message: string | null;
  onDismiss: () => void;
}) {
  useEffect(() => {
    if (!message) return;
    const timer = window.setTimeout(onDismiss, 4000);
    return () => window.clearTimeout(timer);
  }, [message, onDismiss]);

  if (!message) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[9999] max-w-sm rounded-lg border border-white/10 bg-[#0f0f0f]/95 px-4 py-3 text-sm text-white/75 shadow-[0_8px_32px_rgba(0,0,0,0.45)] backdrop-blur-xl"
      role="status"
    >
      {message}
    </div>
  );
}

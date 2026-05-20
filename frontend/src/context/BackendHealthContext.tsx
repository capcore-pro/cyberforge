import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { API_PREFIX } from "@shared/constants";
import { apiRequest } from "@/lib/api-client";

export type BackendConnectionStatus = "loading" | "online" | "offline";

interface HealthPayload {
  status?: string;
  app?: string;
  version?: string;
}

interface BackendHealthContextValue {
  status: BackendConnectionStatus;
  health: HealthPayload | null;
  refresh: () => Promise<void>;
}

const BackendHealthContext = createContext<BackendHealthContextValue | null>(
  null,
);

const POLL_MS = 3000;

export function BackendHealthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<BackendConnectionStatus>("loading");
  const [health, setHealth] = useState<HealthPayload | null>(null);

  const refresh = useCallback(async () => {
    try {
      const response = await apiRequest<HealthPayload>({
        method: "GET",
        path: `${API_PREFIX}/health`,
        timeoutMs: 5000,
      });
      if (response.ok) {
        setStatus("online");
        setHealth(response.data ?? null);
      } else {
        setStatus("offline");
        setHealth(null);
      }
    } catch {
      setStatus("offline");
      setHealth(null);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function tick() {
      if (!cancelled) await refresh();
    }

    void tick();
    const id = window.setInterval(() => void tick(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [refresh]);

  const value = useMemo(
    () => ({ status, health, refresh }),
    [status, health, refresh],
  );

  return (
    <BackendHealthContext.Provider value={value}>
      {children}
    </BackendHealthContext.Provider>
  );
}

export function useBackendHealth(): BackendHealthContextValue {
  const ctx = useContext(BackendHealthContext);
  if (!ctx) {
    throw new Error("useBackendHealth doit être utilisé dans BackendHealthProvider");
  }
  return ctx;
}

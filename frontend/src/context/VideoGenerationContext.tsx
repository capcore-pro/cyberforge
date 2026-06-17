import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

interface VideoGenerationContextValue {
  active: boolean;
  setActive: (active: boolean) => void;
}

const VideoGenerationContext =
  createContext<VideoGenerationContextValue | null>(null);

export function VideoGenerationProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState(false);

  const setActiveStable = useCallback((value: boolean) => {
    setActive(value);
  }, []);

  const value = useMemo(
    () => ({ active, setActive: setActiveStable }),
    [active, setActiveStable],
  );

  return (
    <VideoGenerationContext.Provider value={value}>
      {children}
    </VideoGenerationContext.Provider>
  );
}

export function useVideoGeneration(): VideoGenerationContextValue {
  const ctx = useContext(VideoGenerationContext);
  if (!ctx) {
    throw new Error(
      "useVideoGeneration doit être utilisé dans VideoGenerationProvider",
    );
  }
  return ctx;
}

export function useVideoGenerationOptional(): VideoGenerationContextValue | null {
  return useContext(VideoGenerationContext);
}

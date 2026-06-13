import AsyncStorage from "@react-native-async-storage/async-storage";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import { DEFAULT_BASE_URL } from "./api";

interface AppStore {
  baseUrl: string;
  setBaseUrl: (url: string) => void;
  pushToken: string | null;
  setPushToken: (token: string | null) => void;
  pushEnabled: boolean;
  setPushEnabled: (enabled: boolean) => void;
}

export const useAppStore = create<AppStore>()(
  persist(
    (set) => ({
      baseUrl: DEFAULT_BASE_URL,
      setBaseUrl: (url) => set({ baseUrl: url.trim() || DEFAULT_BASE_URL }),
      pushToken: null,
      setPushToken: (token) => set({ pushToken: token }),
      pushEnabled: false,
      setPushEnabled: (enabled) => set({ pushEnabled: enabled }),
    }),
    {
      name: "cyberforge-mobile",
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        baseUrl: state.baseUrl,
        pushToken: state.pushToken,
        pushEnabled: state.pushEnabled,
      }),
    },
  ),
);

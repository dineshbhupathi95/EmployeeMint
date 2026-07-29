import { create } from "zustand";
import { applyTheme, readStoredTheme, type ThemeId, THEMES } from "@/lib/theme";

export type { ThemeId };
export { THEMES };

interface ThemeState {
  theme: ThemeId;
  setTheme: (theme: ThemeId) => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: readStoredTheme(),
  setTheme: (theme) => {
    applyTheme(theme);
    set({ theme });
  },
}));

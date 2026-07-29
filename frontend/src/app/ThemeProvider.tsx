import type { ReactNode } from "react";
import { useEffect } from "react";
import { applyTheme } from "@/lib/theme";
import { useThemeStore } from "@/store/theme";

export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = useThemeStore((s) => s.theme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  return <>{children}</>;
}

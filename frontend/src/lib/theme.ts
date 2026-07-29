export type ThemeId = "blue" | "emerald" | "violet" | "red";

const STORAGE_KEY = "employeemint-theme-id";
const STYLE_ID = "employeemint-theme-vars";

export const THEMES: { id: ThemeId; label: string; swatch: string }[] = [
  { id: "blue", label: "Blue", swatch: "#2563eb" },
  { id: "emerald", label: "Emerald", swatch: "#059669" },
  { id: "violet", label: "Violet", swatch: "#7c3aed" },
  { id: "red", label: "Red", swatch: "#e11d48" },
];

const PALETTES: Record<ThemeId, Record<string, string>> = {
  blue: {
    "--brand-50": "#eff6ff",
    "--brand-100": "#dbeafe",
    "--brand-200": "#bfdbfe",
    "--brand-500": "#3b82f6",
    "--brand-600": "#2563eb",
    "--brand-700": "#1d4ed8",
    "--brand-900": "#1e3a8a",
  },
  emerald: {
    "--brand-50": "#ecfdf5",
    "--brand-100": "#d1fae5",
    "--brand-200": "#a7f3d0",
    "--brand-500": "#10b981",
    "--brand-600": "#059669",
    "--brand-700": "#047857",
    "--brand-900": "#064e3b",
  },
  violet: {
    "--brand-50": "#f5f3ff",
    "--brand-100": "#ede9fe",
    "--brand-200": "#ddd6fe",
    "--brand-500": "#8b5cf6",
    "--brand-600": "#7c3aed",
    "--brand-700": "#6d28d9",
    "--brand-900": "#4c1d95",
  },
  red: {
    "--brand-50": "#fff1f2",
    "--brand-100": "#ffe4e6",
    "--brand-200": "#fecdd3",
    "--brand-500": "#f43f5e",
    "--brand-600": "#e11d48",
    "--brand-700": "#be123c",
    "--brand-900": "#881337",
  },
};

function normalizeThemeId(value: string | null | undefined): ThemeId | null {
  if (!value) return null;
  if (value === "rose") return "red";
  if (THEMES.some((t) => t.id === value)) return value as ThemeId;
  return null;
}

function injectThemeStyle(theme: ThemeId) {
  const palette = PALETTES[theme];
  const css = `:root, html { ${Object.entries(palette)
    .map(([key, value]) => `${key}: ${value} !important`)
    .join("; ")} }`;

  let el = document.getElementById(STYLE_ID) as HTMLStyleElement | null;
  if (!el) {
    el = document.createElement("style");
    el.id = STYLE_ID;
    document.head.appendChild(el);
  }
  el.textContent = css;
}

export function applyTheme(theme: ThemeId) {
  const root = document.documentElement;
  root.setAttribute("data-theme", theme);

  const palette = PALETTES[theme];
  for (const [key, value] of Object.entries(palette)) {
    root.style.setProperty(key, value);
  }

  injectThemeStyle(theme);
  localStorage.setItem(STORAGE_KEY, theme);
}

export function readStoredTheme(): ThemeId {
  const saved = normalizeThemeId(localStorage.getItem(STORAGE_KEY));
  if (saved) return saved;

  try {
    const raw = localStorage.getItem("employeemint-theme");
    if (raw) {
      const parsed = JSON.parse(raw) as { state?: { theme?: string } };
      const migrated = normalizeThemeId(parsed.state?.theme);
      if (migrated) return migrated;
    }
  } catch {
    /* ignore */
  }

  return "blue";
}

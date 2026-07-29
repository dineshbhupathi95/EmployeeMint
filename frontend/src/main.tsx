import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "@/app/App";
import { readStoredTheme, applyTheme } from "@/lib/theme";
import "@/index.css";

applyTheme(readStoredTheme());

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

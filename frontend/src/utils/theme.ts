import { useCallback, useEffect, useState } from "react";

export type Theme = "light" | "dark";

function current(): Theme {
  return document.documentElement.classList.contains("dark") ? "dark" : "light";
}

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(current);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((t) => {
      const next = t === "dark" ? "light" : "dark";
      try {
        localStorage.setItem("dvs-theme", next);
      } catch {
        /* storage may be unavailable (private mode) */
      }
      return next;
    });
  }, []);

  return [theme, toggle];
}

/** Tracks the <html class="dark"> flag (for widgets that need an explicit theme). */
export function useIsDark(): boolean {
  const [dark, setDark] = useState(() => current() === "dark");
  useEffect(() => {
    const obs = new MutationObserver(() => setDark(current() === "dark"));
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);
  return dark;
}

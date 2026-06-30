import { useEffect, useState } from "react";

export type Theme = "dark" | "light";

const KEY = "beacon-theme";

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem(KEY);
    if (saved === "dark" || saved === "light") return saved;
    return window.matchMedia?.("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark";
  });

  useEffect(() => {
    localStorage.setItem(KEY, theme);
  }, [theme]);

  const toggle = () => setTheme((t) => (t === "dark" ? "light" : "dark"));
  return [theme, toggle];
}

const CUE_KEY = "beacon-shape-cues";

/** Non-colour status cue (pattern/shape alongside colour) — an a11y option. */
export function useShapeCues(): [boolean, () => void] {
  const [on, setOn] = useState<boolean>(() => localStorage.getItem(CUE_KEY) === "1");

  useEffect(() => {
    localStorage.setItem(CUE_KEY, on ? "1" : "0");
  }, [on]);

  return [on, () => setOn((v) => !v)];
}

// Palette/colour helpers + time/day formatting + importance tiers.
// Ported from the design's model.js; operates over the live config palette.

import type { Effect, PaletteColor, Tier, TriggerType } from "./types";

export const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const FALLBACK_HEX = "#3A3A42";

export function isHex(color: string): boolean {
  return /^#?[0-9A-Fa-f]{6}$/.test(color || "");
}
function normHex(color: string): string {
  return color.startsWith("#") ? color : "#" + color;
}

/** Resolve a colour value (slot name or "#RRGGBB") to a display hex. */
export function hexOf(palette: PaletteColor[], color: string): string {
  if (isHex(color)) return normHex(color);
  const p = palette.find((s) => s.slot === color);
  if (!p) return FALLBACK_HEX;
  return p.off ? FALLBACK_HEX : p.hex;
}

export function nameOf(palette: PaletteColor[], color: string): string {
  if (isHex(color)) return "Custom";
  const p = palette.find((s) => s.slot === color);
  return p ? p.name : color;
}

export function isOff(palette: PaletteColor[], color: string): boolean {
  if (isHex(color)) return false;
  const p = palette.find((s) => s.slot === color);
  return p ? p.off : false;
}

/** Selectable slots = everything except the special "off" slot. */
export function selectable(palette: PaletteColor[]): PaletteColor[] {
  return palette.filter((s) => !s.off);
}

export function fmt12(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  const ap = h < 12 ? "am" : "pm";
  const hh = ((h + 11) % 12) + 1;
  return `${hh}:${String(m).padStart(2, "0")}${ap}`;
}

export function daysLabel(days: number[]): string {
  if (days.length === 7) return "Every day";
  if (days.length === 5 && [0, 1, 2, 3, 4].every((d) => days.includes(d)))
    return "Weekdays";
  if (days.length === 2 && days.includes(5) && days.includes(6)) return "Weekends";
  return days
    .slice()
    .sort((a, b) => a - b)
    .map((d) => DAYS[d])
    .join(" · ");
}

/** Soften a vivid LED colour for on-screen rendering (display only). */
export function screenSoften(hex: string): string {
  const c = hex.replace("#", "");
  if (c.length < 6) return hex;
  let r = parseInt(c.slice(0, 2), 16);
  let g = parseInt(c.slice(2, 4), 16);
  let b = parseInt(c.slice(4, 6), 16);
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  const mix = 0.18;
  const dim = 0.9;
  r = Math.round((r * (1 - mix) + lum * mix) * dim);
  g = Math.round((g * (1 - mix) + lum * mix) * dim);
  b = Math.round((b * (1 - mix) + lum * mix) * dim);
  const h = (n: number) => Math.max(0, Math.min(255, n)).toString(16).padStart(2, "0");
  return `#${h(r)}${h(g)}${h(b)}`;
}

/** Scale a hex toward black by factor 0..1 (on-screen brightness preview). */
export function applyBrightness(hex: string, factor: number): string {
  const c = hex.replace("#", "");
  if (c.length < 6) return hex;
  const f = Math.max(0, Math.min(1, factor));
  const r = Math.round(parseInt(c.slice(0, 2), 16) * f);
  const g = Math.round(parseInt(c.slice(2, 4), 16) * f);
  const b = Math.round(parseInt(c.slice(4, 6), 16) * f);
  const h = (n: number) => Math.max(0, Math.min(255, n)).toString(16).padStart(2, "0");
  return `#${h(r)}${h(g)}${h(b)}`;
}

export function hslToHex(h: number, s: number, l: number): string {
  s /= 100;
  l /= 100;
  const k = (n: number) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  const to = (x: number) => Math.round(255 * x).toString(16).padStart(2, "0");
  return "#" + to(f(0)) + to(f(8)) + to(f(4));
}

export function hexToHsl(hex: string): { h: number; s: number; l: number } {
  let c = hex.replace("#", "");
  if (c.length < 6) c = "3dd68c";
  const r = parseInt(c.slice(0, 2), 16) / 255;
  const g = parseInt(c.slice(2, 4), 16) / 255;
  const b = parseInt(c.slice(4, 6), 16) / 255;
  const max = Math.max(r, g, b),
    min = Math.min(r, g, b);
  let h = 0,
    s = 0;
  const l = (max + min) / 2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    h *= 60;
  }
  return { h: Math.round(h), s: Math.round(s * 100), l: Math.round(l * 100) };
}

/** WCAG-ish ink colour for text/icons on a colour fill. */
export function inkFor(hex: string): string {
  const c = hex.replace("#", "");
  if (c.length < 6) return "#ffffff";
  const r = parseInt(c.slice(0, 2), 16) / 255;
  const g = parseInt(c.slice(2, 4), 16) / 255;
  const b = parseInt(c.slice(4, 6), 16) / 255;
  const L = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return L > 0.6 ? "#10130f" : "#ffffff";
}

/* ---------- importance tiers (UI sugar over numeric priority) ---------- */

export const OVERRIDE_PRIORITY = 50;

export const TIERS: { id: Tier; label: string }[] = [
  { id: "low", label: "Low" },
  { id: "normal", label: "Normal" },
  { id: "high", label: "High" },
  { id: "critical", label: "Critical" },
];

const PRIORITY_BY_TIER: Record<Tier, number> = {
  low: 20,
  normal: 40,
  high: 70,
  critical: 90,
};

/** Map a 0..100 priority to a named tier. High/Critical sit above override. */
export function tierOf(priority: number): Tier {
  if (priority >= 80) return "critical";
  if (priority >= 55) return "high";
  if (priority >= 30) return "normal";
  return "low";
}

export function priorityOf(tier: Tier): number {
  return PRIORITY_BY_TIER[tier] ?? 40;
}

export function tierLabel(tier: Tier): string {
  return TIERS.find((t) => t.id === tier)?.label ?? "Normal";
}

/* ---------- effects (the design's reduced set) ---------- */

export const EFFECTS = [
  { id: "solid", name: "Solid" },
  { id: "fade", name: "Fade" },
  { id: "strobe", name: "Strobe" },
];

export function effectType(effect?: Effect | null): string {
  const t = effect?.type ?? "solid";
  return EFFECTS.some((e) => e.id === t) ? t : "solid";
}

export function effectName(effect?: Effect | null): string {
  const t = effectType(effect);
  return EFFECTS.find((e) => e.id === t)?.name ?? "Solid";
}

/** Build a full Effect dict (engine normalizes, but keep the shape valid). */
export function makeEffect(type: string, base?: Effect | null): Effect {
  return {
    type,
    speed: base?.speed ?? 40,
    wave_type: base?.wave_type ?? 1,
    pattern_id: base?.pattern_id ?? 1,
  };
}

/* ---------- trigger type → icon ---------- */

export function triggerIcon(type: TriggerType): string {
  switch (type) {
    case "webcam":
      return "webcam";
    case "lock":
      return "lock";
    case "hotkey":
      return "keyboard";
    default:
      return "mic";
  }
}

/* ---------- hotkey combo formatting ---------- */

export interface HotkeyCombo {
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
  win?: boolean;
  key?: string;
  vk?: number;
}

/** "Ctrl + Alt + B" — human label for a captured combo. */
export function hotkeyLabel(p: HotkeyCombo | undefined): string {
  if (!p || !p.key) return "Not set";
  const parts: string[] = [];
  if (p.ctrl) parts.push("Ctrl");
  if (p.win) parts.push("Win");
  if (p.alt) parts.push("Alt");
  if (p.shift) parts.push("Shift");
  parts.push(p.key);
  return parts.join(" + ");
}

export function hotkeyValid(p: HotkeyCombo | undefined): boolean {
  return !!p && !!p.key && !!(p.ctrl || p.alt || p.shift || p.win);
}

/** Capture a browser KeyboardEvent into a combo (modifiers + key + Win VK). */
export function captureHotkey(e: KeyboardEvent): HotkeyCombo | null {
  const k = e.key;
  // ignore lone modifier presses — wait for the real key
  if (["Control", "Alt", "Shift", "Meta", "OS"].includes(k)) return null;
  let key = "";
  let vk = 0;
  if (/^[a-zA-Z]$/.test(k)) {
    key = k.toUpperCase();
    vk = key.charCodeAt(0); // A-Z -> 65-90
  } else if (/^[0-9]$/.test(k)) {
    key = k;
    vk = k.charCodeAt(0); // 0-9 -> 48-57
  } else if (/^F([1-9]|1[0-9]|2[0-4])$/.test(k)) {
    key = k;
    vk = 111 + Number(k.slice(1)); // F1 -> 112
  } else if (k === " " || k === "Spacebar") {
    key = "Space";
    vk = 0x20;
  } else {
    const map: Record<string, [string, number]> = {
      Enter: ["Enter", 0x0d],
      Tab: ["Tab", 0x09],
      Escape: ["Esc", 0x1b],
      ArrowUp: ["Up", 0x26],
      ArrowDown: ["Down", 0x28],
      ArrowLeft: ["Left", 0x25],
      ArrowRight: ["Right", 0x27],
      ".": [".", 0xbe],
      ",": [",", 0xbc],
      "/": ["/", 0xbf],
      ";": [";", 0xba],
    };
    const m = map[k];
    if (!m) return null; // unsupported key — keep listening
    [key, vk] = m;
  }
  return { ctrl: e.ctrlKey, alt: e.altKey, shift: e.shiftKey, win: e.metaKey, key, vk };
}

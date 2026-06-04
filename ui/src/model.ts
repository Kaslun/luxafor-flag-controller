// Palette helpers + time/day formatting, ported from the design's model.jsx.
// The palette is fetched from /api/palette at runtime; these helpers operate
// over that fetched list.

import type { PaletteSlot } from "./types";

export const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const FALLBACK_HEX = "#3A3A42";

export function isHex(color: string): boolean {
  return /^#?[0-9A-Fa-f]{6}$/.test(color || "");
}

function normHex(color: string): string {
  return color.startsWith("#") ? color : "#" + color;
}

/** Resolve a color value (slot name or "#RRGGBB") to a display hex. */
export function hexOf(palette: PaletteSlot[], color: string): string {
  if (isHex(color)) return normHex(color);
  const p = palette.find((s) => s.slot === color);
  if (!p) return FALLBACK_HEX;
  return p.off ? FALLBACK_HEX : p.hex;
}

export function nameOf(palette: PaletteSlot[], color: string): string {
  if (isHex(color)) return "Custom";
  const p = palette.find((s) => s.slot === color);
  return p ? p.name : color;
}

export function isOff(palette: PaletteSlot[], color: string): boolean {
  if (isHex(color)) return false;
  const p = palette.find((s) => s.slot === color);
  return p ? p.off : false;
}

/** Selectable slots = everything except the special "off" slot. */
export function selectable(palette: PaletteSlot[]): PaletteSlot[] {
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

/** Pick the accent color for the current resolved status. Falls back to a
 *  calm indigo when the flag is off (matches the design's behavior). */
export function accentFor(
  palette: PaletteSlot[],
  slot: string,
  off: boolean,
  theme: "dark" | "light"
): string {
  if (off) return theme === "dark" ? "#7C84FF" : "#5B63E0";
  return hexOf(palette, slot);
}

/** Soften a vivid LED color for on-screen rendering.
 *  Pure values like #00FF00 are harsh on a monitor but look pleasant on the
 *  diffused physical flag; this dims + slightly de-saturates so the on-screen
 *  flag preview reads like the real thing. Display-only — never sent to the
 *  device. */
export function screenSoften(hex: string): string {
  const c = hex.replace("#", "");
  if (c.length < 6) return hex;
  let r = parseInt(c.slice(0, 2), 16);
  let g = parseInt(c.slice(2, 4), 16);
  let b = parseInt(c.slice(4, 6), 16);
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  const mix = 0.18; // pull toward the channel's luminance to cut neon harshness
  const dim = 0.9;
  r = Math.round((r * (1 - mix) + lum * mix) * dim);
  g = Math.round((g * (1 - mix) + lum * mix) * dim);
  b = Math.round((b * (1 - mix) + lum * mix) * dim);
  const h = (n: number) => Math.max(0, Math.min(255, n)).toString(16).padStart(2, "0");
  return `#${h(r)}${h(g)}${h(b)}`;
}

/** WCAG-ish ink color for text on an accent background. */
export function inkFor(hex: string): string {
  const c = hex.replace("#", "");
  if (c.length < 6) return "#ffffff";
  const r = parseInt(c.slice(0, 2), 16) / 255;
  const g = parseInt(c.slice(2, 4), 16) / 255;
  const b = parseInt(c.slice(4, 6), 16) / 255;
  const L = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return L > 0.6 ? "#1a1500" : "#ffffff";
}

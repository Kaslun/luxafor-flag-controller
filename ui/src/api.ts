// Typed fetch wrappers for the engine's localhost API.

import type {
  Config,
  Effect,
  EffectsMeta,
  PaletteSlot,
  Signals,
  State,
  TriggerMeta,
} from "./types";

async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url} -> ${r.status}`);
  return r.json() as Promise<T>;
}

async function send(method: string, url: string, body?: unknown): Promise<Response> {
  const r = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    let detail = `${method} ${url} -> ${r.status}`;
    try {
      const j = await r.json();
      if (j.detail) detail = j.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return r;
}

export const api = {
  getState: () => getJSON<State>("/api/state"),
  getConfig: () => getJSON<Config>("/api/config"),
  getPalette: () => getJSON<PaletteSlot[]>("/api/palette"),
  getEffects: () => getJSON<EffectsMeta>("/api/effects"),
  getTriggerMeta: () => getJSON<TriggerMeta>("/api/triggers/meta"),
  getSignals: () => getJSON<Signals>("/api/signals"),

  putConfig: (cfg: Config) => send("PUT", "/api/config", cfg),

  setOverride: (
    color: string,
    durationMinutes: number | null,
    effect?: Effect | null
  ) =>
    send("POST", "/api/override", {
      color,
      duration_minutes: durationMinutes,
      effect: effect ?? null,
    }),
  clearOverride: () => send("DELETE", "/api/override"),

  setPreview: (color: string, effect?: Effect | null) =>
    send("POST", "/api/preview", { color, effect: effect ?? null }),
  clearPreview: () => send("DELETE", "/api/preview"),

  pause: () => send("POST", "/api/pause"),
  resume: () => send("DELETE", "/api/pause"),

  recheckConflict: () => send("POST", "/api/conflict/recheck"),
  recheckUpdate: () => send("POST", "/api/update/recheck"),
  applyUpdate: () => send("POST", "/api/update/apply"),
  openLogs: () => send("POST", "/api/logs/open"),

  setAutostart: (enabled: boolean) =>
    send(enabled ? "POST" : "DELETE", "/api/autostart"),
};

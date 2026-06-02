// Wire types mirroring the engine's State / Config / palette contracts.

export type Kind =
  | "paused"
  | "disconnected"
  | "call"
  | "override"
  | "routine"
  | "available"
  | "off"
  | "dim";

export interface ManualOverride {
  color: string;
  expiry: string | null; // ISO timestamp, or null = until cleared
}

export interface UpdateAvailable {
  version: string;
  url: string;
}

export interface ConflictDetected {
  luxafor_v2_running: boolean;
  luxafor_v2_startup: boolean;
}

export interface State {
  color: string;
  routine: string;
  kind: Kind;
  reason: string;
  paused: boolean;
  in_call: boolean;
  device_connected: boolean;
  manual_override: ManualOverride | null;
  update_available: UpdateAvailable | null;
  conflict_detected: ConflictDetected | null;
  updated_at: string;
}

export interface Routine {
  id: string;
  name: string;
  enabled: boolean;
  days: number[]; // Mon=0 .. Sun=6
  start: string; // "HH:MM"
  end: string; // "HH:MM"
  color: string; // palette slot
}

export interface Settings {
  call_detection: boolean;
  call_color: string;
  available_color: string;
  off_behavior: string; // "off" | "dim" | <slot>
  heartbeat_interval_seconds: number;
}

export interface Config {
  routines: Routine[];
  settings: Settings;
}

export interface PaletteSlot {
  slot: string;
  name: string;
  hex: string; // "#RRGGBB" or "off"
  meaning: string;
  off: boolean;
}

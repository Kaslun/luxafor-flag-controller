// Wire types mirroring the engine's State / Config / palette contracts.

export type Kind =
  | "paused"
  | "disconnected"
  | "preview"
  | "trigger"
  | "override"
  | "routine"
  | "available"
  | "off"
  | "dim";

export interface Effect {
  type: string; // "solid" | "fade" | "strobe" | "wave" | "pattern"
  speed: number;
  wave_type: number;
  pattern_id: number;
}

export interface ManualOverride {
  color: string;
  expiry: string | null; // ISO timestamp, or null = until cleared
  effect?: Effect | null;
}

export interface EffectsMeta {
  types: string[];
  wave_types: { id: number; name: string }[];
  pattern_ids: { id: number; name: string }[];
  speed_min: number;
  speed_max: number;
  default: Effect;
  color_ignored_types: string[];
}

export interface UpdateAvailable {
  version: string;
  url: string;
}

export interface ConflictDetected {
  luxafor_v2_running: boolean;
  luxafor_v2_startup: boolean;
}

export type TriggerType = "mic" | "mic_app" | "webcam" | "lock";

export interface Trigger {
  id: string;
  name: string;
  enabled: boolean;
  type: TriggerType;
  color: string; // slot name or "#RRGGBB"
  priority: number; // 0..100, higher wins; 50 == manual override
  params: { app?: string };
  effect?: Effect;
}

export interface ActiveTrigger {
  id: string;
  name: string;
  type: TriggerType;
  color: string;
  priority: number;
  effect?: Effect;
}

export interface TriggerMeta {
  types: { id: TriggerType; name: string; needs_app: boolean }[];
  priority_min: number;
  priority_max: number;
  override_priority: number;
}

export interface Signals {
  mic?: boolean;
  webcam?: boolean;
  lock?: boolean;
  mic_capturers?: string[];
  webcam_capturers?: string[];
}

export interface State {
  color: string;
  routine: string;
  kind: Kind;
  reason: string;
  effect: Effect | null;
  paused: boolean;
  in_call: boolean;
  locked: boolean;
  signals: Signals;
  active_triggers: ActiveTrigger[];
  device_connected: boolean;
  manual_override: ManualOverride | null;
  update_available: UpdateAvailable | null;
  conflict_detected: ConflictDetected | null;
  autostart_enabled: boolean;
  version: string;
  updated_at: string;
}

export interface Routine {
  id: string;
  name: string;
  enabled: boolean;
  days: number[]; // Mon=0 .. Sun=6
  start: string; // "HH:MM"
  end: string; // "HH:MM"
  color: string; // palette slot name or "#RRGGBB"
  effect?: Effect;
}

export interface Settings {
  available_color: string;
  off_behavior: string; // "off" | "dim" | <slot>
  heartbeat_interval_seconds: number;
}

export interface Config {
  routines: Routine[];
  triggers: Trigger[];
  settings: Settings;
}

export interface PaletteSlot {
  slot: string;
  name: string;
  hex: string; // "#RRGGBB" or "off"
  meaning: string;
  off: boolean;
}

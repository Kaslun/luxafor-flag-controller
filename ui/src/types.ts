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

export interface EffectsMeta {
  types: string[];
  wave_types: { id: number; name: string }[];
  pattern_ids: { id: number; name: string }[];
  speed_min: number;
  speed_max: number;
  default: Effect;
  color_ignored_types: string[];
}

export interface ManualOverride {
  color: string;
  expiry: string | null;
  effect?: Effect | null;
}

export interface UpdateAvailable {
  version: string;
  url: string;
}

export interface ConflictDetected {
  luxafor_v2_running: boolean;
  luxafor_v2_startup: boolean;
}

/** A user-editable template colour (lives in config.palette). */
export interface PaletteColor {
  slot: string;
  name: string;
  hex: string; // display hex (#RRGGBB), or ignored when off
  off: boolean;
  led?: string | null; // optional LED-tuned hex written to the device
}
export type PaletteSlot = PaletteColor; // back-compat alias

export type TriggerType = "mic" | "mic_app" | "webcam" | "lock" | "hotkey";

export interface HotkeyParams {
  ctrl?: boolean;
  alt?: boolean;
  shift?: boolean;
  win?: boolean;
  key?: string; // display key, e.g. "B", "F5"
  vk?: number; // Win32 virtual-key code
}

export interface Trigger {
  id: string;
  name: string;
  enabled: boolean;
  type: TriggerType;
  color: string;
  priority: number; // 0..100; mapped to/from importance tiers in the UI
  params: { app?: string } & HotkeyParams;
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
  types: { id: TriggerType; name: string; needs_app: boolean; needs_hotkey?: boolean }[];
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

export interface Routine {
  id: string;
  name: string;
  enabled: boolean;
  days: number[]; // Mon=0 .. Sun=6
  start: string; // "HH:MM"
  end: string; // "HH:MM"
  color: string;
  effect?: Effect;
}

export interface Settings {
  available_color: string;
  off_behavior: string; // "off" | "dim" | <slot>
  heartbeat_interval_seconds: number;
  brightness: number; // 10..100
}

export interface Config {
  routines: Routine[];
  triggers: Trigger[];
  palette: PaletteColor[];
  settings: Settings;
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
  focus_seq: number;
  version: string;
  updated_at: string;
}

export type Tier = "low" | "normal" | "high" | "critical";

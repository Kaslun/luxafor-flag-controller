// Modals + banners — ported from the design (modals.jsx), wired to real data.

import { useEffect, useRef, useState } from "react";
import { Icon } from "../icons";
import { Flag } from "./Flag";
import { Switch } from "./controls";
import {
  hexOf,
  hexToHsl,
  hslToHex,
  selectable,
  EFFECTS,
} from "../model";
import type {
  ConflictDetected,
  PaletteColor,
  Settings,
  UpdateAvailable,
} from "../types";

/* ---------------- Hue/saturation wheel ---------------- */
function WheelPicker({ hex, onChange }: { hex: string; onChange: (h: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const { h, s, l } = hexToHsl(hex);
  const R = 96;

  const pick = (clientX: number, clientY: number) => {
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    const dx = clientX - cx;
    const dy = clientY - cy;
    const ang = (Math.atan2(dx, -dy) * 180) / Math.PI;
    const hue = Math.round((ang + 360) % 360);
    const sat = Math.round(Math.min(Math.hypot(dx, dy) / R, 1) * 100);
    onChange(hslToHex(hue, sat, l));
  };
  const onDown = (e: React.PointerEvent) => {
    e.preventDefault();
    pick(e.clientX, e.clientY);
    const mv = (ev: PointerEvent) => pick(ev.clientX, ev.clientY);
    const up = () => {
      window.removeEventListener("pointermove", mv);
      window.removeEventListener("pointerup", up);
    };
    window.addEventListener("pointermove", mv);
    window.addEventListener("pointerup", up);
  };

  const th = (h * Math.PI) / 180;
  const rad = (s / 100) * R;
  const hx = R + rad * Math.sin(th);
  const hy = R - rad * Math.cos(th);

  return (
    <div className="wheel-wrap">
      <div className="wheel" ref={ref} onPointerDown={onDown}>
        <div className="wheel-handle" style={{ left: hx, top: hy, background: hex }} />
      </div>
      <div className="shade-row">
        <span className="shade-lab">Shade</span>
        <input
          type="range"
          min={22}
          max={78}
          value={l}
          style={{
            background: `linear-gradient(90deg, ${hslToHex(h, s, 22)}, ${hslToHex(h, s, 50)}, ${hslToHex(h, s, 78)})`,
          }}
          onChange={(e) => onChange(hslToHex(h, s, Number(e.target.value)))}
        />
      </div>
    </div>
  );
}

export function Scrim({
  onClose,
  z = 40,
  children,
}: {
  onClose: () => void;
  z?: number;
  children: React.ReactNode;
}) {
  // close on Escape (a11y); the topmost scrim wins because keydown fires on
  // the focused document and each mounted Scrim listens while open
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="scrim" style={{ zIndex: z }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()}>{children}</div>
    </div>
  );
}

function ColorFields({
  palette,
  value,
  effect,
  allowEffects,
  hexOnly,
  onColor,
  onEffect,
}: {
  palette: PaletteColor[];
  value: string;
  effect: string;
  allowEffects: boolean;
  hexOnly: boolean;
  onColor: (c: string) => void;
  onEffect: (e: string) => void;
}) {
  const hex = hexOf(palette, value);
  return (
    <>
      {!hexOnly && (
        <div className="field">
          <label>— presets</label>
          <div className="swatch-row">
            {selectable(palette).map((s) => (
              <button
                key={s.slot}
                className={"swatch-chip" + (value === s.slot ? " on" : "")}
                title={s.name}
                onClick={() => onColor(s.slot)}
              >
                <span className="sw" style={{ background: s.hex }} />
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="field">
        <label>— {hexOnly ? "colour" : "or pick your own"}</label>
        <div className="wheel-block">
          <WheelPicker hex={hex} onChange={onColor} />
          <div className="wheel-side">
            <Flag hex={hex} brightness={1} effect={allowEffects ? effect : "solid"} size={84} />
            <div className="hex-field">
              <span className="hexhash">#</span>
              <input
                className="input mono"
                value={hex.replace("#", "").toUpperCase()}
                maxLength={6}
                onChange={(e) => {
                  const v = e.target.value.replace(/[^0-9a-fA-F]/g, "");
                  onColor("#" + v.padEnd(6, "0").slice(0, 6));
                }}
              />
            </div>
          </div>
        </div>
        <p className="hint" style={{ marginTop: 8 }}>
          The flag shows colours more vividly than the screen, so a custom pick
          may look brighter on the device than in this preview.
        </p>
      </div>

      {allowEffects && (
        <div className="field">
          <label>— effect</label>
          <div className="seg seg-wide">
            {EFFECTS.map((e) => (
              <button key={e.id} className={effect === e.id ? "on" : ""} onClick={() => onEffect(e.id)}>
                {e.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

export function ColorPicker({
  palette,
  initial,
  initialEffect = "solid",
  allowEffects = true,
  hexOnly = false,
  title,
  eyebrow,
  z = 60,
  onApply,
  onClose,
}: {
  palette: PaletteColor[];
  initial: string;
  initialEffect?: string;
  allowEffects?: boolean;
  hexOnly?: boolean;
  title?: string;
  eyebrow?: string;
  z?: number;
  onApply: (color: string, effect: string) => void;
  onClose: () => void;
}) {
  const [value, setValue] = useState(initial);
  const [effect, setEffect] = useState(initialEffect);
  return (
    <Scrim onClose={onClose} z={z}>
      <div className="pop" style={{ width: 460 }}>
        <div className="pop-head">
          <div className="eye">{eyebrow || "— colour"}</div>
          <h3>{title || "Pick a colour"}</h3>
        </div>
        <div className="pop-body">
          <ColorFields
            palette={palette}
            value={value}
            effect={effect}
            allowEffects={allowEffects && !hexOnly}
            hexOnly={hexOnly}
            onColor={setValue}
            onEffect={setEffect}
          />
        </div>
        <div className="pop-foot">
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" onClick={() => onApply(value, effect)}>
            <Icon name="check" size={15} /> Apply
          </button>
        </div>
      </div>
    </Scrim>
  );
}

const DURATIONS: [number, string][] = [
  [15, "15 min"],
  [30, "30 min"],
  [60, "1 hour"],
  [0, "Until I clear it"],
];

export function OverridePopover({
  palette,
  current,
  onSet,
  onClose,
}: {
  palette: PaletteColor[];
  current: { color: string } | null;
  onSet: (color: string, dur: number | null, effect: string) => void;
  onClose: () => void;
}) {
  const [value, setValue] = useState(current ? current.color : "busy");
  const [effect, setEffect] = useState("solid");
  const [dur, setDur] = useState(30);
  return (
    <Scrim onClose={onClose} z={50}>
      <div className="pop" style={{ width: 460 }}>
        <div className="pop-head">
          <div className="eye">— manual override</div>
          <h3>Set it by hand</h3>
          <p>A quick status. A High trigger still takes over.</p>
        </div>
        <div className="pop-body">
          <ColorFields
            palette={palette}
            value={value}
            effect={effect}
            allowEffects
            hexOnly={false}
            onColor={setValue}
            onEffect={setEffect}
          />
          <div className="field">
            <label>— for how long</label>
            <div className="durrow">
              {DURATIONS.map(([v, l]) => (
                <button key={v} className={"chip" + (dur === v ? " on" : "")} onClick={() => setDur(v)}>
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="pop-foot">
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" onClick={() => onSet(value, dur === 0 ? null : dur, effect)}>
            <Icon name="check" size={15} /> Set
          </button>
        </div>
      </div>
    </Scrim>
  );
}

export function PaletteEditor({
  palette,
  onChange,
  onRecolor,
  onDelete,
  onClose,
}: {
  palette: PaletteColor[];
  onChange: (p: PaletteColor[]) => void;
  onRecolor: (index: number) => void;
  onDelete: (index: number) => void;
  onClose: () => void;
}) {
  const setSlot = (i: number, patch: Partial<PaletteColor>) =>
    onChange(palette.map((s, idx) => (idx === i ? { ...s, ...patch } : s)));
  const del = (i: number) => onDelete(i);
  const add = () => {
    const slot = "c" + Date.now();
    const last = palette.length - 1; // off is kept last
    onChange([
      ...palette.slice(0, last),
      { slot, name: "New colour", hex: "#3DD68C", off: false },
      palette[last],
    ]);
  };
  return (
    <Scrim onClose={onClose} z={50}>
      <div className="pop" style={{ width: 480 }}>
        <div className="pop-head">
          <div className="eye">— colour palette</div>
          <h3>Your template colours</h3>
          <p>Used across triggers, routines and overrides. Rename, recolour, remove, or add your own.</p>
        </div>
        <div className="pop-body">
          <div className="pal-list">
            {palette.map((s, i) => (
              <div key={s.slot} className={"pal-row" + (s.off ? " locked" : "")}>
                <span
                  className="sw"
                  style={{ background: s.off ? "#222826" : s.hex, opacity: s.off ? 0.6 : 1 }}
                  title={s.off ? "Off can't be recoloured" : "Recolour"}
                  onClick={() => !s.off && onRecolor(i)}
                />
                <input
                  className="nm"
                  value={s.name}
                  onChange={(e) => setSlot(i, { name: e.target.value })}
                  readOnly={s.off}
                />
                <span className="hx">{s.off ? "lights off" : s.hex.toUpperCase()}</span>
                {!s.off ? (
                  <button className="del" title="Delete" onClick={() => del(i)}>
                    <Icon name="trash" size={15} />
                  </button>
                ) : (
                  <span style={{ width: 32 }} />
                )}
              </div>
            ))}
          </div>
        </div>
        <div className="pop-foot between">
          <button className="btn sm" onClick={add}>
            <Icon name="plus" size={14} /> Add colour
          </button>
          <button className="btn primary" onClick={onClose}>
            <Icon name="check" size={15} /> Done
          </button>
        </div>
      </div>
    </Scrim>
  );
}

export function SettingsModal({
  settings,
  palette,
  version,
  autostart,
  update,
  checking,
  shapeCues,
  onToggleShapeCues,
  onChange,
  onToggleAutostart,
  onPickResting,
  onOpenPalette,
  onCheckUpdate,
  onInstallUpdate,
  onOpenLogs,
  onClose,
}: {
  settings: Settings;
  palette: PaletteColor[];
  version: string;
  autostart: boolean;
  update: UpdateAvailable | null;
  checking: boolean;
  shapeCues: boolean;
  onToggleShapeCues: () => void;
  onChange: (s: Settings) => void;
  onToggleAutostart: () => void;
  onPickResting: () => void;
  onOpenPalette: () => void;
  onCheckUpdate: () => void;
  onInstallUpdate: () => void;
  onOpenLogs: () => void;
  onClose: () => void;
}) {
  const ISSUES = "https://github.com/Kaslun/luxafor-flag-controller/issues";
  const restingHex = hexOf(palette, settings.available_color);
  // map engine off_behavior -> the design's off/dim/resting segment
  const offSel =
    settings.off_behavior === "off" ? "off" : settings.off_behavior === "dim" ? "dim" : "resting";
  const setOff = (v: string) =>
    onChange({
      ...settings,
      off_behavior: v === "resting" ? settings.available_color : v,
    });

  return (
    <Scrim onClose={onClose} z={50}>
      <div className="pop" style={{ width: 520, maxHeight: "86vh" }}>
        <div
          className="pop-head"
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
        >
          <h3>Settings</h3>
          <button className="btn sm icon ghost" onClick={onClose}>
            <Icon name="x" size={16} />
          </button>
        </div>
        <div className="pop-body">
          <div>
            <p className="set-cap">— defaults</p>
            <div className="set-group">
              <div className="set-row">
                <div className="si">
                  <h3>Resting colour</h3>
                  <p>Your default at the desk, when nothing else is firing.</p>
                </div>
                <div className="set-ctl">
                  <span
                    className="swatch"
                    style={{ width: 30, height: 30, background: restingHex, ["--sw" as string]: restingHex }}
                    onClick={onPickResting}
                    title="Change"
                  />
                </div>
              </div>
              <div className="set-row">
                <div className="si">
                  <h3>Off-hours</h3>
                  <p>Nights and weekends, outside every routine.</p>
                </div>
                <div className="set-ctl">
                  <div className="seg">
                    {[
                      ["off", "Off"],
                      ["dim", "Dim"],
                      ["resting", "Resting"],
                    ].map(([v, l]) => (
                      <button key={v} className={offSel === v ? "on" : ""} onClick={() => setOff(v)}>
                        {l}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div>
            <p className="set-cap">— accessibility</p>
            <div className="set-group">
              <div className="set-row">
                <div className="si">
                  <h3>Shape &amp; motion cues</h3>
                  <p>Mark "now" and active states with a pulse and ring, not colour alone — helps if red/green is hard to tell apart.</p>
                </div>
                <div className="set-ctl">
                  <Switch on={shapeCues} onClick={onToggleShapeCues} label="Shape and motion cues" />
                </div>
              </div>
            </div>
          </div>

          <div>
            <p className="set-cap">— colours &amp; startup</p>
            <div className="set-group">
              <div className="set-row">
                <div className="si">
                  <h3>Colour palette</h3>
                  <p>Edit, add, or remove your template colours.</p>
                </div>
                <div className="set-ctl">
                  <button className="btn sm" onClick={onOpenPalette}>
                    <Icon name="palette" size={14} /> Edit
                  </button>
                </div>
              </div>
              <div className="set-row">
                <div className="si">
                  <h3>Start with Windows</h3>
                </div>
                <div className="set-ctl">
                  <Switch on={autostart} onClick={onToggleAutostart} />
                </div>
              </div>
            </div>
          </div>

          <div>
            <p className="set-cap">— about</p>
            <div className="set-group">
              <div className="set-row">
                <div className="si">
                  <h3>Beacon v{version}</h3>
                  <p>{update ? `Version ${update.version} is available.` : "You're up to date."}</p>
                </div>
                <div className="set-ctl">
                  {update && (
                    <button className="btn sm primary" onClick={onInstallUpdate}>
                      <Icon name="download" size={13} /> Install
                    </button>
                  )}
                  <button className="btn sm" onClick={onCheckUpdate} disabled={checking}>
                    <Icon name="refresh" size={14} /> {checking ? "Checking…" : "Check"}
                  </button>
                </div>
              </div>
              <div className="set-row">
                <div className="si">
                  <h3>Help</h3>
                </div>
                <div className="set-ctl">
                  <button className="btn sm" onClick={onOpenLogs}>
                    Logs
                  </button>
                  <button className="btn sm" onClick={() => window.open(ISSUES, "_blank", "noopener")}>
                    Report <Icon name="external" size={13} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Scrim>
  );
}

export function ConflictSheet({
  conflict,
  rechecking,
  onRecheck,
  onDismiss,
  connected = true,
}: {
  conflict: ConflictDetected;
  rechecking: boolean;
  onRecheck: () => void;
  onDismiss: () => void;
  connected?: boolean;
}) {
  const allClear = !conflict.luxafor_v2_running && !conflict.luxafor_v2_startup;
  return (
    <Scrim onClose={onDismiss} z={70}>
      <div className="sheet">
        <div className="sheet-head" style={{ ["--live" as string]: "#ff5470" }}>
          <div className="emblem">
            <Flag hex="#ff3b3b" brightness={1} effect="strobe" size={66} />
          </div>
          <div>
            <div className="eye">— first run / one-time</div>
            <h2>{allClear ? "All set — Beacon has the flag" : "Two apps are fighting over your flag"}</h2>
            <p>
              {allClear
                ? "No other app is holding the flag. You're good to go."
                : "The old Luxafor app is still running, so both keep overwriting the colour and it flickers. Quit it and drop it from startup."}
            </p>
          </div>
        </div>
        <div className="sheet-body">
          <div className={"step" + (connected ? " done" : "")}>
            <div className="num">{connected ? <Icon name="check" size={15} /> : "•"}</div>
            <div className="stx">
              <h4>{connected ? "Beacon found your flag" : "Plug in your flag"}</h4>
              <p>{connected ? "Connected over USB." : "No Luxafor detected on USB yet."}</p>
            </div>
          </div>
          <div className={"step" + (!conflict.luxafor_v2_running ? " done" : "")}>
            <div className="num">{!conflict.luxafor_v2_running ? <Icon name="check" size={15} /> : "1"}</div>
            <div className="stx">
              <h4>Quit the old Luxafor app</h4>
              <p>
                Right-click its tray icon and choose <b>Exit</b>, or end <code>Luxafor.exe</code>.
              </p>
            </div>
          </div>
          <div className={"step" + (!conflict.luxafor_v2_startup ? " done" : "")}>
            <div className="num">{!conflict.luxafor_v2_startup ? <Icon name="check" size={15} /> : "2"}</div>
            <div className="stx">
              <h4>Remove it from startup</h4>
              <p>
                <code>Task Manager → Startup apps</code>, find <b>Luxafor</b>, set <b>Disabled</b>.
              </p>
            </div>
          </div>
        </div>
        <div className="sheet-foot">
          <span className="fnote">Beacon keeps working meanwhile.</span>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn" onClick={onDismiss}>
              {allClear ? "Done" : "Later"}
            </button>
            {!allClear && (
              <button className="btn primary" onClick={onRecheck} disabled={rechecking}>
                <Icon name="refresh" size={15} /> {rechecking ? "Checking…" : "Re-check"}
              </button>
            )}
          </div>
        </div>
      </div>
    </Scrim>
  );
}

export function UpdateSheet({
  version,
  update,
  installing,
  onInstall,
  onLater,
}: {
  version: string;
  update: UpdateAvailable;
  installing: boolean;
  onInstall: () => void;
  onLater: () => void;
}) {
  return (
    <Scrim onClose={onLater} z={75}>
      <div className="sheet" style={{ width: 480 }}>
        <div className="sheet-head" style={{ ["--live" as string]: "var(--accent)" }}>
          <div
            className="emblem"
            style={{
              width: 52,
              height: 52,
              borderRadius: 14,
              display: "grid",
              placeItems: "center",
              background: "color-mix(in srgb, var(--accent) 16%, var(--bg-card))",
              color: "var(--accent)",
            }}
          >
            <Icon name="download" size={24} />
          </div>
          <div>
            <div className="eye">— update available</div>
            <h2>Beacon v{update.version} is ready</h2>
            <p>
              A new version is available with the latest fixes and improvements.
              Installing takes a few seconds — Beacon closes and reopens on its own.
            </p>
          </div>
        </div>
        <div className="sheet-foot">
          <span className="fnote">You're on v{version}.</span>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn" onClick={onLater}>
              Later
            </button>
            <button className="btn primary" onClick={onInstall} disabled={installing}>
              <Icon name="download" size={15} /> {installing ? "Installing…" : "Install now"}
            </button>
          </div>
        </div>
      </div>
    </Scrim>
  );
}

export function UpdateBanner({
  update,
  onInstall,
  onDismiss,
}: {
  update: UpdateAvailable;
  onInstall: () => void;
  onDismiss: () => void;
}) {
  return (
    <div className="banner">
      <Icon name="download" size={18} />
      <div className="bx">
        <b>Update available.</b> Beacon v{update.version} is ready to install.
      </div>
      <button className="btn sm primary" onClick={onInstall}>
        Install
      </button>
      <button className="btn sm ghost icon" title="Dismiss" onClick={onDismiss}>
        <Icon name="x" size={15} />
      </button>
    </div>
  );
}

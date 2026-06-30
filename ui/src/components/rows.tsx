// Trigger & routine rows — collapsed views lean on icons; expanded views edit.
// Ported from the design (rows.jsx), wired to the real Trigger/Routine model.

import { useEffect, useState } from "react";
import { Icon } from "../icons";
import { Switch, TierSeg, DayPicker } from "./controls";
import {
  hexOf,
  nameOf,
  daysLabel,
  fmt12,
  effectName,
  tierOf,
  priorityOf,
  tierLabel,
  triggerIcon,
  hotkeyLabel,
  captureHotkey,
} from "../model";
import { api } from "../api";
import type { PaletteColor, Routine, Tier, Trigger, TriggerMeta } from "../types";

function swatchStyle(hex: string): React.CSSProperties {
  return { background: hex, ["--sw" as string]: hex };
}

function shortApp(raw: string): string {
  const parts = raw.split(/[#\\/]/);
  return parts[parts.length - 1] || raw;
}

/** "Press your combo" capture field for hotkey triggers. */
function HotkeyCapture({
  value,
  onChange,
}: {
  value: Trigger["params"];
  onChange: (p: Trigger["params"]) => void;
}) {
  const [listening, setListening] = useState(false);
  const [needMod, setNeedMod] = useState(false);

  // while listening, release the registered global hotkeys so the OS doesn't
  // swallow the very combo (or a colliding one) the user is trying to capture
  useEffect(() => {
    if (!listening) return;
    api.suspendHotkeys().catch(() => {});
    const onKey = (e: KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.key === "Escape") {
        setListening(false); // cancel, keep the existing combo
        return;
      }
      const combo = captureHotkey(e);
      if (!combo) return; // unsupported key — keep listening
      if (!(combo.ctrl || combo.alt || combo.shift || combo.win)) {
        setNeedMod(true); // a bare key isn't allowed
        return;
      }
      setNeedMod(false);
      onChange(combo);
      setListening(false);
    };
    window.addEventListener("keydown", onKey, true);
    return () => {
      window.removeEventListener("keydown", onKey, true);
      api.resumeHotkeys().catch(() => {});
    };
  }, [listening, onChange]);

  return (
    <>
      <button
        type="button"
        className={"colorbtn" + (listening ? " listening" : "")}
        onClick={() => {
          setNeedMod(false);
          setListening((l) => !l);
        }}
      >
        <Icon name="keyboard" size={16} />
        {listening ? "Press a key combo… (Esc to cancel)" : hotkeyLabel(value)}
        <span className="muted ar" style={{ fontSize: 12 }}>
          {listening ? "listening" : "change"}
        </span>
      </button>
      {needMod && (
        <p className="hint" style={{ color: "var(--error)" }}>
          Add a modifier — Ctrl, Alt, Shift, or Win — plus a key.
        </p>
      )}
    </>
  );
}

export function TriggerRow({
  trigger: t,
  palette,
  triggerMeta,
  active,
  regError = false,
  open,
  onOpen,
  onChange,
  onDelete,
  onPickColor,
}: {
  trigger: Trigger;
  palette: PaletteColor[];
  triggerMeta: TriggerMeta;
  active: boolean;
  regError?: boolean;
  open: boolean;
  onOpen: () => void;
  onChange: (t: Trigger) => void;
  onDelete: () => void;
  onPickColor: () => void;
}) {
  const [detected, setDetected] = useState<string[]>([]);
  const hex = hexOf(palette, t.color);
  const typeMeta = triggerMeta.types.find((x) => x.id === t.type) || triggerMeta.types[0];
  const needsApp = typeMeta?.needs_app ?? false;
  const needsHotkey = typeMeta?.needs_hotkey ?? false;
  const needsMinutes = typeMeta?.needs_minutes ?? false;
  const tier = tierOf(t.priority);
  const set = (patch: Partial<Trigger>) => onChange({ ...t, ...patch });

  // label + placeholder for the text-match field varies by trigger type
  const appLabel =
    t.type === "foreground"
      ? "— app or window title contains"
      : t.type === "process"
      ? "— process name contains"
      : "— app name contains";
  const appHint =
    t.type === "foreground"
      ? "Matches the focused window's app name or title."
      : t.type === "process"
      ? "Fires whenever a process with this name is running."
      : detected.length
      ? "On mic now: " + detected.map(shortApp).join(", ")
      : "No apps are using the microphone right now.";

  // short summary shown in the collapsed row
  const summary = needsHotkey
    ? hotkeyLabel(t.params)
    : needsMinutes
    ? `after ${t.params.minutes ?? 5} min idle`
    : needsApp && t.params.app
    ? `“${t.params.app}”`
    : typeMeta?.name;

  useEffect(() => {
    if (open && t.type === "mic_app") {
      api.getSignals().then((s) => setDetected(s.mic_capturers ?? [])).catch(() => {});
    }
  }, [open, t.type]);

  const editId = `trigger-edit-${t.id}`;
  const triggerLabel = t.name || "Untitled trigger";

  return (
    <div className={"row" + (open ? " open" : "") + (t.enabled ? "" : " disabled")}>
      <div className="row-main" onClick={onOpen}>
        <span
          className={"live-dot" + (active ? " on" : "")}
          title={active ? "Active now" : "Idle"}
          style={{ cursor: "default" }}
        />
        <span
          className="swatch"
          role="button"
          tabIndex={0}
          aria-label={`Change colour (currently ${nameOf(palette, t.color)})`}
          style={swatchStyle(hex)}
          title="Change colour"
          onClick={(e) => {
            e.stopPropagation();
            onPickColor();
          }}
          onKeyDown={(e) => {
            if (e.key === " " || e.key === "Enter") {
              e.preventDefault();
              e.stopPropagation();
              onPickColor();
            }
          }}
        />
        <div className="r-info">
          <div className={"r-name" + (t.name ? "" : " placeholder")}>{t.name || "Untitled"}</div>
          <div className="r-meta">
            <Icon name={triggerIcon(t.type)} size={13} />
            <span>{needsHotkey ? hotkeyLabel(t.params) : typeMeta?.name}</span>
            {needsHotkey && regError && (
              <>
                <span className="sep">·</span>
                <span style={{ color: "var(--error)" }}>combo unavailable</span>
              </>
            )}
            {active && (
              <>
                <span className="sep">·</span>
                <span className="live">active</span>
              </>
            )}
          </div>
        </div>
        <div className="r-right" onClick={(e) => e.stopPropagation()}>
          <span className="tier-tag">{tierLabel(tier)}</span>
          <Switch on={t.enabled} onClick={() => set({ enabled: !t.enabled })} label={`${triggerLabel} enabled`} />
          <button
            type="button"
            className="chev-btn"
            aria-expanded={open}
            aria-controls={editId}
            aria-label={`${open ? "Collapse" : "Expand"} ${triggerLabel}`}
            onClick={onOpen}
          >
            <Icon name="chevron" size={18} className="chev" />
          </button>
        </div>
      </div>

      {open && (
        <div id={editId} className="row-edit" onClick={(e) => e.stopPropagation()}>
          <div className="egrid">
            <div className="field">
              <label>— name</label>
              <input
                className="input"
                value={t.name}
                placeholder="Name this trigger"
                autoFocus={!t.name}
                onChange={(e) => set({ name: e.target.value })}
              />
            </div>
            <div className="field">
              <label>— when</label>
              <select
                className="input"
                value={t.type}
                onChange={(e) => set({ type: e.target.value as Trigger["type"] })}
              >
                {triggerMeta.types.map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {needsApp && (
            <div className="field">
              <label>— app name contains</label>
              <input
                className="input"
                value={t.params.app ?? ""}
                placeholder="e.g. teams, zoom, slack"
                onChange={(e) => set({ params: { ...t.params, app: e.target.value } })}
              />
              <p className="hint">
                {detected.length
                  ? "On mic now: " + detected.map(shortApp).join(", ")
                  : "No apps are using the microphone right now."}
              </p>
            </div>
          )}

          {needsHotkey && (
            <div className="field">
              <label>— shortcut</label>
              <HotkeyCapture value={t.params} onChange={(p) => set({ params: p })} />
              {regError ? (
                <p className="hint" style={{ color: "var(--error)" }}>
                  Windows wouldn't register this combo (another app may own it, or
                  it's reserved). Pick a different one.
                </p>
              ) : (
                <p className="hint">
                  Press it anywhere to toggle this status on and off. Needs a
                  modifier (Ctrl / Alt / Shift / Win) plus a key.
                </p>
              )}
            </div>
          )}

          <div className="field">
            <label>— colour &amp; effect</label>
            <button className="colorbtn" onClick={onPickColor}>
              <span className="sw" style={{ background: hex }} />
              {nameOf(palette, t.color)}
              <span className="muted" style={{ fontSize: 12 }}>
                · {effectName(t.effect)}
              </span>
              <Icon name="chevron" size={15} className="ar" />
            </button>
          </div>

          <div className="field">
            <label>— importance</label>
            <TierSeg value={tier} onChange={(tr: Tier) => set({ priority: priorityOf(tr) })} />
            <p className="hint">
              {tier === "critical" ? (
                <>
                  <b>Critical</b> outranks everything — a manual override, routines,
                  and other triggers.
                </>
              ) : tier === "high" ? (
                <>
                  <b>High</b> beats a manual override and routines.
                </>
              ) : tier === "normal" ? (
                <>
                  <b>Normal</b> beats routines, but yields to a manual override.
                </>
              ) : (
                <>
                  <b>Low</b> only shows when nothing else is active — routines
                  outrank it.
                </>
              )}
            </p>
          </div>

          <div className="edit-foot">
            <button className="btn danger sm" onClick={onDelete}>
              <Icon name="trash" size={15} /> Delete
            </button>
            <button className="btn primary sm" onClick={onOpen}>
              <Icon name="check" size={15} /> Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export function RoutineRow({
  routine: r,
  palette,
  activeNow,
  open,
  onOpen,
  onChange,
  onDelete,
  onPickColor,
}: {
  routine: Routine;
  palette: PaletteColor[];
  activeNow: boolean;
  open: boolean;
  onOpen: () => void;
  onChange: (r: Routine) => void;
  onDelete: () => void;
  onPickColor: () => void;
}) {
  const hex = hexOf(palette, r.color);
  const set = (patch: Partial<Routine>) => onChange({ ...r, ...patch });
  const toggleDay = (d: number) => {
    const has = r.days.includes(d);
    set({ days: has ? r.days.filter((x) => x !== d) : [...r.days, d] });
  };

  const editId = `routine-edit-${r.id}`;
  const routineLabel = r.name || "Untitled routine";

  return (
    <div className={"row" + (open ? " open" : "") + (r.enabled ? "" : " disabled")}>
      <div className="row-main" onClick={onOpen}>
        <span
          className={"live-dot" + (activeNow ? " on" : "")}
          title={activeNow ? "Active now" : "Idle"}
          style={{ cursor: "default" }}
        />
        <span
          className="swatch"
          role="button"
          tabIndex={0}
          aria-label={`Change colour (currently ${nameOf(palette, r.color)})`}
          style={swatchStyle(hex)}
          title="Change colour"
          onClick={(e) => {
            e.stopPropagation();
            onPickColor();
          }}
          onKeyDown={(e) => {
            if (e.key === " " || e.key === "Enter") {
              e.preventDefault();
              e.stopPropagation();
              onPickColor();
            }
          }}
        />
        <div className="r-info">
          <div className={"r-name" + (r.name ? "" : " placeholder")}>{r.name || "Untitled"}</div>
          <div className="r-meta">
            <Icon name="clock" size={13} />
            <span>{daysLabel(r.days)}</span>
            <span className="sep">·</span>
            <span>
              {fmt12(r.start)}–{fmt12(r.end)}
            </span>
            {activeNow && (
              <>
                <span className="sep">·</span>
                <span className="live">now</span>
              </>
            )}
          </div>
        </div>
        <div className="r-right" onClick={(e) => e.stopPropagation()}>
          <Switch on={r.enabled} onClick={() => set({ enabled: !r.enabled })} label={`${routineLabel} enabled`} />
          <button
            type="button"
            className="chev-btn"
            aria-expanded={open}
            aria-controls={editId}
            aria-label={`${open ? "Collapse" : "Expand"} ${routineLabel}`}
            onClick={onOpen}
          >
            <Icon name="chevron" size={18} className="chev" />
          </button>
        </div>
      </div>

      {open && (
        <div id={editId} className="row-edit" onClick={(e) => e.stopPropagation()}>
          <div className="egrid">
            <div className="field">
              <label>— name</label>
              <input
                className="input"
                value={r.name}
                placeholder="Name this block"
                autoFocus={!r.name}
                onChange={(e) => set({ name: e.target.value })}
              />
            </div>
            <div className="field">
              <label>— window</label>
              <div className="timepair">
                <input
                  className="input mono"
                  type="time"
                  value={r.start}
                  aria-label={`${routineLabel} start time`}
                  onChange={(e) => set({ start: e.target.value })}
                />
                <span>–</span>
                <input
                  className="input mono"
                  type="time"
                  value={r.end}
                  aria-label={`${routineLabel} end time`}
                  onChange={(e) => set({ end: e.target.value })}
                />
              </div>
              {r.end <= r.start && (
                <p className="hint" style={{ color: "var(--error)" }}>
                  End time must be after start (overnight windows aren't
                  supported yet).
                </p>
              )}
            </div>
          </div>
          <div className="field">
            <label>— days</label>
            <DayPicker days={r.days} onToggle={toggleDay} />
          </div>
          <div className="field">
            <label>— colour &amp; effect</label>
            <button className="colorbtn" onClick={onPickColor}>
              <span className="sw" style={{ background: hex }} />
              {nameOf(palette, r.color)}
              <span className="muted" style={{ fontSize: 12 }}>
                · {effectName(r.effect)}
              </span>
              <Icon name="chevron" size={15} className="ar" />
            </button>
          </div>
          <div className="edit-foot">
            <button className="btn danger sm" onClick={onDelete}>
              <Icon name="trash" size={15} /> Delete
            </button>
            <button className="btn primary sm" onClick={onOpen}>
              <Icon name="check" size={15} /> Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

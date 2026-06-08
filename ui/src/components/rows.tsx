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

export function TriggerRow({
  trigger: t,
  palette,
  triggerMeta,
  active,
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
  const tier = tierOf(t.priority);
  const set = (patch: Partial<Trigger>) => onChange({ ...t, ...patch });

  useEffect(() => {
    if (open && needsApp) {
      api.getSignals().then((s) => setDetected(s.mic_capturers ?? [])).catch(() => {});
    }
  }, [open, needsApp]);

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
          style={swatchStyle(hex)}
          title="Change colour"
          onClick={(e) => {
            e.stopPropagation();
            onPickColor();
          }}
        />
        <div className="r-info">
          <div className={"r-name" + (t.name ? "" : " placeholder")}>{t.name || "Untitled"}</div>
          <div className="r-meta">
            <Icon name={triggerIcon(t.type)} size={13} />
            <span>{typeMeta?.name}</span>
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
          <Switch on={t.enabled} onClick={() => set({ enabled: !t.enabled })} />
          <Icon name="chevron" size={18} className="chev" />
        </div>
      </div>

      {open && (
        <div className="row-edit" onClick={(e) => e.stopPropagation()}>
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
                  <b>Critical</b> outranks everything, including other High triggers.
                </>
              ) : tier === "high" ? (
                <>
                  <b>High</b> beats a manual override and every routine.
                </>
              ) : tier === "normal" ? (
                <>
                  <b>Normal</b> yields to a manual override.
                </>
              ) : (
                <>
                  <b>Low</b> only shows when nothing else is active.
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
          style={swatchStyle(hex)}
          title="Change colour"
          onClick={(e) => {
            e.stopPropagation();
            onPickColor();
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
          <Switch on={r.enabled} onClick={() => set({ enabled: !r.enabled })} />
          <Icon name="chevron" size={18} className="chev" />
        </div>
      </div>

      {open && (
        <div className="row-edit" onClick={(e) => e.stopPropagation()}>
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
                  onChange={(e) => set({ start: e.target.value })}
                />
                <span>–</span>
                <input
                  className="input mono"
                  type="time"
                  value={r.end}
                  onChange={(e) => set({ end: e.target.value })}
                />
              </div>
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

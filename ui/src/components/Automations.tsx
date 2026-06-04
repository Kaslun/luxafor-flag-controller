import { useEffect, useState } from "react";
import type {
  Config,
  EffectsMeta,
  PaletteSlot,
  State,
  Trigger,
  TriggerMeta,
  TriggerType,
} from "../types";
import { hexOf, nameOf } from "../model";
import { Icon } from "../icons";
import { ColorPicker } from "./ColorPicker";
import { effectLabel } from "./ColorEffectFields";
import { api } from "../api";

/** Event triggers: user-defined condition → color/effect, evaluated each
 *  tick. Mirrors the Routines list (expand-in-place rows). The highest
 *  priority active trigger wins; priority 50 == a manual override. */
export function Automations({
  config,
  palette,
  effects,
  triggerMeta,
  state,
  onChange,
}: {
  config: Config;
  palette: PaletteSlot[];
  effects: EffectsMeta;
  triggerMeta: TriggerMeta;
  state: State;
  onChange: (next: Config) => void;
}) {
  const [openId, setOpenId] = useState<string | null>(null);
  const triggers = config.triggers;

  const setTriggers = (next: Trigger[]) => onChange({ ...config, triggers: next });

  const addTrigger = () => {
    const id = "t" + Date.now();
    setTriggers([
      ...triggers,
      {
        id,
        name: "",
        enabled: true,
        type: "mic",
        color: "busy",
        priority: triggerMeta.override_priority + 20,
        params: {},
        effect: effects.default,
      },
    ]);
    setOpenId(id);
  };

  const changeTrigger = (next: Trigger) =>
    setTriggers(triggers.map((t) => (t.id === next.id ? next : t)));

  const deleteTrigger = (id: string) => {
    setTriggers(triggers.filter((t) => t.id !== id));
    if (openId === id) setOpenId(null);
  };

  const activeIds = new Set(state.active_triggers.map((a) => a.id));

  return (
    <div>
      <div className="section-head">
        <div>
          <h2>Triggers</h2>
          <p>
            Events that set your status automatically. Higher priority wins; a
            manual override sits at {triggerMeta.override_priority}.
          </p>
        </div>
        <button className="btn primary" onClick={addTrigger}>
          <Icon name="plus" /> Add trigger
        </button>
      </div>

      {triggers.length === 0 ? (
        <div className="empty">
          <div className="icon">
            <Icon name="bolt" size={26} />
          </div>
          <h3>No triggers yet</h3>
          <p>
            Add an event — like being in a call, on webcam, or with your screen
            locked — and the flag will react on its own.
          </p>
          <button className="btn primary" onClick={addTrigger} style={{ margin: "0 auto" }}>
            <Icon name="plus" /> Add your first trigger
          </button>
        </div>
      ) : (
        <div className="routine-list">
          {triggers.map((t) => (
            <TriggerRow
              key={t.id}
              trigger={t}
              palette={palette}
              effects={effects}
              triggerMeta={triggerMeta}
              active={activeIds.has(t.id) && t.enabled}
              open={openId === t.id}
              onOpen={() => setOpenId(openId === t.id ? null : t.id)}
              onChange={changeTrigger}
              onDelete={() => deleteTrigger(t.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function TriggerRow({
  trigger,
  palette,
  effects,
  triggerMeta,
  active,
  open,
  onOpen,
  onChange,
  onDelete,
}: {
  trigger: Trigger;
  palette: PaletteSlot[];
  effects: EffectsMeta;
  triggerMeta: TriggerMeta;
  active: boolean;
  open: boolean;
  onOpen: () => void;
  onChange: (t: Trigger) => void;
  onDelete: () => void;
}) {
  const [showPicker, setShowPicker] = useState(false);
  const [detected, setDetected] = useState<string[]>([]);
  const t = trigger;
  const hex = hexOf(palette, t.color);
  const eff = effectLabel(t.effect);
  const set = (patch: Partial<Trigger>) => onChange({ ...t, ...patch });

  const typeMeta = triggerMeta.types.find((x) => x.id === t.type);
  const needsApp = typeMeta?.needs_app ?? false;
  const typeName = typeMeta?.name ?? t.type;

  // when editing a mic_app trigger, fetch the currently-detected mic apps
  // so the user can see real names instead of guessing
  useEffect(() => {
    if (open && needsApp) {
      api.getSignals().then((s) => setDetected(s.mic_capturers ?? [])).catch(() => {});
    }
  }, [open, needsApp]);

  return (
    <div className={"routine" + (open ? " open" : "") + (t.enabled ? "" : " disabled")}>
      <div className="routine-row" onClick={onOpen}>
        <span
          className={"auto-dot" + (active ? " on" : "")}
          title={active ? "Active now" : "Idle"}
        />
        <span className="r-swatch" style={{ background: hex, ["--sw" as string]: hex }} />
        <div className="r-info">
          <div className="r-name">{t.name || "Untitled trigger"}</div>
          <div className="r-meta">
            <span>{typeName}</span>
            {needsApp && t.params.app && <span>“{t.params.app}”</span>}
            <span>priority {t.priority}</span>
            {eff && <span>{eff}</span>}
            {active && <span className="auto-live">· active now</span>}
          </div>
        </div>
        <div className="r-right" onClick={(e) => e.stopPropagation()}>
          <button
            type="button"
            className="r-colorbtn"
            title="Change color"
            onClick={() => setShowPicker(true)}
            style={{ background: hex, ["--sw" as string]: hex }}
          />
          <div
            className={"switch" + (t.enabled ? " on" : "")}
            role="switch"
            aria-checked={t.enabled}
            onClick={() => set({ enabled: !t.enabled })}
          />
          <Icon name="chevron" size={18} className="chev" />
        </div>
      </div>

      {open && (
        <div className="routine-edit" onClick={(e) => e.stopPropagation()}>
          <div className="edit-grid">
            <div className="field">
              <label>Name</label>
              <input
                className="input"
                value={t.name}
                placeholder="New trigger"
                onChange={(e) => set({ name: e.target.value })}
                autoFocus={!t.name}
              />
            </div>
            <div className="field">
              <label>When</label>
              <select
                className="input"
                value={t.type}
                onChange={(e) => set({ type: e.target.value as TriggerType })}
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
              <label>App name contains</label>
              <input
                className="input"
                value={t.params.app ?? ""}
                placeholder="e.g. teams, zoom, slack"
                onChange={(e) => set({ params: { ...t.params, app: e.target.value } })}
              />
              <p className="muted" style={{ margin: "6px 0 0", fontSize: 12 }}>
                {detected.length
                  ? "On mic now: " + detected.map(shortApp).join(", ")
                  : "No apps are using the microphone right now."}
              </p>
            </div>
          )}

          <div className="edit-grid">
            <div className="field">
              <label>Color &amp; effect</label>
              <button
                type="button"
                className="btn"
                style={{ justifyContent: "flex-start", gap: 10 }}
                onClick={() => setShowPicker(true)}
              >
                <span
                  style={{
                    width: 18,
                    height: 18,
                    borderRadius: 6,
                    background: hex,
                    boxShadow: "inset 0 0 0 1px rgba(255,255,255,.25)",
                  }}
                />
                {nameOf(palette, t.color)}
                {eff && <span className="muted">· {eff}</span>}
                <Icon name="chevron" size={15} style={{ marginLeft: "auto" }} />
              </button>
            </div>
            <div className="field">
              <label>Priority ({triggerMeta.priority_min}–{triggerMeta.priority_max})</label>
              <input
                className="input"
                type="number"
                min={triggerMeta.priority_min}
                max={triggerMeta.priority_max}
                value={t.priority}
                onChange={(e) => {
                  const n = Number(e.target.value);
                  if (Number.isFinite(n))
                    set({
                      priority: Math.max(
                        triggerMeta.priority_min,
                        Math.min(triggerMeta.priority_max, Math.round(n))
                      ),
                    });
                }}
              />
              <p className="muted" style={{ margin: "6px 0 0", fontSize: 12 }}>
                Manual override acts at {triggerMeta.override_priority} — set higher
                to win over it.
              </p>
            </div>
          </div>

          <div className="edit-foot">
            <button className="btn sm danger" onClick={onDelete}>
              <Icon name="trash" size={15} /> Delete
            </button>
            <button className="btn sm primary" onClick={onOpen}>
              <Icon name="check" size={15} /> Done
            </button>
          </div>
        </div>
      )}

      {showPicker && (
        <ColorPicker
          palette={palette}
          effects={effects}
          color={t.color}
          effect={t.effect ?? effects.default}
          title={`Color & effect — ${t.name || "trigger"}`}
          onApply={(color, effect) => {
            set({ color, effect });
            setShowPicker(false);
          }}
          onClose={() => setShowPicker(false)}
        />
      )}
    </div>
  );
}

/** Shorten a munged registry capturer path to its executable name. */
function shortApp(raw: string): string {
  const parts = raw.split(/[#\\/]/);
  return parts[parts.length - 1] || raw;
}

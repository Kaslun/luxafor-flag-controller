import { useState } from "react";
import type { Config, EffectsMeta, PaletteSlot, Settings, State } from "../types";
import { hexOf, nameOf } from "../model";
import { ColorPicker } from "./ColorPicker";

/** Front-page automatic triggers (events): mic call + screen lock.
 *  Each can be toggled and given a color; the live state shows when active. */
export function Automations({
  config,
  palette,
  effects,
  state,
  onChange,
}: {
  config: Config;
  palette: PaletteSlot[];
  effects: EffectsMeta;
  state: State;
  onChange: (next: Config) => void;
}) {
  const [picker, setPicker] = useState<null | "call" | "lock">(null);
  const s = config.settings;
  const setS = (patch: Partial<Settings>) =>
    onChange({ ...config, settings: { ...s, ...patch } });

  const rows = [
    {
      key: "call" as const,
      title: "In a call",
      desc: "Turns the flag this color whenever your microphone is in use.",
      enabled: s.call_detection,
      color: s.call_color,
      active: state.in_call,
      toggle: () => setS({ call_detection: !s.call_detection }),
      setColor: (c: string) => setS({ call_color: c }),
    },
    {
      key: "lock" as const,
      title: "Screen locked",
      desc: "Shows this color while your PC is locked — you've stepped away.",
      enabled: s.lock_detection,
      color: s.lock_color,
      active: state.locked,
      toggle: () => setS({ lock_detection: !s.lock_detection }),
      setColor: (c: string) => setS({ lock_color: c }),
    },
  ];

  const current = rows.find((r) => r.key === picker);

  return (
    <div>
      <div className="section-head">
        <div>
          <h2>Automations</h2>
          <p>Automatic triggers that set your status — they always win over routines.</p>
        </div>
      </div>

      <div className="set-group">
        {rows.map((r) => (
          <div className="set-row" key={r.key}>
            <span
              className={"auto-dot" + (r.active && r.enabled ? " on" : "")}
              title={r.active ? "Active now" : "Idle"}
            />
            <div className="si">
              <h3>
                {r.title}
                {r.active && r.enabled && <span className="auto-live"> · active now</span>}
              </h3>
              <p>{r.desc}</p>
            </div>
            <div className="set-ctl">
              <button
                type="button"
                className="r-colorbtn"
                title="Change color"
                onClick={() => setPicker(r.key)}
                disabled={!r.enabled}
                style={{
                  background: hexOf(palette, r.color),
                  ["--sw" as string]: hexOf(palette, r.color),
                  opacity: r.enabled ? 1 : 0.4,
                }}
              />
              <span className="muted" style={{ minWidth: 64, fontSize: 12 }}>
                {nameOf(palette, r.color)}
              </span>
              <div
                className={"switch" + (r.enabled ? " on" : "")}
                role="switch"
                aria-checked={r.enabled}
                onClick={r.toggle}
              />
            </div>
          </div>
        ))}
      </div>

      {current && (
        <ColorPicker
          palette={palette}
          effects={effects}
          color={current.color}
          effect={effects.default}
          allowEffects={false}
          title={`Color — ${current.title}`}
          onApply={(c) => {
            current.setColor(c);
            setPicker(null);
          }}
          onClose={() => setPicker(null)}
        />
      )}
    </div>
  );
}

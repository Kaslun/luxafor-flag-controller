import type { Config, PaletteSlot, Settings } from "../types";
import { nameOf } from "../model";
import { SlotMini } from "./SlotMini";

export function SettingsTab({
  config,
  palette,
  onChange,
  autostartEnabled,
  onToggleAutostart,
}: {
  config: Config;
  palette: PaletteSlot[];
  onChange: (next: Config) => void;
  autostartEnabled: boolean;
  onToggleAutostart: () => void;
}) {
  const s = config.settings;
  const setS = (patch: Partial<Settings>) =>
    onChange({ ...config, settings: { ...s, ...patch } });

  return (
    <div>
      <div className="section-head">
        <div>
          <h2>Settings</h2>
          <p>The defaults the engine falls back on when no routine or override applies.</p>
        </div>
      </div>

      <div className="set-group" style={{ marginBottom: 18 }}>
        <div className="set-row">
          <div className="si">
            <h3>Automatic call detection</h3>
            <p>
              Turns the flag {nameOf(palette, s.call_color).toLowerCase()} whenever
              your mic is in a call. Always highest priority — never appears as a
              routine.
            </p>
          </div>
          <div className="set-ctl">
            <SlotMini
              palette={palette}
              value={s.call_color}
              onChange={(c) => setS({ call_color: c })}
              disabled={!s.call_detection}
            />
            <div
              className={"switch" + (s.call_detection ? " on" : "")}
              role="switch"
              aria-checked={s.call_detection}
              onClick={() => setS({ call_detection: !s.call_detection })}
            />
          </div>
        </div>
      </div>

      <div className="set-group">
        <div className="set-row">
          <div className="si">
            <h3>Available color</h3>
            <p>
              The floor — what shows when you're at your desk and nothing more
              specific applies.
            </p>
          </div>
          <div className="set-ctl">
            <SlotMini
              palette={palette}
              value={s.available_color}
              onChange={(c) => setS({ available_color: c })}
            />
          </div>
        </div>
        <div className="set-row">
          <div className="si">
            <h3>When nothing's active</h3>
            <p>Outside every routine — nights and weekends. Your most common idle state.</p>
          </div>
          <div className="set-ctl">
            <div className="segment">
              {[
                ["off", "Off"],
                ["dim", "Dim"],
                ["available", "Available"],
              ].map(([v, l]) => (
                <button
                  key={v}
                  className={s.off_behavior === v ? "on" : ""}
                  onClick={() => setS({ off_behavior: v })}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="set-group" style={{ marginTop: 18 }}>
        <div className="set-row">
          <div className="si">
            <h3>Start with Windows</h3>
            <p>
              Launch Beacon automatically when you sign in, so your flag is always
              under control. No admin rights needed.
            </p>
          </div>
          <div className="set-ctl">
            <div
              className={"switch" + (autostartEnabled ? " on" : "")}
              role="switch"
              aria-checked={autostartEnabled}
              onClick={onToggleAutostart}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

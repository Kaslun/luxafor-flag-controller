import type { Config, PaletteSlot, Settings, UpdateAvailable } from "../types";
import { nameOf } from "../model";
import { Icon } from "../icons";
import { SlotMini } from "./SlotMini";

export function SettingsTab({
  config,
  palette,
  onChange,
  autostartEnabled,
  onToggleAutostart,
  version,
  updateAvailable,
  checking,
  onCheckUpdate,
  onInstallUpdate,
  onOpenLogs,
}: {
  config: Config;
  palette: PaletteSlot[];
  onChange: (next: Config) => void;
  autostartEnabled: boolean;
  onToggleAutostart: () => void;
  version: string;
  updateAvailable: UpdateAvailable | null;
  checking: boolean;
  onCheckUpdate: () => void;
  onInstallUpdate: () => void;
  onOpenLogs: () => void;
}) {
  const ISSUES_URL = "https://github.com/Kaslun/luxafor-flag-controller/issues";
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

      <div className="set-group" style={{ marginTop: 18 }}>
        <div className="set-row">
          <div className="si">
            <h3>Updates</h3>
            <p>
              You're running <b>Beacon v{version}</b>.{" "}
              {updateAvailable
                ? `Version ${updateAvailable.version} is available.`
                : "You're up to date."}{" "}
              Updates install manually — download and run the new file.
            </p>
          </div>
          <div className="set-ctl">
            {updateAvailable && (
              <button className="btn sm primary" onClick={onInstallUpdate}>
                <Icon name="download" size={13} /> Install update
              </button>
            )}
            <button className="btn sm" onClick={onCheckUpdate} disabled={checking}>
              <Icon name="refresh" size={14} /> {checking ? "Checking…" : "Check for updates"}
            </button>
          </div>
        </div>
      </div>

      <div className="set-group" style={{ marginTop: 18 }}>
        <div className="set-row">
          <div className="si">
            <h3>Help &amp; diagnostics</h3>
            <p>
              Something off? Open the logs folder to grab <code>beacon.log</code>,
              or file an issue so it can be fixed.
            </p>
          </div>
          <div className="set-ctl">
            <button className="btn sm" onClick={onOpenLogs}>
              Open logs
            </button>
            <button
              className="btn sm"
              onClick={() => window.open(ISSUES_URL, "_blank", "noopener")}
            >
              Report an issue <Icon name="external" size={13} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

import type { ConflictDetected } from "../types";
import { Icon } from "../icons";
import { Flag } from "./Flag";

export function ConflictSheet({
  conflict,
  rechecking,
  onRecheck,
  onDismiss,
}: {
  conflict: ConflictDetected;
  rechecking: boolean;
  onRecheck: () => void;
  onDismiss: () => void;
}) {
  const running = conflict.luxafor_v2_running;
  const startup = conflict.luxafor_v2_startup;
  const allClear = !running && !startup;

  return (
    <div className="scrim">
      <div className="sheet">
        <div className="sheet-head">
          <div className="warnmark">
            <Icon name="alert" size={24} />
          </div>
          <div>
            <h2>
              {allClear
                ? "All set — Beacon has the flag"
                : "Two apps are fighting over your flag"}
            </h2>
            <p>
              {allClear
                ? "The old Luxafor app is no longer running or launching at startup. Beacon now drives the flag on its own."
                : "The original Luxafor app is still running. While it is, both apps send colors to the flag and it flickers between them. Quit it and remove it from startup so Beacon can take over cleanly."}
            </p>
          </div>
        </div>
        <div className="sheet-body">
          {!allClear && (
            <div className="symptom">
              <div className="blink">
                <Flag hex="#FF3B3B" size={40} blink />
              </div>
              <div style={{ fontSize: 13, color: "var(--text-2)" }}>
                <b style={{ color: "var(--text)" }}>The symptom:</b> the flag
                flickers or shows the wrong color for a second, then snaps back.
                That's the two apps overwriting each other.
              </div>
            </div>
          )}
          <div className="step done">
            <div className="num">
              <Icon name="check" size={15} />
            </div>
            <div className="stx">
              <h4>Beacon is installed and connected to your flag</h4>
              <p>Detected your Luxafor Flag on USB.</p>
            </div>
          </div>
          <div className={"step" + (running ? "" : " done")}>
            <div className="num">{running ? "1" : <Icon name="check" size={15} />}</div>
            <div className="stx">
              <h4>Quit the old Luxafor app</h4>
              <p>
                Right-click the old Luxafor icon in your system tray and choose{" "}
                <b>Exit</b> — or open Task Manager and end <code>Luxafor.exe</code>.
              </p>
            </div>
          </div>
          <div className={"step" + (startup ? "" : " done")}>
            <div className="num">{startup ? "2" : <Icon name="check" size={15} />}</div>
            <div className="stx">
              <h4>Remove it from startup</h4>
              <p>
                Open <code>Task Manager → Startup apps</code>, find <b>Luxafor</b>,
                and set it to <b>Disabled</b> so it doesn't relaunch tomorrow.
              </p>
            </div>
          </div>
        </div>
        <div className="sheet-foot">
          <span style={{ fontSize: 12.5, color: "var(--text-2)" }}>
            {allClear
              ? "You're good to go."
              : "Beacon keeps working meanwhile — colors may just flicker."}
          </span>
          <div style={{ display: "flex", gap: 10 }}>
            {!allClear && (
              <button className="btn ghost" onClick={onDismiss}>
                Later
              </button>
            )}
            {allClear ? (
              <button className="btn primary" onClick={onDismiss}>
                <Icon name="check" size={15} /> Done
              </button>
            ) : (
              <button className="btn primary" onClick={onRecheck} disabled={rechecking}>
                <Icon name="refresh" size={15} /> {rechecking ? "Checking…" : "Re-check"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

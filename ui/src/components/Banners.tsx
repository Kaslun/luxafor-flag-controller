import type { ConflictDetected, UpdateAvailable } from "../types";
import { Icon } from "../icons";

export function UpdateBanner({
  update,
  onDismiss,
}: {
  update: UpdateAvailable;
  onDismiss: () => void;
}) {
  return (
    <div className="banner update">
      <Icon name="download" size={18} className="bi" />
      <div className="bx">
        Beacon <b>{update.version}</b> is available. Updates install manually —
        your flag keeps working.
      </div>
      <button
        className="btn sm"
        onClick={() => window.open(update.url, "_blank", "noopener")}
      >
        Open download <Icon name="external" size={13} />
      </button>
      <button className="btn sm icon ghost" onClick={onDismiss} aria-label="dismiss">
        <Icon name="x" size={14} />
      </button>
    </div>
  );
}

export function ConflictBanner({
  conflict,
  onFix,
}: {
  conflict: ConflictDetected;
  onFix: () => void;
}) {
  const message = conflict.luxafor_v2_running
    ? "The old Luxafor app is running and may fight Beacon for the flag."
    : "The old Luxafor app is set to launch at startup — it'll fight Beacon for the flag next time it runs.";
  return (
    <div className="banner warn">
      <Icon name="alert" size={18} className="bi" />
      <div className="bx">{message}</div>
      <button className="btn sm" onClick={onFix}>
        Fix it
      </button>
    </div>
  );
}

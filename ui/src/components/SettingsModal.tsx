import type { Config, PaletteSlot, UpdateAvailable } from "../types";
import { Icon } from "../icons";
import { SettingsTab } from "./SettingsTab";

/** Settings as a modal opened from the header gear — keeps the main window
 *  focused on status rather than feeling like a config screen. */
export function SettingsModal(props: {
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
  onClose: () => void;
}) {
  const { onClose, ...rest } = props;
  return (
    <div className="scrim" onClick={onClose} style={{ zIndex: 50 }}>
      <div
        className="sheet"
        style={{ width: 560, maxHeight: "82vh", display: "flex", flexDirection: "column" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sheet-head" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <h2>Settings</h2>
          <button className="btn sm icon ghost" onClick={onClose} aria-label="close">
            <Icon name="x" size={16} />
          </button>
        </div>
        <div style={{ padding: "18px 24px 24px", overflowY: "auto" }}>
          <SettingsTab {...rest} />
        </div>
      </div>
    </div>
  );
}

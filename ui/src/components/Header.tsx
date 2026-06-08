import { Icon } from "../icons";
import type { Theme } from "../theme";

export function Header({
  theme,
  version,
  onToggleTheme,
  onOpenPalette,
  onOpenSettings,
}: {
  theme: Theme;
  version: string;
  onToggleTheme: () => void;
  onOpenPalette: () => void;
  onOpenSettings: () => void;
}) {
  return (
    <div className="hd">
      <div className="mark">
        <span className="glyph">
          <Icon name="beacon" size={20} />
        </span>
        <span className="wordmark">Beacon</span>
        <span className="ver">— v{version}</span>
      </div>
      <div className="spacer" />
      <button className="tbtn" title="Colours" onClick={onOpenPalette}>
        <Icon name="palette" size={17} />
      </button>
      <button className="tbtn" title="Theme" onClick={onToggleTheme}>
        <Icon name={theme === "dark" ? "sun" : "moon"} size={16} />
      </button>
      <button className="tbtn" title="Settings" onClick={onOpenSettings}>
        <Icon name="gear" size={17} />
      </button>
    </div>
  );
}

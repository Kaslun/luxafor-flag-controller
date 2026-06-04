import { Icon } from "../icons";

export function Header({
  accent,
  theme,
  version,
  onToggleTheme,
  onOpenSettings,
}: {
  accent: string;
  theme: "dark" | "light";
  version: string;
  onToggleTheme: () => void;
  onOpenSettings: () => void;
}) {
  return (
    <div className="header">
      <div className="appmark">
        <span className="glyph" style={{ color: accent }}>
          <Icon name="beacon" size={18} />
        </span>
        <span className="title">
          <b>Beacon</b>&nbsp; for Luxafor
        </span>
        <span className="mono" style={{ fontSize: 11, color: "var(--text-3)", marginLeft: 4 }}>
          v{version}
        </span>
      </div>
      <div className="spacer" />
      <button className="tbtn" onClick={onToggleTheme} aria-label="toggle theme">
        <Icon name={theme === "dark" ? "sun" : "moon"} size={15} />
      </button>
      <button className="tbtn" onClick={onOpenSettings} aria-label="settings">
        <Icon name="gear" size={16} />
      </button>
    </div>
  );
}

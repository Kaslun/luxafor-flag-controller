import { Icon } from "../icons";

export function Header({
  accent,
  theme,
  onToggleTheme,
}: {
  accent: string;
  theme: "dark" | "light";
  onToggleTheme: () => void;
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
      </div>
      <div className="spacer" />
      <button className="tbtn" onClick={onToggleTheme} aria-label="toggle theme">
        <Icon name={theme === "dark" ? "sun" : "moon"} size={15} />
      </button>
    </div>
  );
}

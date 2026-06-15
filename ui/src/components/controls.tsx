// Small shared controls ported from the design (ui.jsx).

import { Icon } from "../icons";
import { DAYS, TIERS } from "../model";
import type { Tier } from "../types";

export function Switch({
  on,
  onClick,
  label,
}: {
  on: boolean;
  onClick: () => void;
  label?: string;
}) {
  return (
    <div
      className={"switch" + (on ? " on" : "")}
      role="switch"
      aria-checked={on}
      aria-label={label}
      tabIndex={0}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      onKeyDown={(e) => {
        if (e.key === " " || e.key === "Enter") {
          e.preventDefault();
          e.stopPropagation();
          onClick();
        }
      }}
    />
  );
}

export function TierSeg({
  value,
  onChange,
  live,
}: {
  value: Tier;
  onChange: (t: Tier) => void;
  live?: boolean;
}) {
  return (
    <div className={"seg" + (live ? " live" : "")}>
      {TIERS.map((t) => (
        <button key={t.id} className={value === t.id ? "on" : ""} onClick={() => onChange(t.id)}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function DayPicker({
  days,
  onToggle,
}: {
  days: number[];
  onToggle: (d: number) => void;
}) {
  return (
    <div className="daypick">
      {DAYS.map((d, i) => (
        <button
          key={i}
          className={days.includes(i) ? "on" : ""}
          aria-pressed={days.includes(i)}
          aria-label={d}
          onClick={() => onToggle(i)}
        >
          {d.slice(0, 2)}
        </button>
      ))}
    </div>
  );
}

export function Brightness({
  value,
  onChange,
  disabled = false,
}: {
  value: number;
  onChange: (n: number) => void;
  disabled?: boolean;
}) {
  return (
    <div
      className="bright"
      title={disabled ? "Brightness has no effect during a pattern effect" : undefined}
    >
      <Icon name="sun" size={15} />
      <input
        type="range"
        min={10}
        max={100}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label={`Brightness ${value}%`}
      />
      <span className="mono" style={{ fontSize: 11, minWidth: 30, textAlign: "right", opacity: disabled ? 0.5 : 1 }}>
        {value}%
      </span>
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  body,
  onAdd,
  addLabel,
}: {
  icon: string;
  title: string;
  body: string;
  onAdd: () => void;
  addLabel: string;
}) {
  return (
    <div className="empty">
      <div className="glyph">
        <Icon name={icon} size={26} />
      </div>
      <h3>{title}</h3>
      <p>{body}</p>
      <button className="btn primary" onClick={onAdd} style={{ margin: "0 auto" }}>
        <Icon name="plus" size={15} /> {addLabel} <Icon name="arrow" size={15} className="ar" />
      </button>
    </div>
  );
}

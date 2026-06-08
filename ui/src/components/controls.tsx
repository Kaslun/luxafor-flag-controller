// Small shared controls ported from the design (ui.jsx).

import { Icon } from "../icons";
import { DAYS, TIERS } from "../model";
import type { Tier } from "../types";

export function Switch({ on, onClick }: { on: boolean; onClick: () => void }) {
  return (
    <div
      className={"switch" + (on ? " on" : "")}
      role="switch"
      aria-checked={on}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
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
        <button key={i} className={days.includes(i) ? "on" : ""} onClick={() => onToggle(i)}>
          {d[0]}
        </button>
      ))}
    </div>
  );
}

export function Brightness({
  value,
  onChange,
}: {
  value: number;
  onChange: (n: number) => void;
}) {
  return (
    <div className="bright">
      <Icon name="sun" size={15} />
      <input
        type="range"
        min={10}
        max={100}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label="Brightness"
      />
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

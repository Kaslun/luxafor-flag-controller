import type { PaletteSlot, Routine } from "../types";
import { daysLabel, fmt12, hexOf } from "../model";
import { Icon } from "../icons";
import { DayPicker } from "./DayPicker";
import { SlotPicker } from "./SlotPicker";

export function RoutineRow({
  routine,
  palette,
  open,
  onOpen,
  onChange,
  onDelete,
}: {
  routine: Routine;
  palette: PaletteSlot[];
  open: boolean;
  onOpen: () => void;
  onChange: (r: Routine) => void;
  onDelete: () => void;
}) {
  const r = routine;
  const hex = hexOf(palette, r.color);
  const set = (patch: Partial<Routine>) => onChange({ ...r, ...patch });
  const toggleDay = (d: number) => {
    const has = r.days.includes(d);
    set({ days: has ? r.days.filter((x) => x !== d) : [...r.days, d] });
  };

  return (
    <div
      className={
        "routine" + (open ? " open" : "") + (r.enabled ? "" : " disabled")
      }
    >
      <div className="routine-row" onClick={onOpen}>
        <span
          className="r-swatch"
          style={{ background: hex, ["--sw" as string]: hex }}
        />
        <div className="r-info">
          <div className="r-name">{r.name || "Untitled routine"}</div>
          <div className="r-meta">
            <span className="days">{daysLabel(r.days)}</span>
            <span>
              {fmt12(r.start)} – {fmt12(r.end)}
            </span>
          </div>
        </div>
        <div className="r-right" onClick={(e) => e.stopPropagation()}>
          <div
            className={"switch" + (r.enabled ? " on" : "")}
            role="switch"
            aria-checked={r.enabled}
            onClick={() => set({ enabled: !r.enabled })}
          />
          <Icon name="chevron" size={18} className="chev" />
        </div>
      </div>

      {open && (
        <div className="routine-edit" onClick={(e) => e.stopPropagation()}>
          <div className="edit-grid">
            <div className="field">
              <label>Name</label>
              <input
                className="input"
                value={r.name}
                placeholder="New routine"
                onChange={(e) => set({ name: e.target.value })}
                autoFocus={!r.name}
              />
            </div>
            <div className="field">
              <label>Time window</label>
              <div className="time-pair">
                <input
                  className="input"
                  type="time"
                  value={r.start}
                  onChange={(e) => set({ start: e.target.value })}
                />
                <span>to</span>
                <input
                  className="input"
                  type="time"
                  value={r.end}
                  onChange={(e) => set({ end: e.target.value })}
                />
              </div>
            </div>
          </div>
          <div className="field">
            <label>Days</label>
            <DayPicker days={r.days} onToggle={toggleDay} />
          </div>
          <div className="field">
            <label>Color</label>
            <SlotPicker
              palette={palette}
              value={r.color}
              onChange={(c) => set({ color: c })}
            />
          </div>
          <div className="edit-foot">
            <button className="btn sm danger" onClick={onDelete}>
              <Icon name="trash" size={15} /> Delete
            </button>
            <button className="btn sm primary" onClick={onOpen}>
              <Icon name="check" size={15} /> Done
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

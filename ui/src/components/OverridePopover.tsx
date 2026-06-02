import { useState } from "react";
import type { ManualOverride, PaletteSlot } from "../types";
import { selectable } from "../model";
import { Icon } from "../icons";

const DURATIONS: [number, string][] = [
  [15, "15 min"],
  [30, "30 min"],
  [60, "1 hour"],
  [0, "Until I clear it"],
];

export function OverridePopover({
  palette,
  current,
  onSet,
  onClose,
}: {
  palette: PaletteSlot[];
  current: ManualOverride | null;
  onSet: (color: string, durationMinutes: number | null) => void;
  onClose: () => void;
}) {
  const [color, setColor] = useState(current?.color ?? "busy");
  const [dur, setDur] = useState(30);

  const commit = () => onSet(color, dur === 0 ? null : dur);

  return (
    <div className="scrim" onClick={onClose}>
      <div className="popover" onClick={(e) => e.stopPropagation()}>
        <div className="pop-head">
          <h3>Set a manual override</h3>
          <p>A quick status that isn't worth a routine. A real call still takes over.</p>
        </div>
        <div className="pop-body">
          <div className="field">
            <label>Color</label>
            <div className="ov-grid">
              {selectable(palette).map((p) => (
                <button
                  key={p.slot}
                  className={"ov-slot" + (color === p.slot ? " on" : "")}
                  onClick={() => setColor(p.slot)}
                >
                  <span className="sw" style={{ background: p.hex }} />
                  <span className="lbl">{p.name}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="field">
            <label>Duration</label>
            <div className="dur-row">
              {DURATIONS.map(([v, l]) => (
                <button
                  key={v}
                  className={"chip" + (dur === v ? " on" : "")}
                  onClick={() => setDur(v)}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button className="btn" onClick={onClose}>
              Cancel
            </button>
            <button className="btn primary" onClick={commit}>
              <Icon name="check" size={15} /> Set override
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

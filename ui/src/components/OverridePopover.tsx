import { useState } from "react";
import type { Effect, EffectsMeta, ManualOverride, PaletteSlot } from "../types";
import { Icon } from "../icons";
import { ColorEffectFields } from "./ColorEffectFields";

const DURATIONS: [number, string][] = [
  [15, "15 min"],
  [30, "30 min"],
  [60, "1 hour"],
  [0, "Until I clear it"],
];

export function OverridePopover({
  palette,
  effects,
  current,
  onSet,
  onClose,
}: {
  palette: PaletteSlot[];
  effects: EffectsMeta;
  current: ManualOverride | null;
  onSet: (color: string, durationMinutes: number | null, effect: Effect) => void;
  onClose: () => void;
}) {
  const [color, setColor] = useState(current?.color ?? "busy");
  // Default to a solid effect so opening the override and picking a color
  // reliably stops any pattern that was running.
  const [effect, setEffect] = useState<Effect>({ ...effects.default });
  const [dur, setDur] = useState(30);

  const commit = () => onSet(color, dur === 0 ? null : dur, effect);

  return (
    <div className="scrim" onClick={onClose}>
      <div className="popover" style={{ width: 440 }} onClick={(e) => e.stopPropagation()}>
        <div className="pop-head">
          <h3>Set a manual override</h3>
          <p>A quick status that isn't worth a routine. A real call still takes over.</p>
        </div>
        <div className="pop-body">
          <ColorEffectFields
            palette={palette}
            effects={effects}
            color={color}
            effect={effect}
            onColorChange={setColor}
            onEffectChange={setEffect}
          />
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

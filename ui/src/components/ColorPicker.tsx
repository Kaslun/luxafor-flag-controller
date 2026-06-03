import { useState } from "react";
import type { Effect, EffectsMeta, PaletteSlot } from "../types";
import { Icon } from "../icons";
import { ColorEffectFields } from "./ColorEffectFields";

/** Modal color + effect picker, opened by clicking a routine's color. */
export function ColorPicker({
  palette,
  effects,
  color: initialColor,
  effect: initialEffect,
  title = "Color & effect",
  onApply,
  onClose,
}: {
  palette: PaletteSlot[];
  effects: EffectsMeta;
  color: string;
  effect: Effect;
  title?: string;
  onApply: (color: string, effect: Effect) => void;
  onClose: () => void;
}) {
  const [color, setColor] = useState(initialColor);
  const [effect, setEffect] = useState<Effect>(initialEffect ?? { ...effects.default });

  return (
    <div className="scrim" onClick={onClose} style={{ zIndex: 60 }}>
      <div
        className="popover"
        style={{ width: 440 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="pop-head">
          <h3>{title}</h3>
          <p>Pick a preset, a custom color, and an optional effect.</p>
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
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button className="btn" onClick={onClose}>
              Cancel
            </button>
            <button className="btn primary" onClick={() => onApply(color, effect)}>
              <Icon name="check" size={15} /> Apply
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

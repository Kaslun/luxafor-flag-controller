import type { PaletteSlot } from "../types";
import { selectable } from "../model";

export function SlotPicker({
  palette,
  value,
  onChange,
}: {
  palette: PaletteSlot[];
  value: string;
  onChange: (slot: string) => void;
}) {
  return (
    <div className="slotpick">
      {selectable(palette).map((p) => (
        <button
          key={p.slot}
          type="button"
          className={"slotchip" + (value === p.slot ? " on" : "")}
          onClick={() => onChange(p.slot)}
        >
          <span className="sw" style={{ background: p.hex }} />
          {p.name}
        </button>
      ))}
    </div>
  );
}

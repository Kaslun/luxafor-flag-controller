import { useState } from "react";
import type { PaletteSlot } from "../types";
import { selectable } from "../model";
import { Icon } from "../icons";

/** Compact slot dropdown used in Settings. */
export function SlotMini({
  palette,
  value,
  onChange,
  disabled,
}: {
  palette: PaletteSlot[];
  value: string;
  onChange: (slot: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const cur = palette.find((p) => p.slot === value);

  return (
    <div
      style={{
        position: "relative",
        opacity: disabled ? 0.5 : 1,
        pointerEvents: disabled ? "none" : "auto",
      }}
    >
      <button
        className="btn sm"
        onClick={() => setOpen((o) => !o)}
        style={{ minWidth: 128, justifyContent: "space-between" }}
      >
        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              width: 14,
              height: 14,
              borderRadius: 4,
              background: cur?.hex ?? "#3A3A42",
              boxShadow: "inset 0 0 0 1px rgba(255,255,255,.25)",
            }}
          />
          {cur?.name ?? value}
        </span>
        <Icon name="chevron" size={15} />
      </button>
      {open && (
        <>
          <div
            style={{ position: "fixed", inset: 0, zIndex: 10 }}
            onClick={() => setOpen(false)}
          />
          <div
            style={{
              position: "absolute",
              top: "calc(100% + 6px)",
              right: 0,
              zIndex: 11,
              background: "var(--surface-1)",
              border: "1px solid var(--border-strong)",
              borderRadius: 10,
              boxShadow: "var(--shadow-pop)",
              padding: 6,
              width: 168,
            }}
          >
            {selectable(palette).map((p) => (
              <button
                key={p.slot}
                className="btn ghost"
                style={{ width: "100%", justifyContent: "flex-start", gap: 10 }}
                onClick={() => {
                  onChange(p.slot);
                  setOpen(false);
                }}
              >
                <span
                  style={{
                    width: 14,
                    height: 14,
                    borderRadius: 4,
                    background: p.hex,
                    boxShadow: "inset 0 0 0 1px rgba(255,255,255,.25)",
                  }}
                />
                {p.name}
                {p.slot === value && (
                  <Icon name="check" size={15} style={{ marginLeft: "auto" }} />
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

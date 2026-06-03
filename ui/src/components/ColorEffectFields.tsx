import type { Effect, EffectsMeta, PaletteSlot } from "../types";
import { hexOf, isHex, selectable } from "../model";

const TYPE_LABELS: Record<string, string> = {
  solid: "Solid",
  fade: "Fade",
  strobe: "Strobe",
  wave: "Wave",
  pattern: "Pattern",
};

function defaultEffect(meta: EffectsMeta): Effect {
  return { ...meta.default };
}

/** Reusable color + effect editor. Used inside the routine ColorPicker
 *  modal and inline in the override popover. */
export function ColorEffectFields({
  palette,
  effects,
  color,
  effect,
  onColorChange,
  onEffectChange,
  allowEffects = true,
}: {
  palette: PaletteSlot[];
  effects: EffectsMeta;
  color: string;
  effect: Effect;
  onColorChange: (color: string) => void;
  onEffectChange: (effect: Effect) => void;
  allowEffects?: boolean;
}) {
  const eff = effect ?? defaultEffect(effects);
  const setEff = (patch: Partial<Effect>) => onEffectChange({ ...eff, ...patch });
  const currentHex = hexOf(palette, color);
  const customActive = isHex(color);

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {/* presets */}
      <div className="field">
        <label>Preset</label>
        <div className="slotpick">
          {selectable(palette).map((p) => (
            <button
              key={p.slot}
              type="button"
              className={"slotchip" + (color === p.slot ? " on" : "")}
              onClick={() => onColorChange(p.slot)}
            >
              <span className="sw" style={{ background: p.hex }} />
              {p.name}
            </button>
          ))}
        </div>
      </div>

      {/* custom color */}
      <div className="field">
        <label>Custom color</label>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <input
            type="color"
            value={currentHex}
            onChange={(e) => onColorChange(e.target.value.toUpperCase())}
            style={{
              width: 44,
              height: 38,
              padding: 0,
              border: "1px solid var(--border-strong)",
              borderRadius: 9,
              background: "var(--field)",
              cursor: "pointer",
            }}
            aria-label="custom color"
          />
          <input
            className="input"
            style={{ fontFamily: "var(--font-mono)", maxWidth: 130 }}
            value={customActive ? currentHex : ""}
            placeholder={currentHex}
            onChange={(e) => {
              const v = e.target.value.trim();
              if (isHex(v)) onColorChange(v.startsWith("#") ? v.toUpperCase() : "#" + v.toUpperCase());
            }}
            aria-label="hex code"
          />
          <span
            className={"slotchip" + (customActive ? " on" : "")}
            style={{ cursor: "default" }}
          >
            <span className="sw" style={{ background: currentHex }} />
            {customActive ? "Custom" : "Using preset"}
          </span>
        </div>
      </div>

      {/* effect */}
      {allowEffects && (
        <div className="field">
          <label>Effect</label>
          <div className="segment" style={{ flexWrap: "wrap" }}>
            {effects.types.map((t) => (
              <button
                key={t}
                type="button"
                className={eff.type === t ? "on" : ""}
                onClick={() => setEff({ type: t })}
              >
                {TYPE_LABELS[t] ?? t}
              </button>
            ))}
          </div>

          {eff.type !== "solid" && (
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 6 }}>
              <span className="mono" style={{ fontSize: 12, color: "var(--text-3)" }}>
                Speed
              </span>
              <input
                type="range"
                min={effects.speed_min}
                max={effects.speed_max}
                value={eff.speed}
                onChange={(e) => setEff({ speed: Number(e.target.value) })}
                style={{ flex: 1, accentColor: "var(--accent)" }}
              />
              <span className="mono" style={{ fontSize: 12, width: 32, textAlign: "right" }}>
                {eff.speed}
              </span>
            </div>
          )}

          {eff.type === "wave" && (
            <select
              className="input"
              style={{ marginTop: 6 }}
              value={eff.wave_type}
              onChange={(e) => setEff({ wave_type: Number(e.target.value) })}
            >
              {effects.wave_types.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          )}

          {eff.type === "pattern" && (
            <>
              <select
                className="input"
                style={{ marginTop: 6 }}
                value={eff.pattern_id}
                onChange={(e) => setEff({ pattern_id: Number(e.target.value) })}
              >
                {effects.pattern_ids.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
              <p style={{ margin: "6px 0 0", fontSize: 12, color: "var(--text-3)" }}>
                Built-in patterns play their own colors — the color above is ignored.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export function effectLabel(effect?: Effect | null): string {
  if (!effect || effect.type === "solid") return "";
  return TYPE_LABELS[effect.type] ?? effect.type;
}

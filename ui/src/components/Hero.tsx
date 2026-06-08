import type { PaletteColor, State } from "../types";
import { hexOf, nameOf, effectType } from "../model";
import { Icon } from "../icons";
import { Flag } from "./Flag";
import { Brightness } from "./controls";

const EYEBROW: Record<string, string> = {
  trigger: "— live signal",
  override: "— manual",
  routine: "— scheduled",
  available: "— at your desk",
  dim: "— resting",
  off: "— off-hours",
  paused: "— paused",
  disconnected: "— no device",
  preview: "— preview",
};

export function Hero({
  state,
  palette,
  brightness,
  onBrightness,
  onOverride,
  onClearOverride,
  onTogglePause,
  onFlagClick,
}: {
  state: State;
  palette: PaletteColor[];
  brightness: number;
  onBrightness: (n: number) => void;
  onOverride: () => void;
  onClearOverride: () => void;
  onTogglePause: () => void;
  onFlagClick: () => void;
}) {
  const off =
    state.kind === "off" || state.kind === "paused" || state.kind === "disconnected";
  const statusHex = hexOf(palette, state.color);
  const hasOverride = state.manual_override !== null;
  const paused = state.paused;

  const heading =
    state.kind === "paused"
      ? "Paused"
      : state.kind === "disconnected"
      ? "Off"
      : state.kind === "off"
      ? "Off"
      : nameOf(palette, state.color);

  return (
    <div className="hero">
      <div className="hero-flag">
        <div style={{ cursor: "pointer" }} onClick={onFlagClick} title="Set a status">
          <Flag
            hex={statusHex}
            brightness={brightness / 100}
            off={off}
            effect={effectType(state.effect)}
            size={132}
            blink={state.kind === "disconnected"}
          />
        </div>
        <Brightness value={brightness} onChange={onBrightness} />
      </div>

      <div className="hero-main">
        <div className="hero-eyebrow">
          <span className="dot" />
          {EYEBROW[state.kind] || "— status"}
        </div>
        <h1 className="hero-status">
          <em>{heading}</em>
        </h1>

        {state.kind === "trigger" && (
          <div className="hero-reason">
            <Icon name="bolt" size={15} />
            <span>
              <b>{state.reason}</b> has the flag.
            </span>
          </div>
        )}
        {state.kind === "override" && (
          <div className="hero-reason">
            <Icon name="cursor" size={15} />
            <span>Set by hand.</span>
          </div>
        )}
        {state.kind === "routine" && (
          <div className="hero-reason">
            <Icon name="clock" size={15} />
            <span>
              <b>{state.reason}</b>
            </span>
          </div>
        )}
        {state.kind === "disconnected" && (
          <div className="hero-reason">
            <Icon name="plug" size={15} />
            <span>Plug your Luxafor back in.</span>
          </div>
        )}

        <div className="hero-actions">
          {hasOverride ? (
            <button className="btn" onClick={onClearOverride}>
              <Icon name="x" size={15} /> Clear
            </button>
          ) : (
            <button className="btn live" onClick={onOverride}>
              <Icon name="cursor" size={15} /> Set status
            </button>
          )}
          <button className="btn icon" title={paused ? "Resume" : "Pause"} onClick={onTogglePause}>
            <Icon name={paused ? "play" : "pause"} size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

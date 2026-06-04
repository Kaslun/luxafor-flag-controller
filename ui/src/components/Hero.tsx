import type { PaletteSlot, State } from "../types";
import { hexOf, nameOf } from "../model";
import { Icon, type IconName } from "../icons";
import { Flag } from "./Flag";

const REASON_LEAD =
  /^(In a call|Manual:|Paused|Off|Available|Dimmed|Flag disconnected)/;

function reasonIcon(kind: State["kind"]): IconName {
  switch (kind) {
    case "trigger":
      return "bolt";
    case "override":
      return "cursor";
    case "routine":
      return "clock";
    case "paused":
      return "pause";
    case "disconnected":
      return "plug";
    default:
      return "info";
  }
}

export function Hero({
  state,
  palette,
  onOverride,
  onClearOverride,
  onTogglePause,
}: {
  state: State;
  palette: PaletteSlot[];
  onOverride: () => void;
  onClearOverride: () => void;
  onTogglePause: () => void;
}) {
  const hex = hexOf(palette, state.color);
  const off = state.kind === "off" || state.kind === "paused" || state.kind === "disconnected";
  const dim = state.kind === "dim";
  const hasOverride = state.manual_override !== null;

  const eyebrow = state.paused
    ? "Paused"
    : state.kind === "disconnected"
    ? "No device"
    : "Current status";
  const heading = state.paused
    ? "Paused"
    : state.kind === "disconnected"
    ? "Disconnected"
    : nameOf(palette, state.color);

  // Bold the leading clause of the reason, matching the design.
  const m = state.reason.match(REASON_LEAD);
  const reasonNode = m ? (
    <span>
      <b>{m[0]}</b>
      {state.reason.slice(m[0].length)}
    </span>
  ) : (
    <span>{state.reason}</span>
  );

  return (
    <div className="hero">
      <div className="flagwrap">
        <Flag
          hex={hex}
          off={off}
          dim={dim}
          size={120}
          blink={state.kind === "disconnected"}
        />
      </div>
      <div className="hero-main">
        <div className="hero-eyebrow">
          <span className="dot" />
          {eyebrow}
        </div>
        <h1 className="hero-status">{heading}</h1>
        <div className="hero-reason">
          <Icon name={reasonIcon(state.kind)} size={16} />
          {reasonNode}
        </div>
        <div className="hero-actions">
          {hasOverride ? (
            <button className="btn" onClick={onClearOverride}>
              <Icon name="x" size={15} /> Clear override
            </button>
          ) : (
            <button className="btn primary" onClick={onOverride}>
              <Icon name="cursor" size={15} /> Set override
            </button>
          )}
          {hasOverride && (
            <button className="btn" onClick={onOverride}>
              <Icon name="pencil" size={15} /> Change
            </button>
          )}
          <button className="btn" onClick={onTogglePause}>
            <Icon name={state.paused ? "play" : "pause"} size={15} />{" "}
            {state.paused ? "Resume" : "Pause"}
          </button>
        </div>
      </div>
    </div>
  );
}

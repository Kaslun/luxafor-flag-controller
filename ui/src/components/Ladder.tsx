// Precedence ladder — what's showing now and what would take over.
// Ported from the design (ui.jsx Ladder).

import { Fragment } from "react";
import { Icon } from "../icons";
import type { Kind } from "../types";

export function Ladder({ activeKind }: { activeKind: Kind }) {
  const rungs = [
    { kind: "trigger", lab: "Triggers" },
    { kind: "override", lab: "Override" },
    { kind: "routine", lab: "Routines" },
    { kind: "rest", lab: "Resting" },
  ];
  const liveKind =
    activeKind === "trigger"
      ? "trigger"
      : activeKind === "override"
      ? "override"
      : activeKind === "routine"
      ? "routine"
      : "rest";

  return (
    <div className="ladder">
      {rungs.map((r, i) => {
        const on = r.kind === liveKind;
        return (
          <Fragment key={r.kind}>
            <div className={"rung" + (on ? " live" : "")}>
              <span className="rank">{i + 1}</span>
              <span className="lab">{r.lab}</span>
              {on && <span className="nowtag">now</span>}
            </div>
            {i < rungs.length - 1 && (
              <span className="rung-sep">
                <Icon name="chevron" size={15} className="caret" />
              </span>
            )}
          </Fragment>
        );
      })}
    </div>
  );
}

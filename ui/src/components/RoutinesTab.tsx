import { useState } from "react";
import type { Config, PaletteSlot, Routine } from "../types";
import { Icon } from "../icons";
import { RoutineRow } from "./RoutineRow";

export function RoutinesTab({
  config,
  palette,
  onChange,
}: {
  config: Config;
  palette: PaletteSlot[];
  onChange: (next: Config) => void;
}) {
  const [openId, setOpenId] = useState<string | null>(null);
  const routines = config.routines;

  const setRoutines = (next: Routine[]) => onChange({ ...config, routines: next });

  const addRoutine = () => {
    const id = "r" + Date.now();
    setRoutines([
      ...routines,
      {
        id,
        name: "",
        enabled: true,
        days: [0, 1, 2, 3, 4],
        start: "09:00",
        end: "17:00",
        color: "available",
      },
    ]);
    setOpenId(id);
  };

  const changeRoutine = (next: Routine) =>
    setRoutines(routines.map((r) => (r.id === next.id ? next : r)));

  const deleteRoutine = (id: string) => {
    setRoutines(routines.filter((r) => r.id !== id));
    if (openId === id) setOpenId(null);
  };

  return (
    <div>
      <div className="section-head">
        <div>
          <h2>Routines</h2>
          <p>
            Scheduled color blocks. Overlaps resolve automatically — a live call
            always wins.
          </p>
        </div>
        <button className="btn primary" onClick={addRoutine}>
          <Icon name="plus" /> Add routine
        </button>
      </div>

      {routines.length === 0 ? (
        <div className="empty">
          <div className="icon">
            <Icon name="calendar" size={26} />
          </div>
          <h3>No routines yet</h3>
          <p>
            Add a scheduled block — like lunch or a daily focus window — and the
            flag will switch colors on its own.
          </p>
          <button className="btn primary" onClick={addRoutine} style={{ margin: "0 auto" }}>
            <Icon name="plus" /> Add your first routine
          </button>
        </div>
      ) : (
        <div className="routine-list">
          {routines.map((r) => (
            <RoutineRow
              key={r.id}
              routine={r}
              palette={palette}
              open={openId === r.id}
              onOpen={() => setOpenId(openId === r.id ? null : r.id)}
              onChange={changeRoutine}
              onDelete={() => deleteRoutine(r.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

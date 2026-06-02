import { DAYS } from "../model";

export function DayPicker({
  days,
  onToggle,
}: {
  days: number[];
  onToggle: (day: number) => void;
}) {
  return (
    <div className="daypick">
      {DAYS.map((d, i) => (
        <button
          key={d}
          type="button"
          className={days.includes(i) ? "on" : ""}
          onClick={() => onToggle(i)}
        >
          {d[0]}
        </button>
      ))}
    </div>
  );
}

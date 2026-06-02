import { Icon } from "../icons";

export type TabId = "routines" | "settings";

export function Tabs({
  tab,
  onChange,
}: {
  tab: TabId;
  onChange: (t: TabId) => void;
}) {
  return (
    <>
      <div className="tabs">
        <button
          className={"tab" + (tab === "routines" ? " active" : "")}
          onClick={() => onChange("routines")}
        >
          <Icon name="list" /> Routines
        </button>
        <button
          className={"tab" + (tab === "settings" ? " active" : "")}
          onClick={() => onChange("settings")}
        >
          <Icon name="gear" /> Settings
        </button>
      </div>
      <div className="tabs-line" />
    </>
  );
}

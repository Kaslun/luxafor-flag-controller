import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { usePolling } from "./hooks/usePolling";
import { useTheme } from "./theme";
import { hexOf, inkFor, makeEffect, effectType } from "./model";
import type {
  Config,
  EffectsMeta,
  PaletteColor,
  Routine,
  State,
  Trigger,
  TriggerMeta,
} from "./types";
import { Header } from "./components/Header";
import { Hero } from "./components/Hero";
import { Flag } from "./components/Flag";
import { Ladder } from "./components/Ladder";
import { EmptyState } from "./components/controls";
import { Icon } from "./icons";
import { TriggerRow, RoutineRow } from "./components/rows";
import {
  ColorPicker,
  OverridePopover,
  PaletteEditor,
  SettingsModal,
  ConflictSheet,
  UpdateBanner,
  UpdateSheet,
} from "./components/modals";

interface PickerState {
  initial: string;
  initialEffect: string;
  allowEffects: boolean;
  hexOnly: boolean;
  title: string;
  eyebrow: string;
  z: number;
  onApply: (color: string, effect: string) => void;
}

/** Turn an engine validation error into something a person can act on. */
function humanizeSaveError(raw: string): string {
  if (/start must be before end|midnight span/i.test(raw))
    return "Couldn't save — a routine's end time must be after its start.";
  if (/invalid .*hex|invalid color/i.test(raw))
    return "Couldn't save — that colour isn't valid.";
  return "Couldn't save your change. It's been reverted.";
}

function routineActiveNow(r: Routine, now: Date): boolean {
  if (!r.enabled) return false;
  const d = (now.getDay() + 6) % 7; // Mon=0
  if (!r.days.includes(d)) return false;
  const [sh, sm] = r.start.split(":").map(Number);
  const [eh, em] = r.end.split(":").map(Number);
  const mins = now.getHours() * 60 + now.getMinutes();
  return mins >= sh * 60 + sm && mins < eh * 60 + em;
}

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const {
    data: state,
    failures,
    refresh: refreshState,
  } = usePolling<State>(api.getState, 3000);

  const [config, setConfig] = useState<Config | null>(null);
  const [effects, setEffects] = useState<EffectsMeta | null>(null);
  const [triggerMeta, setTriggerMeta] = useState<TriggerMeta | null>(null);

  const [openTrigger, setOpenTrigger] = useState<string | null>(null);
  const [openRoutine, setOpenRoutine] = useState<string | null>(null);
  const [picker, setPicker] = useState<PickerState | null>(null);
  const [showOverride, setShowOverride] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showPalette, setShowPalette] = useState(false);
  const [showConflict, setShowConflict] = useState(false);
  const [rechecking, setRechecking] = useState(false);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [updateDismissed, setUpdateDismissed] = useState(false);
  const [showUpdate, setShowUpdate] = useState(false);
  const [applying, setApplying] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [undo, setUndo] = useState<{ label: string; config: Config } | null>(null);
  const [, setTick] = useState(0);

  const putTimer = useRef<number | null>(null);
  const prevConflict = useRef(false);
  const prevFocusSeq = useRef<number | null>(null);
  const seenVersion = useRef<string | null>(null);
  const undoTimer = useRef<number | null>(null);

  useEffect(() => {
    api.getConfig().then(setConfig).catch((e) => setErr(String(e)));
    api.getEffects().then(setEffects).catch((e) => setErr(String(e)));
    api.getTriggerMeta().then(setTriggerMeta).catch((e) => setErr(String(e)));
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  // keep routine "active now" fresh
  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 30000);
    return () => window.clearInterval(id);
  }, []);

  // auto-open the conflict sheet when v2 is actively running
  useEffect(() => {
    const running = state?.conflict_detected?.luxafor_v2_running === true;
    if (running && !prevConflict.current) setShowConflict(true);
    prevConflict.current = running;
  }, [state?.conflict_detected]);

  // a second launch (or tray "Open Beacon") bumps focus_seq when a tab is
  // already open — bring this tab forward instead of spawning a duplicate.
  useEffect(() => {
    const seq = state?.focus_seq;
    if (seq == null) return;
    if (prevFocusSeq.current != null && seq > prevFocusSeq.current) {
      try {
        window.focus();
      } catch {
        /* best-effort: browsers may ignore cross-window focus */
      }
    }
    prevFocusSeq.current = seq;
  }, [state?.focus_seq]);

  // proactively prompt when an update is newly detected — once per version,
  // persisted so a page reload doesn't re-nag for the same version
  useEffect(() => {
    const uv = state?.update_available?.version ?? null;
    if (!uv) return;
    if (localStorage.getItem("beacon-update-prompted") !== uv) {
      localStorage.setItem("beacon-update-prompted", uv);
      setUpdateDismissed(false);
      setShowUpdate(true);
    }
  }, [state?.update_available]);

  // after an in-place update the engine relaunches and reuses this tab, but it
  // would still be running the OLD bundle. If the engine version changes from
  // what we first saw, reload to pick up the matching UI.
  useEffect(() => {
    const v = state?.version;
    if (!v) return;
    if (seenVersion.current == null) {
      seenVersion.current = v;
    } else if (seenVersion.current !== v) {
      window.location.reload();
    }
  }, [state?.version]);

  // make the tab itself a glance surface: title + favicon track live status
  useEffect(() => {
    if (!state || !config) return;
    const off = ["off", "paused", "disconnected"].includes(state.kind);
    const name =
      state.kind === "paused"
        ? "Paused"
        : state.kind === "disconnected"
        ? "No device"
        : state.kind === "off"
        ? "Off"
        : config.palette.find((p) => p.slot === state.color)?.name ??
          (state.color.startsWith("#") ? "Custom" : state.color);
    document.title = `${off ? "○" : "●"} ${name} — Beacon`;
    const hex = off
      ? "#9aa0a6"
      : config.palette.find((p) => p.slot === state.color)?.hex ??
        (state.color.startsWith("#") ? state.color : "#9aa0a6");
    const svg =
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">` +
      `<rect x="6" y="5" width="14" height="16" rx="4" fill="${hex}"/>` +
      `<rect x="18" y="4" width="3" height="24" rx="1.5" fill="#15191a"/></svg>`;
    let link = document.querySelector<HTMLLinkElement>("link[rel='icon']");
    if (!link) {
      link = document.createElement("link");
      link.rel = "icon";
      document.head.appendChild(link);
    }
    link.href = "data:image/svg+xml," + encodeURIComponent(svg);
  }, [state?.kind, state?.color, config?.palette]);

  const commitConfig = (next: Config) => {
    setConfig(next);
    if (putTimer.current) window.clearTimeout(putTimer.current);
    putTimer.current = window.setTimeout(() => {
      api.putConfig(next).catch((e) => {
        // the optimistic edit didn't persist — resync from the engine so the
        // UI can't keep showing unsaved state, and surface a human message
        setErr(humanizeSaveError(String(e)));
        api.getConfig().then(setConfig).catch(() => {});
      });
    }, 400);
  };

  const armUndo = (label: string) => {
    if (!config) return;
    setUndo({ label, config });
    if (undoTimer.current) window.clearTimeout(undoTimer.current);
    undoTimer.current = window.setTimeout(() => setUndo(null), 7000);
  };
  const doUndo = () => {
    if (undo) commitConfig(undo.config);
    setUndo(null);
  };

  // engine stopped responding (quit, crashed, or mid-update) — don't let the
  // tab sit on stale data pretending the flag is live
  if (failures >= 3) {
    return (
      <div className="app">
        <div className="dead">
          <div className="glyph">
            <Icon name="plug" size={26} />
          </div>
          <h2>Beacon isn't running</h2>
          <p>The engine stopped responding — it may have quit or be updating.</p>
          <button className="btn primary" onClick={refreshState}>
            <Icon name="refresh" size={15} /> Retry
          </button>
        </div>
      </div>
    );
  }

  if (!state || !config || !effects || !triggerMeta) {
    return (
      <div className="app">
        <div className="loading">Connecting to Beacon…</div>
      </div>
    );
  }

  const palette = config.palette;
  const settings = config.settings;
  const live = hexOf(palette, state.color);
  const liveInk = inkFor(live);
  const activeIds = new Set(state.active_triggers.map((a) => a.id));
  const now = new Date();

  /* ----- config edits ----- */
  const setTriggers = (triggers: Trigger[]) => commitConfig({ ...config, triggers });
  const setRoutines = (routines: Routine[]) => commitConfig({ ...config, routines });
  const setPalette = (p: PaletteColor[]) => commitConfig({ ...config, palette: p });
  const setSettings = (s: Config["settings"]) => commitConfig({ ...config, settings: s });

  const changeTrigger = (next: Trigger) =>
    setTriggers(config.triggers.map((t) => (t.id === next.id ? next : t)));
  const deleteTrigger = (id: string) => {
    const t = config.triggers.find((x) => x.id === id);
    armUndo(`Deleted ${t?.name || "trigger"}`);
    setTriggers(config.triggers.filter((t) => t.id !== id));
    if (openTrigger === id) setOpenTrigger(null);
  };
  const addTrigger = () => {
    const id = "t" + Date.now();
    setTriggers([
      ...config.triggers,
      { id, name: "", enabled: true, type: "mic", color: "busy", priority: 70, params: {}, effect: effects.default },
    ]);
    setOpenTrigger(id);
  };

  const changeRoutine = (next: Routine) =>
    setRoutines(config.routines.map((r) => (r.id === next.id ? next : r)));
  const deleteRoutine = (id: string) => {
    const r = config.routines.find((x) => x.id === id);
    armUndo(`Deleted ${r?.name || "routine"}`);
    setRoutines(config.routines.filter((r) => r.id !== id));
    if (openRoutine === id) setOpenRoutine(null);
  };

  const deletePaletteColor = (i: number) => {
    armUndo(`Deleted ${palette[i]?.name || "colour"}`);
    setPalette(palette.filter((_, idx) => idx !== i));
  };
  const addRoutine = () => {
    const id = "r" + Date.now();
    setRoutines([
      ...config.routines,
      { id, name: "", enabled: true, days: [0, 1, 2, 3, 4], start: "09:00", end: "17:00", color: "available", effect: effects.default },
    ]);
    setOpenRoutine(id);
  };

  /* ----- colour picker openers ----- */
  const pickTriggerColor = (t: Trigger) =>
    setPicker({
      initial: t.color, initialEffect: effectType(t.effect), allowEffects: true, hexOnly: false,
      title: t.name || "Trigger colour", eyebrow: "— colour & effect", z: 60,
      onApply: (color, fx) => { changeTrigger({ ...t, color, effect: makeEffect(fx, t.effect) }); setPicker(null); },
    });
  const pickRoutineColor = (r: Routine) =>
    setPicker({
      initial: r.color, initialEffect: effectType(r.effect), allowEffects: true, hexOnly: false,
      title: r.name || "Routine colour", eyebrow: "— colour & effect", z: 60,
      onApply: (color, fx) => { changeRoutine({ ...r, color, effect: makeEffect(fx, r.effect) }); setPicker(null); },
    });
  const recolorSlot = (i: number) =>
    setPicker({
      initial: palette[i].hex, initialEffect: "solid", allowEffects: false, hexOnly: true,
      title: palette[i].name, eyebrow: "— recolour", z: 80,
      onApply: (hex) => {
        setPalette(palette.map((s, idx) => (idx === i ? { ...s, hex, led: null } : s)));
        setPicker(null);
      },
    });
  const pickResting = () =>
    setPicker({
      initial: settings.available_color, initialEffect: "solid", allowEffects: false, hexOnly: false,
      title: "Default at the desk", eyebrow: "— resting colour", z: 80,
      onApply: (color) => { setSettings({ ...settings, available_color: color }); setPicker(null); },
    });

  /* ----- live actions ----- */
  const setOverride = (color: string, dur: number | null, fx: string) => {
    api.setOverride(color, dur, makeEffect(fx)).then(refreshState).catch((e) => setErr(String(e)));
    setShowOverride(false);
  };
  const clearOverride = () => api.clearOverride().then(refreshState).catch((e) => setErr(String(e)));
  const togglePause = () =>
    (state.paused ? api.resume() : api.pause()).then(refreshState).catch((e) => setErr(String(e)));
  const setBrightness = (n: number) => setSettings({ ...settings, brightness: n });
  const toggleAutostart = () =>
    api.setAutostart(!state.autostart_enabled).then(refreshState).catch((e) => setErr(String(e)));
  const recheck = () => {
    setRechecking(true);
    api.recheckConflict().then(refreshState).catch((e) => setErr(String(e))).finally(() => setRechecking(false));
  };
  const checkUpdate = () => {
    setUpdateDismissed(false);
    setCheckingUpdate(true);
    api.recheckUpdate().then(refreshState).catch((e) => setErr(String(e))).finally(() => setCheckingUpdate(false));
  };
  const installUpdate = () => {
    setApplying(true);
    api.applyUpdate().catch((e) => { setApplying(false); setErr(String(e)); });
  };
  const openLogs = () => api.openLogs().catch((e) => setErr(String(e)));

  const conflictActive = state.conflict_detected != null;
  const conflictForSheet = state.conflict_detected ?? { luxafor_v2_running: false, luxafor_v2_startup: false };

  return (
    <div className="app" style={{ ["--live" as string]: live, ["--live-ink" as string]: liveInk }}>
      <Header
        theme={theme}
        version={state.version}
        onToggleTheme={toggleTheme}
        onOpenPalette={() => setShowPalette(true)}
        onOpenSettings={() => setShowSettings(true)}
      />

      <div className="body">
        <Hero
          state={state}
          palette={palette}
          brightness={settings.brightness}
          onBrightness={setBrightness}
          onOverride={() => setShowOverride(true)}
          onClearOverride={clearOverride}
          onTogglePause={togglePause}
          onFlagClick={() => setShowOverride(true)}
        />

        <div className="content">
          {err && (
            <div className="banner error">
              <Icon name="alert" size={18} />
              <div className="bx">{err}</div>
              <button className="btn sm ghost icon" title="Dismiss" onClick={() => setErr(null)}>
                <Icon name="x" size={15} />
              </button>
            </div>
          )}
          {state.update_available && !updateDismissed && (
            <UpdateBanner
              update={state.update_available}
              onInstall={installUpdate}
              onDismiss={() => setUpdateDismissed(true)}
            />
          )}
          {conflictActive && !showConflict && (
            <div className="banner">
              <Icon name="alert" size={18} />
              <div className="bx">
                <b>Another app is using your flag.</b> Beacon detected the old Luxafor app.
              </div>
              <button className="btn sm" onClick={() => setShowConflict(true)}>
                Fix
              </button>
            </div>
          )}

          <div className="ladder-cap eye">
            — where your status comes from (triggers rank by importance)
          </div>
          <Ladder
            activeKind={state.kind}
            dimmed={state.kind === "paused" || state.kind === "disconnected"}
          />

          <div className="sec">
            <span className="eye">
              <Icon name="bolt" size={14} /> — triggers
            </span>
            <button className="btn sm primary" onClick={addTrigger}>
              <Icon name="plus" size={14} /> Add
            </button>
          </div>
          {config.triggers.length === 0 ? (
            <EmptyState
              icon="bolt"
              title="Nothing's watching yet"
              body="Point Beacon at a signal — a call, the webcam, a locked screen — and the flag reacts on its own."
              addLabel="Add a trigger"
              onAdd={addTrigger}
            />
          ) : (
            <div className="rlist">
              {config.triggers.map((t) => (
                <TriggerRow
                  key={t.id}
                  trigger={t}
                  palette={palette}
                  triggerMeta={triggerMeta}
                  active={activeIds.has(t.id) && t.enabled}
                  regError={(state.hotkey_errors ?? []).includes(t.id)}
                  open={openTrigger === t.id}
                  onOpen={() => setOpenTrigger(openTrigger === t.id ? null : t.id)}
                  onChange={changeTrigger}
                  onDelete={() => deleteTrigger(t.id)}
                  onPickColor={() => pickTriggerColor(t)}
                />
              ))}
            </div>
          )}

          <div style={{ height: 28 }} />

          <div className="sec">
            <span className="eye">
              <Icon name="clock" size={14} /> — routines
            </span>
            <button className="btn sm primary" onClick={addRoutine}>
              <Icon name="plus" size={14} /> Add
            </button>
          </div>
          {config.routines.length === 0 ? (
            <EmptyState
              icon="calendar"
              title="No scheduled colours"
              body="Add a block — lunch, a daily focus window — and the flag switches colour by the clock."
              addLabel="Add a routine"
              onAdd={addRoutine}
            />
          ) : (
            <div className="rlist">
              {config.routines.map((r) => (
                <RoutineRow
                  key={r.id}
                  routine={r}
                  palette={palette}
                  activeNow={routineActiveNow(r, now)}
                  open={openRoutine === r.id}
                  onOpen={() => setOpenRoutine(openRoutine === r.id ? null : r.id)}
                  onChange={changeRoutine}
                  onDelete={() => deleteRoutine(r.id)}
                  onPickColor={() => pickRoutineColor(r)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {applying && (
        <div className="scrim" style={{ zIndex: 90 }}>
          <div className="pop" style={{ width: 380 }}>
            <div className="pop-body" style={{ alignItems: "center", textAlign: "center" }}>
              <div style={{ display: "grid", placeItems: "center", padding: "8px 0" }}>
                <Flag hex={live} brightness={1} size={72} />
              </div>
              <h3 style={{ margin: 0, font: "600 16px var(--font-body)" }}>Updating Beacon…</h3>
              <p style={{ margin: 0, fontSize: 13, color: "var(--fg-muted)" }}>
                Downloading and installing the new version. Beacon will close and reopen
                automatically — you can close this tab.
              </p>
            </div>
          </div>
        </div>
      )}

      {showOverride && (
        <OverridePopover
          palette={palette}
          current={state.manual_override}
          onSet={setOverride}
          onClose={() => setShowOverride(false)}
        />
      )}
      {showPalette && (
        <PaletteEditor
          palette={palette}
          onChange={setPalette}
          onRecolor={recolorSlot}
          onDelete={deletePaletteColor}
          onClose={() => setShowPalette(false)}
        />
      )}
      {showSettings && (
        <SettingsModal
          settings={settings}
          palette={palette}
          version={state.version}
          autostart={state.autostart_enabled}
          update={state.update_available}
          checking={checkingUpdate}
          onChange={setSettings}
          onToggleAutostart={toggleAutostart}
          onPickResting={pickResting}
          onOpenPalette={() => { setShowSettings(false); setShowPalette(true); }}
          onCheckUpdate={checkUpdate}
          onInstallUpdate={installUpdate}
          onOpenLogs={openLogs}
          onClose={() => setShowSettings(false)}
        />
      )}
      {showConflict && (
        <ConflictSheet
          conflict={conflictForSheet}
          connected={state.device_connected}
          rechecking={rechecking}
          onRecheck={recheck}
          onDismiss={() => setShowConflict(false)}
        />
      )}
      {showUpdate && state.update_available && (
        <UpdateSheet
          version={state.version}
          update={state.update_available}
          installing={applying}
          onInstall={() => {
            setShowUpdate(false);
            installUpdate();
          }}
          onLater={() => setShowUpdate(false)}
        />
      )}
      {picker && (
        <ColorPicker
          palette={palette}
          initial={picker.initial}
          initialEffect={picker.initialEffect}
          allowEffects={picker.allowEffects}
          hexOnly={picker.hexOnly}
          title={picker.title}
          eyebrow={picker.eyebrow}
          z={picker.z}
          onApply={picker.onApply}
          onClose={() => setPicker(null)}
        />
      )}
      {undo && (
        <div className="toast" role="status">
          <span>{undo.label}</span>
          <button className="btn sm" onClick={doUndo}>
            <Icon name="refresh" size={13} /> Undo
          </button>
        </div>
      )}
    </div>
  );
}

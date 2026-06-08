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
  const { data: state, refresh: refreshState } = usePolling<State>(api.getState, 3000);

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
  const [applying, setApplying] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [, setTick] = useState(0);

  const putTimer = useRef<number | null>(null);
  const prevConflict = useRef(false);
  const prevFocusSeq = useRef<number | null>(null);

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

  const commitConfig = (next: Config) => {
    setConfig(next);
    if (putTimer.current) window.clearTimeout(putTimer.current);
    putTimer.current = window.setTimeout(() => {
      api.putConfig(next).catch((e) => setErr(String(e)));
    }, 400);
  };

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
    setRoutines(config.routines.filter((r) => r.id !== id));
    if (openRoutine === id) setOpenRoutine(null);
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
            <div className="banner">
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

          <div className="ladder-cap eye">— what's showing now, and what would take over</div>
          <Ladder activeKind={state.kind} />

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
          rechecking={rechecking}
          onRecheck={recheck}
          onDismiss={() => setShowConflict(false)}
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
    </div>
  );
}

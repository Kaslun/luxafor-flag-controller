import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { usePolling } from "./hooks/usePolling";
import { accentFor, inkFor } from "./model";
import { useTheme } from "./theme";
import type { Config, Effect, EffectsMeta, PaletteSlot, State } from "./types";
import { Header } from "./components/Header";
import { Hero } from "./components/Hero";
import { Flag } from "./components/Flag";
import { Tabs, type TabId } from "./components/Tabs";
import { RoutinesTab } from "./components/RoutinesTab";
import { SettingsTab } from "./components/SettingsTab";
import { OverridePopover } from "./components/OverridePopover";
import { ConflictSheet } from "./components/ConflictSheet";
import { UpdateBanner, ConflictBanner } from "./components/Banners";

export default function App() {
  const [theme, toggleTheme] = useTheme();
  const { data: state, refresh: refreshState } = usePolling<State>(api.getState, 3000);

  const [palette, setPalette] = useState<PaletteSlot[]>([]);
  const [effects, setEffects] = useState<EffectsMeta | null>(null);
  const [config, setConfig] = useState<Config | null>(null);

  const [tab, setTab] = useState<TabId>("routines");
  const [showOverride, setShowOverride] = useState(false);
  const [showConflict, setShowConflict] = useState(false);
  const [rechecking, setRechecking] = useState(false);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [updateDismissed, setUpdateDismissed] = useState(false);
  const [applying, setApplying] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const putTimer = useRef<number | null>(null);
  const prevConflict = useRef(false);

  // one-time loads
  useEffect(() => {
    api.getPalette().then(setPalette).catch((e) => setErr(String(e)));
    api.getEffects().then(setEffects).catch((e) => setErr(String(e)));
    api.getConfig().then(setConfig).catch((e) => setErr(String(e)));
  }, []);

  // Auto-open the conflict sheet only when Luxafor is actively *running*
  // (live flicker, urgent). For a startup-only entry the dismissible banner
  // is enough — no need to nag with a modal on every launch.
  useEffect(() => {
    const running = state?.conflict_detected?.luxafor_v2_running === true;
    if (running && !prevConflict.current) setShowConflict(true);
    prevConflict.current = running;
  }, [state?.conflict_detected]);

  // debounced config PUT
  const commitConfig = (next: Config) => {
    setConfig(next);
    if (putTimer.current) window.clearTimeout(putTimer.current);
    putTimer.current = window.setTimeout(() => {
      api.putConfig(next).catch((e) => setErr(String(e)));
    }, 400);
  };

  if (!state || !config || palette.length === 0 || !effects) {
    return (
      <div data-theme={theme} className="app" style={{ placeItems: "center", display: "grid" }}>
        <div className="muted">Connecting to Beacon…</div>
      </div>
    );
  }

  const off =
    state.kind === "off" || state.kind === "paused" || state.kind === "disconnected";
  const accent = accentFor(palette, state.color, off, theme);
  const accentInk = inkFor(accent);

  const conflictActive = state.conflict_detected != null;
  const conflictForSheet = state.conflict_detected ?? {
    luxafor_v2_running: false,
    luxafor_v2_startup: false,
  };

  const setOverride = (
    color: string,
    durationMinutes: number | null,
    effect: Effect
  ) => {
    api
      .setOverride(color, durationMinutes, effect)
      .then(refreshState)
      .catch((e) => setErr(String(e)));
    setShowOverride(false);
  };
  const clearOverride = () =>
    api.clearOverride().then(refreshState).catch((e) => setErr(String(e)));
  const togglePause = () =>
    (state.paused ? api.resume() : api.pause())
      .then(refreshState)
      .catch((e) => setErr(String(e)));

  const toggleAutostart = () =>
    api
      .setAutostart(!state.autostart_enabled)
      .then(refreshState)
      .catch((e) => setErr(String(e)));

  const recheck = () => {
    setRechecking(true);
    api
      .recheckConflict()
      .then(refreshState)
      .catch((e) => setErr(String(e)))
      .finally(() => setRechecking(false));
  };

  const checkUpdate = () => {
    setUpdateDismissed(false);
    setCheckingUpdate(true);
    api
      .recheckUpdate()
      .then(refreshState)
      .catch((e) => setErr(String(e)))
      .finally(() => setCheckingUpdate(false));
  };

  const installUpdate = () => {
    setApplying(true);
    // On success the engine exits ~1s later to let the swap script replace
    // the exe and relaunch (which opens a fresh window). Keep the overlay up.
    api.applyUpdate().catch((e) => {
      setApplying(false);
      setErr(String(e));
    });
  };

  const openLogs = () => api.openLogs().catch((e) => setErr(String(e)));

  return (
    <div
      data-theme={theme}
      className="app"
      style={{
        ["--accent" as string]: accent,
        ["--accent-ink" as string]: accentInk,
      }}
    >
      <Header
        accent={accent}
        theme={theme}
        version={state.version}
        onToggleTheme={toggleTheme}
      />

      <div className="win-body">
        <Hero
          state={state}
          palette={palette}
          onOverride={() => setShowOverride(true)}
          onClearOverride={clearOverride}
          onTogglePause={togglePause}
        />

        <Tabs tab={tab} onChange={setTab} />

        <div className="content">
          {err && (
            <div className="banner warn">
              <div className="bx">{err}</div>
              <button className="btn sm" onClick={() => setErr(null)}>
                Dismiss
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
            <ConflictBanner
              conflict={state.conflict_detected!}
              onFix={() => setShowConflict(true)}
            />
          )}

          {tab === "routines" ? (
            <RoutinesTab
              config={config}
              palette={palette}
              effects={effects}
              onChange={commitConfig}
            />
          ) : (
            <SettingsTab
              config={config}
              palette={palette}
              onChange={commitConfig}
              autostartEnabled={state.autostart_enabled}
              onToggleAutostart={toggleAutostart}
              version={state.version}
              updateAvailable={state.update_available}
              checking={checkingUpdate}
              onCheckUpdate={checkUpdate}
              onInstallUpdate={installUpdate}
              onOpenLogs={openLogs}
            />
          )}
        </div>
      </div>

      {applying && (
        <div className="scrim" style={{ zIndex: 80 }}>
          <div className="popover" style={{ width: 380, textAlign: "center" }}>
            <div className="pop-body" style={{ alignItems: "center" }}>
              <div style={{ display: "grid", placeItems: "center", padding: "8px 0" }}>
                <Flag hex={accent} size={72} />
              </div>
              <h3 style={{ margin: 0, font: "600 16px var(--font-display)" }}>
                Updating Beacon…
              </h3>
              <p style={{ margin: 0, fontSize: 13, color: "var(--text-2)" }}>
                Downloading and installing the new version. Beacon will close and
                reopen in a fresh window automatically — you can close this tab.
              </p>
            </div>
          </div>
        </div>
      )}

      {showOverride && (
        <OverridePopover
          palette={palette}
          effects={effects}
          current={state.manual_override}
          onSet={setOverride}
          onClose={() => setShowOverride(false)}
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
    </div>
  );
}

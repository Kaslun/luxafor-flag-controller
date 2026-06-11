# Beacon — Developer Hand-off & Project Review

_Last updated: 2026-06-11, at v0.1.16. Written as an onboarding + improvement
guide for the next developer. Everything below was verified against the code,
not from memory; file pointers are given throughout._

---

## 1. What this is

**Beacon** drives a Luxafor Flag 2 USB LED from local Windows signals so the
flag shows your real status. One Python process: a tick-loop engine, a
loopback-only FastAPI server serving a built React UI, and a pystray tray
icon. Distributed as a PyInstaller onefile exe + Inno Setup per-user
installer, released via GitHub Actions with an in-place auto-updater.

```
engine/__main__.py     entry: single-instance, port pick, uvicorn, tray, browser
engine/loop.py         BeaconEngine: 5s tick — sample signals → evaluate
                       triggers → resolve → write HID report (+ heartbeat)
engine/resolver.py     pure resolve(now, state, config) → ResolvedStatus
                       ladder: paused > disconnected > preview >
                       (triggers ⋈ override by priority) > routines > floor
engine/config.py       dataclasses + validation + JSON persistence + migrations
                       (Trigger, Routine, PaletteColor, Settings)
engine/device.py       raw hidapi; validated 8-byte report, written twice
engine/effects.py      effect dict → HID report; animation-stop logic
engine/mic.py, webcam.py, session.py, hotkeys.py   signal detectors
engine/app.py          FastAPI routes + static UI mount
engine/tray.py         pystray icon/menu (⚠ still uses the old static palette)
engine/selfupdate.py   download → sha256 verify → detached batch swap → relaunch
ui/src/               React 18 + Vite + TS; KML design system in styles/tokens.css
```

**Key invariants (do not regress):**
- HID report `[0x00, 0x01, 0xFF, R, G, B, 0, 0]`, written **twice** (first-write drop).
- Leaving a firmware animation (strobe/wave/pattern) requires sending
  `PATTERN_OFF_REPORT` first (`effects.report_is_animation`, `loop.py` ~line 340) —
  a plain static write does **not** stop the firmware animation. Device-verified.
- The engine loop must never die silently: the whole tick iteration is
  try/excepted, plus a done-callback on the task (`app.py` lifespan). This was
  a real shipped bug (frozen flag); keep the guards.
- CI release must keep the **smoke-launch gate** (`release.yml`): it launches
  the built exe and curls `/api/state` before publishing. It exists because a
  Python 3.12/3.13 runner split once shipped an exe whose bootloader wanted
  `python312.dll` while the bundle carried `python313.dll`. Pin = **3.13**,
  invoked as `python -m PyInstaller`.
- The update swap script must strip `_MEIPASS2`/`_PYI_*` env vars before
  relaunching (`selfupdate.py`) or the new exe reuses the old, deleted
  extraction dir and dies with "Failed to load Python DLL".
- `python -m pytest` masks import errors that bare `pytest` (CI) hits; test
  modules must not import siblings.

**Config migrations** are implicit and additive (`config_from_dict`): a config
missing `triggers` is seeded from legacy `call_*`/`lock_*` settings; missing
`palette` gets the default 6 slots with LED-tuned `led` hexes; missing
`brightness` defaults to 80. Colors are either `#RRGGBB` or a *slot reference*
resolved against the live palette at write time (deleted slot → black).

---

## 2. Known bugs (verified in code, ordered by impact)

1. **Tray is stale-palette and off-brand** — `tray.py` imports `SELECTABLE`,
   `rgb_of`, `name_of` from the *static* `engine/palette.py`. User-edited or
   custom palette colours render black/raw-id in the tray icon, status line,
   and the Override submenu. The icon is also still the old-design rounded
   rect. Fix: read `engine.config.palette` everywhere in tray.py and rebuild
   the menu when config changes (pystray menus are callables, so most of it is
   live already; the override list is built once at startup).

2. **Hotkey re-capture is swallowed by the hotkey itself** — while a hotkey
   trigger is enabled, `RegisterHotKey` consumes its combo system-wide, so the
   browser's "press a combo" capture field never receives that combo (or any
   colliding one). Fix: add `POST /api/hotkeys/suspend` + `resume` that the
   capture field calls (HotkeyManager already supports unregister/reload via
   thread messages).

3. **Hidden-tab throttling can defeat tab-dedup** — `client_alive()` window is
   8s (`loop.py`), but Chrome throttles hidden-tab timers to ≥1/min after ~5
   minutes, so a long-backgrounded tab reads as "no tab" and a second launch
   opens a duplicate again. Fix: widen the window to ~75s, and/or have the UI
   send an immediate poll on `visibilitychange`/`pagehide` keepalive.

4. **Hotkey registration failures are silent for the user** — reserved combos
   (many Win+X) fail `RegisterHotKey` and are only logged. The UI shows the
   combo as if it works. Fix: surface per-trigger registration status on
   `/api/state` (e.g. `hotkey_errors: [trigger_id]`) and badge the row.

5. **Update prompt re-fires on every page reload** — `promptedUpdateFor` is a
   React ref (`App.tsx`), so a reload re-prompts for the same version.
   Intended "once per version"; persist the prompted version in
   `localStorage`.

6. **Deleting a referenced palette slot silently blacks the flag** — the
   palette editor lets you delete a slot still used by triggers/routines/
   resting colour; the engine then resolves it to black with no warning.
   Fix: on delete, either warn-and-remap references to a fallback slot, or
   block deletion while referenced.

7. **Disconnected state reads as "Off"** — `Hero.tsx` heading shows "Off" for
   `kind === "disconnected"` (eyebrow says "— no device", but the big Fraunces
   word is misleading). Give it its own heading ("No device") and the plug
   reason line (the reason line exists; the heading is wrong).

8. **`fade` preview mismatch** — the UI previews fade as a looping pulse
   (`flag-fade` CSS), but device command 0x02 is a one-shot fade-to-colour.
   Either loop it engine-side (re-send on heartbeat) or change the preview.
   Related: animated effects are deliberately excluded from the heartbeat
   (`is_solid` check, loop.py ~350), so an external writer can permanently
   stomp a strobe/wave until the next state change.

9. **Brightness appears dead during patterns** — firmware patterns ignore RGB,
   so the brightness slider does nothing while one runs. Cosmetic, but the UI
   gives no hint.

10. **Override expiry is invisible (regression)** — the old design showed
    "Manual: Focus until 3:30pm"; the redesign's minimal reasons dropped it
    and nothing now shows remaining time, even though `manual_override.expiry`
    is on the wire. Add a countdown chip to the hero when an override is set.

---

## 3. Pain points

**User-facing**
- **SmartScreen**: unsigned exe → "Windows protected your PC" on every new
  machine. Code signing is the single highest-leverage distribution fix
  (Azure Trusted Signing is the cheap route; sign both exe and installer in
  `release.yml`).
- **Autostart now opens a browser tab at every sign-in** (changed when fixing
  "starts in background" — `__main__.py` opens the dashboard on *every*
  launch). Some users will hate a tab at login. Make it a setting
  (`open_on_autostart`, default on) and pass `--autostart` through again.
- **Browser-tab app model**: `window.focus()` from a background tab rarely
  raises the window, the tab can be closed accidentally, and Beacon lives in
  the tab strip. A dedicated window via Edge/Chrome `--app=http://127.0.0.1:p`
  (detect browser, fall back to default) would make launch/focus/dedup
  rock-solid and look native. This is the cleanest structural improvement
  available for the front-end experience.
- **No visibility into history** — `history.sqlite` records every transition
  but nothing reads it. Either ship a small timeline view ("what was my day")
  or stop writing it. It also has **no retention policy** (unbounded growth).

**Developer-facing**
- **No linting/formatting anywhere**: no ruff/black for Python, no ESLint/
  Prettier for TS (verified: no configs, none in manifests). Add ruff +
  eslint+prettier and run them in `ci.yml`.
- **Manual version bump** in `engine/version.py` must match the tag or the
  release fails (a guard exists in release.yml, which is good, but deriving
  the version from the tag — or a `bump` script — would remove the footgun).
- **No CHANGELOG**; release notes are auto-generated from commits only.
- **Dead code** (verified): `palette.as_payload()` (the live palette is served
  from config now), `__main__._open_browser_soon()`, the vestigial
  `force_show`/`first_run`/`autostart_launch` flags, and the `--show` arg the
  update swap still passes. Tailwind is fully unused but still installed
  (`ui/tailwind.config.js`, `tailwindcss` dep, postcss plugin) — remove it
  for faster builds.
- `scripts/build.ps1` duplicates the CI steps and has drifted (CI now does
  smoke-test + installer); consolidate or document it as "local UI+exe only".
- Repo hygiene: `.pytest_cache/` and `beacon_luxafor.egg-info/` are tracked;
  add to `.gitignore`.

---

## 4. Missing features (gaps in what exists)

- **More trigger types** — the framework makes each a small add (detector fn +
  meta entry + optional param field). Scoped and ready: **idle/away**
  (`GetLastInputInfo` + minutes param), **foreground app / window title**
  (`GetForegroundWindow`), **presentation/full-screen DND**
  (`SHQueryUserNotificationState`), **any process running** (psutil, already a
  dep). Further out: Wi-Fi SSID/VPN, Focus Assist state (undocumented
  registry/WNF — fragile), audio-playing.
- **Calendar busy** (Outlook COM / Graph) — deliberately deferred by the build
  spec; the biggest "real status" win if internal users live in Outlook.
- **Multi-condition triggers** — AND/OR (e.g. "mic AND webcam → On camera"),
  and time-scoping a trigger ("only on weekdays").
- **Settings not exposed**: `heartbeat_interval_seconds`, port, tick interval.
- **Config export/import & diagnostics bundle** (config + log zip) for support.
- **First-run onboarding** — the conflict sheet covers the Luxafor-v2 case but
  there's no welcome/tour for triggers/routines/palette.
- **Tray quick actions** — brightness, pause until time, "open dashboard" as
  default double-click action.
- **Wave/pattern effects lost their UI** — the engine still supports them and
  configs may carry them, but the redesigned picker only offers
  solid/fade/strobe (matches the design prototype). Decide: re-expose behind
  an "advanced" disclosure, or deprecate in the engine.
- **No favicon / dynamic tab title** — the tab is anonymous; title could show
  live status ("● Busy — Beacon"), favicon could be the flag glyph in the
  current colour (cheap, high-polish).

---

## 5. Design review (KML system, implemented at v0.1.12)

The Kasper Mork Lunde reskin is faithfully ported: Fraunces reserved for the
single hero status word, Geist body/mono, north-green dark / warm-paper light,
aurora↔puffin accent flip, em-dash labels, pill buttons, numbered precedence
ladder with NOW badge, Hue-style wheel picker, frosted flag render with
brightness bloom. Tokens live in `ui/src/styles/tokens.css` (single source).

**What's strong**
- The `--live` (status colour) vs `--accent` (brand chrome) split is clean and
  consistently applied; theme flip works end-to-end.
- The precedence ladder genuinely explains the resolver — keep it in sync if
  the ladder ever changes.
- Minimal copy holds up; rows lean on icons as intended.

**Gaps / inconsistencies to fix**
1. **Tray icon + window icon are off-brand** (old palette, old shape — see
   bug #1) and there's **no favicon**, so the brand stops at the page edge.
   `packaging/icon.ico` / `scripts/make_icon.py` also predate the redesign.
2. **Error styling**: the generic error banner in `App.tsx` reuses the warm
   `.banner` (accent-warm tint). Errors should use `--error` (#ff5470); add a
   `.banner.error` variant.
3. **Disconnected hero** (bug #7): heading says "Off"; design intent is a
   distinct no-device state.
4. **Override has no time affordance** (bug #10) — also a design gap: the
   hero's "Clear" button gives no hint of what/until-when.
5. **Accessibility is the weakest area**: switches are `<div role="switch">`
   with no keyboard handling or focus styles; icon buttons rely on `title`
   only (no `aria-label`); the colour wheel is pointer-only (no keyboard or
   text-equivalent beyond the hex field — the hex field saves this, barely);
   modals don't trap focus or close on Escape. A focused a11y pass
   (tab-reachable switches, Escape-to-close, `:focus-visible` rings using
   `--accent`) is a day of work and worth it.
6. **i18n-readiness**: copy was minimised for localisation but every string is
   hardcoded in components. If localisation is real, introduce a strings
   module now while the surface is small (~60 strings).
7. **Empty-state copy** is still sentence-length; the design brief said
   "icons speak". Minor.
8. **Reduced motion** is handled for rows and flag animations
   (`prefers-reduced-motion`), but the hero bloom transition isn't gated.
   Trivial fix.
9. **Light-theme contrast**: muted text `#5a625e` on `#f5f1e8` ≈ 4.6:1 — passes
   AA for body, borderline for the 11px mono labels. Consider darkening
   `--light-text-muted` one step.

---

## 6. Testing & CI

- **89 pytest tests**, all green, fast (<0.5s). Good coverage: resolver
  ladder, trigger priority/migration, palette/brightness config, effects
  reports, mic/webcam registry walks (faked winreg), conflict detection,
  selfupdate script generation.
- **Not covered**: the hotkey thread (only smoke-tested manually),
  device layer (manual-only, fine), tray, selfupdate end-to-end (the dir-swap
  mechanics were only validated with dummy files + live usage), and **the
  entire UI** (no component or e2e tests; `tsc` is the only gate). A small
  Playwright suite against `python -m engine` + built UI would catch the
  class of "modal renders at opacity 0" bugs the design tool itself hit.
- **CI** (`ci.yml`): pytest + UI build on Windows. **Release** (`release.yml`):
  build → **smoke-launch gate** → installer → sha256-stamped `version.json` →
  GitHub Release. Keep the gate; consider adding the pytest suite to the
  release job too (currently only ci.yml runs tests — a tag push skips them).
  ⚠ That's a real hole: **a tagged release never runs the test suite.**

---

## 7. Suggested priority order

1. **Release-job test gap** (run pytest in release.yml) — one line, closes a
   real hole.
2. **Tray palette sync + brand pass** (bug #1) — user-visible daily.
3. **Hotkey capture suspend + registration feedback** (bugs #2, #4).
4. **Tab-dedup hardening** (bug #3) or jump straight to **`--app` dedicated
   window**, which subsumes it.
5. **Code signing** in CI — unblocks wider distribution.
6. **Override countdown + disconnected heading + error banner variant**
   (bugs #7, #10, design #2) — small UI batch.
7. **Idle/away + foreground-app triggers** — the two most-requested signal
   types, both trivial on the framework.
8. **A11y pass + favicon/dynamic title** — polish batch.
9. **Lint/format + dead-code sweep + .gitignore hygiene** — do alongside any
   of the above.

---

## 8. Operational notes

- **AppData**: `%APPDATA%\Beacon\` — `config.json` (atomic writes),
  `beacon.log` (rotating 5×1MB), `history.sqlite`, `instance.json` (port),
  `beacon-new.exe`/`beacon-update.bat` (transient, during update).
- **Updates**: manifest is `version.json` on the latest GitHub release;
  checked at startup + every 6h; `POST /api/update/apply` downloads, verifies
  sha256, spawns the swap batch, exits. Updating **from 0.1.9/0.1.10** still
  uses those versions' buggy swap script (one DLL-error dialog; relaunch
  manually once) — anyone on ≥0.1.11 is clean.
- **Security posture**: loopback-only API, no auth (deliberate v1 — any local
  process can control the flag and rewrite config; acceptable for internal
  use, revisit before any broader distribution). Updater trusts GitHub TLS +
  manifest sha256. Hotkeys use `RegisterHotKey`, not a keyboard hook — Beacon
  never sees unregistered keystrokes.
- **Known support FAQ**: Luxafor v2 app fights for the HID handle (conflict
  sheet guides quit + de-startup); SmartScreen "More info → Run anyway";
  startup-disabled v2 entries are correctly ignored via `StartupApproved`.

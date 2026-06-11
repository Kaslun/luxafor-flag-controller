# Beacon — UX Review

_2026-06-11, at v0.1.16. Companion to HANDOFF.md (visual/brand review lives
there, §5). This pass walks every user journey through the shipped UI code;
every finding below was verified in source, with file pointers. Severity:_
**[A] breaks the user's mental model or silently loses work · [B] misleading
state · [C] friction · [D] polish.**

---

## 0. The product's UX contract

Beacon is an *ambient* tool. The success metric is: after ten minutes of
setup, the user never opens the dashboard again except to change a status by
hand. That implies three things everything below is judged against:

1. **The glance must never lie** — flag, tray, and dashboard must agree and
   reflect reality within a tick.
2. **The model must be learnable once** — triggers › override › routines ›
   resting, then trusted forever.
3. **Hand edits must be cheap and safe** — fast to make, hard to lose, easy
   to undo.

---

## 1. [A] The precedence story contradicts itself

The app teaches its core model in two places — and they disagree.

- The **ladder** (`Ladder.tsx`) presents a fixed order: `1 Triggers ›
  2 Override › 3 Routines › 4 Resting`.
- The **tier hints** (`rows.tsx` ~220) say a *Normal* trigger "yields to a
  manual override" — so triggers are not unconditionally rank 1.
- And the *Low* hint — "**Low** only shows when nothing else is active" — is
  **false**: in `resolver.py` the trigger band sits above routines
  unconditionally, so a Low trigger beats an active routine whenever no
  override is set.

A user who sets a Low "screen locked" trigger and a Lunch routine will watch
lock-yellow override lunch-orange and have no way to reconcile that with the
copy. This is the most important UX fix in the app, because the whole product
is this model.

**Fix options** (pick one, don't band-aid):
- *Make the ladder true*: render Override as a band that splits triggers —
  `High/Critical triggers › Override › Normal/Low triggers › Routines ›
  Resting` — and fix the Low hint ("Low still outranks routines").
- *Or make the copy true*: change the resolver so Low triggers genuinely rank
  below routines (give tiers real bands: Critical/High above override, Normal
  between override and routines, Low below routines). This is the better
  product: tiers become honest positions in the ladder, and the ladder can
  highlight exactly where each trigger sits.

## 2. [A] Edits can silently fail and diverge from reality

`App.tsx` `commitConfig` applies every edit optimistically, debounces 400ms,
PUTs — and on failure only sets a raw error string (e.g. `routine 'r17':
start must be before end (no midnight span)`). Consequences:

- The UI keeps showing the **unsaved** state; a reload reverts it. The user
  thinks they created the routine; tomorrow it's gone.
- The error copy is the engine's validation message — developer English, in a
  warning-tinted banner (not even error-styled).
- The easiest way to hit it: set a routine's end before its start, which the
  paired `<input type="time">` fields happily allow.

**Fix:** validate inline before commit (time order, hotkey completeness) so
the API error path is truly exceptional; on PUT failure, re-fetch config to
resync and show a human message ("Couldn't save — end time must be after
start"). Related feature gap: **night-shift users cannot express 22:00–02:00
at all** (`config.py` rejects midnight spans) — the engine's resolver could
support wrapping windows with a small change to `active_routine`.

## 3. [A] The tab dies silently — twice over

- `usePolling` returns an `error`, but `App.tsx` line 55 never destructures
  it. If the engine quits (tray → Quit) or crashes, the open tab **freezes on
  stale data forever** — flag says Busy, reality is off. The glance lies.
- After an in-place update, the relaunched engine reuses the still-open tab
  (dedup working as designed) — but that tab is running the **old JS bundle**
  against the new engine. There is no version-mismatch reload
  (verified: no `location.reload` anywhere). Schema drift between versions
  will produce undefined behaviour the user can't diagnose.

**Fix:** consume the polling error — after ~3 failed polls show a "Beacon
isn't running" takeover state with a retry; and on every state poll, compare
`state.version` to the bundle's built-in version and `location.reload()` on
mismatch (one line of build-time injection + one effect).

## 4. [B] States that mislead

- **Paused highlights "Resting · NOW"** in the ladder (`Ladder.tsx` maps
  every non-trigger/override/routine kind to `rest`). Paused means "Beacon
  isn't controlling the flag" — the opposite of a resting status. Grey the
  ladder out when paused instead.
- **Disconnected says "Off"** in the hero heading (`Hero.tsx`) — already in
  HANDOFF as a bug; through the UX lens it's worse: "Off" is a *successful*
  state (off-hours), so the user can't distinguish "working as intended" from
  "unplugged".
- **The conflict sheet hardcodes "Beacon found your flag — Connected over
  USB"** as a completed step (`modals.tsx` ~556) even when the device is
  disconnected. First-run users with an unplugged flag get told it's
  connected. Drive it from `state.device_connected`.
- **Pause is an unlabeled icon toggle** next to "Set status". Pause is the
  most destructive ambient action in the app (flag stops reflecting reality)
  and it's a 40px icon with a tooltip. When paused, the only cues are the
  hero text and tray bars. Consider a persistent "Paused — resume" banner in
  the content area; a paused ambient device should nag gently.

## 5. [B] Triggers can't be trusted because they can't be tested

The design prototype let you click a trigger's live-dot to *simulate* the
signal; the real app's dot is display-only. So after creating a webcam
trigger the only way to verify it works is to start a real call. Combined
with silent hotkey-registration failures (HANDOFF bug #4), the user has no
way to build confidence in their setup.

**Fix:** a "Test" affordance per row — for mic/webcam/lock, a transient
3-second simulated fire (engine already has the plumbing: inject into
`active_triggers` like preview does); for hotkeys, show registration status
and "press your combo now" feedback.

## 6. [C] Friction in the daily loop

- **Manual status = 3 clicks** (Set status → preset → Set), and the popover
  leads with the full wheel/duration machinery. The 90% case is "Busy, 30
  min". Consider one-click preset chips directly in the hero actions row
  (the palette is right there), with the popover as the "more…" path. The
  tray *is* the quick path but is currently broken for edited palettes
  (HANDOFF bug #1) — fixing the tray is part of this story.
- **Override countdown invisible** (HANDOFF #10): "Clear" gives no clue
  what's set or until when.
- **Flag-click opens the override popover** — pleasant, but undiscoverable
  (title tooltip only) and inconsistent: in the picker, the flag is a
  preview; in the hero it's a button. Low priority.
- **Day picker reads `M T W T F S S`** (`controls.tsx` line 52, `d[0]`).
  Tue/Thu and Sat/Sun are indistinguishable — a classic. Use `Mo Tu We Th Fr
  Sa Su` (also dodges the localisation trap of single letters).
- **Hotkey capture accepts invalid combos**: `captureHotkey` (`model.ts`)
  fires for a modifier-less key (e.g. bare `Esc` — which also *binds* Escape
  instead of cancelling the capture). The engine then silently never
  registers it (`hotkeys.py` requires vk + modifier). Fix: Esc cancels
  listening; combos without a modifier show "add Ctrl/Alt/Shift/Win" inline
  and don't commit.
- **Trigger latency is up to 5s** (tick interval) — fine, but during setup it
  reads as "not working". A "checking…" shimmer on the live-dot for the first
  tick after an edit would absorb the wait.

## 7. [C] No undo, no confirmation, anywhere

Deleting a trigger, routine, or palette colour is instant and irreversible
(`rows.tsx`, `modals.tsx` PaletteEditor) — and palette deletion can silently
black the flag if referenced (HANDOFF #6). For an app whose config is small,
the cheapest robust fix is a single-level **undo toast** ("Deleted 'Deep
work' — Undo") rather than confirm dialogs; config is already replaced
wholesale per edit, so undo = keep the previous Config in a ref.

## 8. [C] Brightness & palette edges

- The brightness slider gives no value feedback, has no reset, and — because
  `dim` off-behaviour multiplies `dim_rgb`(0.15) by brightness — at low
  brightness "Dim" is indistinguishable from "Off". Clamp dim's floor or show
  %.
- Recolouring a default slot drops its LED tuning (`led: null`, by design) —
  the flag may then render the colour noticeably differently from the swatch,
  with no explanation. One sentence in the recolour picker ("the flag shows
  colours more vividly than the screen") would pre-empt confusion.
- Brightness does nothing during firmware patterns (HANDOFF #9) — disable the
  slider with a tooltip while a pattern effect is live.

## 9. [D] Polish

- **Keyboard**: nothing is operable without a mouse — switches are divs,
  modals don't close on Escape, the wheel is pointer-only (the hex field is
  the only lifeline). One a11y pass covers this (HANDOFF §5.5).
- **Empty states** are good (clear CTA, honest copy). The seeded demo
  triggers/routines on first run are a smart implicit tutorial — keep them.
- **Header icon buttons** rely on `title` tooltips; fine, but the palette
  icon's purpose ("template colours") is guessable at best. The Settings →
  "Colour palette → Edit" path covers discovery, so this is minor.
- **No favicon / static tab title** — for a tab-based app, the tab *is* the
  app icon. A flag favicon tinted to the live status colour plus
  "● Busy — Beacon" title would make the tab itself a glanceable surface —
  cheap and very on-product.
- The **update prompt** stack (sheet → banner → settings) is well-layered;
  just persist the per-version dismissal (HANDOFF #5) so it doesn't re-prompt
  on every reload.

---

## Priority order (UX-only; merges into HANDOFF §7)

1. **Resolve the precedence contradiction** (§1) — decide ladder-true vs
   copy-true; everything else about trust hangs off this.
2. **Failure honesty batch** (§2, §3): inline validation + resync-on-failure;
   dead-engine takeover state; version-mismatch auto-reload.
3. **Misleading states batch** (§4): paused ladder, disconnected heading,
   conflict sheet device step.
4. **Trigger confidence** (§5): test affordance + hotkey feedback.
5. **Daily-loop friction** (§6): hero preset chips, override countdown, day
   labels, hotkey capture rules.
6. **Undo toast** (§7) and the §8 edges.
7. **Favicon/title + a11y pass** (§9).

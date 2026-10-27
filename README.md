# Genshin Wish Probability Calculator — v1.0.3

Version 1.0.3 makes number formatting consistent and fixes first-paint flashes
and keyboard focus visibility. Probability models and engine results are unchanged.

- **Wishes and copies:** grouped whole numbers (`1,200`), including summaries,
  history, confidence thresholds, slider accessibility text, budget differences,
  and readable text exports. Native number inputs keep editable numeric values.
- **Averages:** E[T] and E[T | success] always show exactly one decimal place
  (`162.0`, `1,234.5`), independently of the precision setting. Undefined averages
  remain `—`.
- **Calculated probabilities:** the precision setting still controls decimal
  places, with the existing `<0.01%` / `>99.99%` guards at precision 2.
  Confidence preset controls retain their whole-percent labels. Exported raw
  JSON retains original numeric values for analysis.

A small parser-blocking `web/startup.js` applies validated saved appearance
settings before the stylesheet/body paint. It owns the shared English/Chinese
translations and settings validation. A temporary parser observer translates
incoming labels before rendering, even if the deferred calculator script is
slow or fails; it disconnects at DOMContentLoaded. Theme, font size, animations,
and language use the existing `wishlab.settings.v1` storage schema, including
legacy font migration. Invalid or blocked storage uses defaults. No content is
hidden during startup: if JavaScript is disabled or fails to load, the static
English page remains readable, with a CSS system-light fallback. Interactive
calculations require JavaScript (or the Python CLI).

Keyboard controls now share an opaque 3 px accent outline in both themes.
Inputs no longer suppress that outline or add a competing faint glow. The
transparent confidence range draws its single keyboard outline around the
visible axis. Forced-color mode uses the system highlight color.

Version 1.0.2 fixes result visibility, request feedback, and version drift.
After a successful calculation or a history selection, the app waits for the
layout animation to finish before checking the result card. If its heading and
leading content are outside a comfortable viewport area, it scrolls them into
view. Focus moves to the result heading only when scrolling is needed and focus
has stayed on the initiating action (or the document body). An already-visible
result keeps the user's scroll position and focus. On short screens the leading
section is the target rather than requiring the whole tall card to fit.
Reduced-motion and animation-off preferences use an immediate reveal.

While a request runs, a visible loading panel and placeholder replace old
numbers. Cancel buttons are available beneath Calculate and in the result
feedback. A **30-second timeout** aborts the browser request and restores the
controls. Failures, cancellation, and timeouts are shown prominently in the
result card, with a retry action; network/validation/server failures also remain
reported beside the form. If a last successful result exists, it is restored
with an explicit previous-result label. Unsuccessful attempts are never saved
to history, and late responses from cancelled/timed-out attempts cannot replace
a newer calculation. Retry submits the current form inputs.

Cancellation stops waiting in the browser; an already-running synchronous
backend calculation may still finish on the server. No probability-engine
cancellation or numerical behavior was changed.

All displayed app versions now come from the FastAPI `VERSION`: the top bar,
localized footer, About panel, and text-export header share the backend value.
The UI loads it from `GET /api/version`; a fresh calculation's backend-supplied
version also refreshes it. If no backend version is available, the UI/export
says “unavailable” rather than using a hard-coded or saved-history version.
Historical record versions remain in the raw export data as provenance and do
not replace the live app version.

Version 1.0.1 refines the web interface: a centered, wider wish-plan card opens
the page, then moves left when results are available. The three result cards
enter on the right (or stack beneath the plan on mobile). Mode selection and
the confidence axis now use smooth sliding indicators. All input surfaces and
result panels share the same subtle gradient texture.

Settings now opens as a frosted-glass, Windows-style window with a left sidebar:
**Calculator Settings**, **Appearance**, **Language Preferences**, and **Help
Center**. The lower-left sidebar carries the Wish Lab icon and name. Each time
you open Settings it starts on Calculator Settings. Keyboard arrows, Home, and
End navigate categories; Escape closes the window. The close icon is centered,
and standard number/select controls share a consistent 44 px height.

Font size is selectable in **1 px increments from 10 to 20 px**, with **14 px**
as the new default. Existing saved Small/Default/Large preferences migrate to
their previous 14/16/18 px equivalents. About Calculator and the version number
appear together in Help Center, followed by Terms & Policies and then the
author contact link, each on a separate row.

Layout, mode, and confidence animations obey both the animation toggle and the
system reduced-motion preference. Calculation behavior and model assumptions
are unchanged.

Version 1.0 adds a responsive, bilingual web planner built on the existing
character, weapon, and combined probability engines. The original Python APIs
and command-line planner remain available.

## Run the web calculator

From the repository root (Python 3.10 or later; 3.12 is tested):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[web]"
.\.venv\Scripts\python.exe -m uvicorn web.backend:app --host 127.0.0.1 --port 8000
```

Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)**. FastAPI serves both the
page and API, so a second development server is unnecessary. Open this address
instead of double-clicking `web/index.html`. Stop the server with Ctrl+C.
If the environment is already configured, only the final command is needed.

### Web features

- The main mode switch selects **Character**, **Weapon**, or **Character +
  Weapon**. Combined mode always finishes characters first, then spends the
  remaining wishes on the supplied weapon state.
- The web UI always uses the existing **community soft-pity assumptions** and,
  for characters, the configurable **community Capturing Radiance counter
  model**, starting at C1. The expandable counter field allows C0–C3. The web UI
  deliberately has no probability-model switches; the Python and CLI model
  options remain available.
- The result shows exact success probability, unconditional average wishes to
  target, and average completion wishes conditional on success within budget.
- Ranked outcomes show the top N most likely **stop-at-target** copy counts,
  plus your requested outcome if it falls outside the top N. Its rank is always
  displayed. Exact ties share a competition rank, with deterministic copy-count
  ordering for display. The list is capped at each requested target, rather
  than modeling continued pulls after success.
- The 0–100% confidence axis snaps to 50/75/90/95/99%, with 0% and 100% endpoints.
  Preset buttons and arrow/Home/End keyboard controls are supported. The number
  shown is the **minimum total wish budget** for that probability, not the
  expected wait. Exactly 100% uses the existing structural model bound.
- The latest **five calculations** appear below Calculate. They load on opening
  the page; selecting a record restores its inputs and exact result. The initial
  screen stays centered without automatically opening the latest result.
  Turning history off hides the history section entirely.
- Bottom-left **Settings** includes history on/off and a `.txt` export, display
  precision (0–10 decimal places, default 2), top outcomes (1–10, default 3),
  system/dark/light themes, font sizes (10–20 px, default 14 px), animations,
  English/Chinese, and help in separate sidebar pages.
  Dark mode retains the original blue/violet design with clearer input outlines;
  light mode uses a white/silver gradient. System theme and reduced-motion
  preferences are respected.
- The Help Center contains the model explanation, current version, Terms and
  Policies, and the author's
  [GitHub issue page](https://github.com/nv2rdwzksh-eng/Genshin-Wish-Probability-Calculator/issues).

Settings and history are stored in this browser's `localStorage`, without a
server-side history database or analytics. Turning history off removes the
saved records and prevents new ones being stored; the current result remains
visible for the session. Clear removes history without disabling it. Export is
available when history is on and contains records: it includes all saved inputs,
unrounded probabilities, ranks, thresholds, and model assumptions. Blocked or
unavailable browser storage falls back to session-only state. The calculator
backend receives form inputs; local server logs may record request metadata.

Precision changes only formatting. Tiny nonzero probabilities are shown with
`<`/near-certain probabilities with `>` when rounding would otherwise imply
0% or 100%. The calculations retain their original floating-point precision.
Inputs changing after a calculation mark the displayed result as stale.

Interactive web limits are **0–2,000 wishes** and **0–10 target copies per
banner**; underlying engine APIs retain their general limits and configurability.
A zero-copy target is already met. Targets count new copies for this plan.
These limits bound local server work; they are not claims about game mechanics.

### Web architecture and outcome semantics

`web/index.html`, `web/style.css`, and `web/script.js` implement the interface
without a frontend build step or third-party CDN. `web/backend.py` validates
requests and calls the existing public target-aware planning APIs. The engine
and model files are unchanged.

For combined copy outcomes, unfinished character trajectories have zero weapon
copies. For trajectories completing the character target at time t:

```text
P(C=K, W>=j) = sum_t P(TC=t) * P(TW(j)<=N-t)
P(C=K, W=j)  = P(C=K, W>=j) - P(C=K, W>=j+1)
```

Each additional weapon-target CDF is calculated once over all remaining
budgets, and adjacent tails give the exact endpoint count probabilities.
This supplies ranked joint outcomes without a giant joint-state DP or a
separate weapon calculation per possible character completion time.

For the 240-wish combined example (character pity 37, no guarantee, C1, target
2; fresh weapon state, target 1), the web result is **45.74509331%**. Its
90/95/99% budgets are **332/353/403**. The corresponding character-only result
is **91.04958393%**. A fresh weapon target of one copy in 120 wishes gives
**70.66535051%**. All values retain the existing probability assumptions.

**Results are exact under the selected community modeling assumptions**, not a
promise of the live game's outcome. The hidden CR counter, its C2 trigger
chance, and per-wish soft-pity curves are not officially published formulas.
No new Genshin mechanics or engine regression values are introduced in v1.0.1.

### Web verification

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[web,web-test]"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The optional web tests use FastAPI's test client and check all modes, validation,
static serving, historical probability regressions, exact ranks, probability
mass, and tiny sequential-reference agreement for joint outcomes. They are
skipped if the web/test extras are absent, so engine-only installations still
run the original suite.

For the separate real-browser smoke test, leave the server running and install
Node Playwright locally:

```powershell
npm install --no-save --package-lock=false playwright
npx playwright install chromium
node tests/web_smoke.cjs
```

This checks navigation, all three calculations, confidence keyboard controls,
history restore/cap/off, text export, translations, appearance, mobile overflow,
and error recovery. It also verifies the centered-to-results transition, settings
sidebar navigation/default page, centered close icon, uniform control heights,
numeric font sizes, old-history compatibility, and reduced-motion behavior.
Screenshots are written under ignored `artifacts/web-v101/`.
Optional environment variables `WISH_WEB_URL`, `PLAYWRIGHT_MODULE`, and
`PLAYWRIGHT_CHROMIUM_EXECUTABLE` select an existing test server or installation.

The dedicated v1.0.2 browser regression check exercises actual desktop/mobile
viewports (including 761/760 px), history selection, no-op reveals for already
visible results, reduced motion, delayed responses, cancellation, timeout with
a browser test clock, retries, HTTP/network/invalid-response failures, and API
version propagation through both languages and exported files:

```powershell
node tests/web_reliability.cjs
```

Its screenshots are saved under ignored `artifacts/web-v102/`. It uses the same
Playwright environment overrides as the smoke test.

The v1.0.3 browser check covers integer/average/probability formatting, exports,
first contentful paint with the deferred script held back and cache disabled,
saved/system appearance, both languages, reloads, disabled/failed JavaScript,
malformed/blocked storage, and keyboard focus/contrast in both themes:

```powershell
node tests/web_consistency.cjs
```

It uses the same environment overrides and saves screenshots in ignored
`artifacts/web-v103/`. These rendering checks use headless Chromium; they do not
claim a physical-device or cross-browser accessibility audit.
v1.0.3 verification: **127 Python tests** and **332 browser checks** passed
(88 smoke, 52 reliability, 192 consistency), with no unexpected browser errors.

v0.5 adds exact sequential **character target -> weapon target** planning.
The two existing target-aware engines provide first-completion distributions;
the new composition layer uses them to spend one shared budget, stopping at
each target. Interactive reports and exact combined confidence thresholds are
available through the CLI.

v0.4.1 adds optional, configurable Capturing Radiance to character planning.
Existing model constructors keep CR disabled for compatibility; enable the
community counter assumption explicitly as described below.

v0.4 adds an independent exact Weapon Event Wish planner to the existing
Character Event Wish planner. Both report finite-budget probabilities,
first-completion and remaining-budget distributions, expected completion
times, and exact inverse thresholds. v1.0 now exposes these engines in the web UI.

v0.3.2 makes the normal planner follow the user's stopping policy: once the
requested number of copies is obtained, wishing on that goal stops. The older
continued-pulling calculation remains available as an explicit analysis mode.

## Two different questions

The project now names two semantics rather than mixing them:

1. **Target-aware planning (default):** “I have at most N wishes and stop as
   soon as I obtain K copies.” Successful probability is stored by the first
   completion wish, so unused wishes remain available for a future goal.
2. **Full-distribution analysis (advanced):** “I spend exactly N wishes on this
   banner regardless of earlier results.” This can produce K+1, K+2, and higher
   copy counts.

Both modes have the same probability of reaching at least K copies by wish N.
Their final copy distributions differ. For example, if every wish were a
featured 5-star, a target of 1 with a budget of 3 ends at exactly 1 copy under
target-aware planning, but at exactly 3 copies under continued pulling.

Target-aware planning is the default because it better represents ordinary
wish budgeting and supplies the remaining-budget distribution used by combined
sequential-goal planning.

## Combined character -> weapon planning (v0.5)

The player spends wishes on the character banner until the character target is
reached, then immediately switches to the weapon banner with all remaining
wishes. The weapon phase starts from its supplied initial weapon state.
Character pulls do not change weapon pity, promoted guarantee, or Fate Points.
Both phases stop as soon as their own target is met.

This model assumes the supplied banner states and selected probability models
remain valid for their respective phases. It does not model calendar-driven
banner expiration or changing the selected weapon during the plan. Capturing
Radiance and both soft-pity schedules remain configurable as before.

Let `TC` be the additional wishes needed for the character target and `TW` the
weapon wishes needed from its fixed starting state. Conditional on character
completion at wish `t`, the weapon phase receives `N-t` wishes. Therefore:

```text
P(both within N) = sum_t P(TC=t) * P(TW <= N-t)
P(total completion at s) = sum_t P(TC=t) * P(TW=s-t)
```

The second formula is a finite convolution of the two completion PMFs. Its
cumulative sum gives the first formula for every total budget. Each banner's
target-aware calculation runs once per prepared distribution. The weapon DP
is not recomputed for every character completion time. Multiplying the two
standalone full-budget success probabilities would incorrectly give both
phases access to the same wishes and is not used.

### API and distributions

`combined_planning.py` adds `CharacterGoal` and `WeaponGoal` adapters that call
only the existing public target-aware and structural-bound APIs. Its reusable
PMF convolution and small `TargetGoal` contract consume common planning results,
without sharing or combining banner state representations. The engines remain
unchanged. v0.5 exposes only the specified two-phase order; arbitrary sequences
and reverse ordering are not implemented.

```python
from genshin_wish import (
    CharacterGoal, WeaponGoal, WishState, WeaponWishState,
    community_soft_pity_model, community_weapon_soft_pity_model,
    with_capturing_radiance, deterministic_combined_wishes_to_target,
    prepare_combined_distribution,
)

character = CharacterGoal(
    initial_state=WishState(pity=37, cr_counter=1),
    target_copies=2,
    model=with_capturing_radiance(community_soft_pity_model()),
)
weapon = WeaponGoal(
    initial_state=WeaponWishState(), target_copies=1,
    model=community_weapon_soft_pity_model(),
)
bound = deterministic_combined_wishes_to_target(
    character_goal=character, weapon_goal=weapon,
)
prepared = prepare_combined_distribution(
    character_goal=character, weapon_goal=weapon, max_wishes=bound,
)
report = prepared.report(240)
thresholds = prepared.threshold_table()  # reuses both phase calculations
report_for_320 = prepared.report(320)    # also reuses the same distributions
```

For a single budget, `calculate_combined_plan(...)` is the convenient wrapper.
`minimum_combined_wishes_for_probability(...)` and
`combined_threshold_table(...)` prepare the exact curve through certainty.
Prepared reports require a covered horizon; once the entire completion support
has been prepared, larger budgets can also be reported without recomputation.

`CombinedPlanningResult` contains:

- `success_probability`: both goals completed within `total_wishes`;
- `character_success_weapon_failure_probability` and
  `character_failure_probability`: together with success, these sum to 1;
- `character_completion_time_distribution[t]`: `P(TC=t)` for `t<=N`; its
  mass is character success probability, not necessarily 1;
- `character_remaining_wishes_distribution[r]`: joint mass for character
  success with `r=N-TC` wishes left when switching to weapons;
- `conditional_character_remaining_wishes_distribution[r]`:
  `P(N-TC=r | TC<=N)`;
- `expected_remaining_wishes_after_character`:
  `sum_t (N-t)P(TC=t)` over successful character trajectories, assigning zero
  remaining wishes to character failures;
- `expected_remaining_wishes_given_character_success`: the previous mean
  divided by character success probability;
- `total_completion_time_distribution[s]`: probability both goals first
  complete on overall wish `s`, including mass at zero for already-met goals;
- `expected_total_completion_wish_given_success`:
  `E[TC+TW | TC+TW<=N]`.

If the relevant success probability is zero, its conditional expectation is
`None` and its conditional distribution is an all-zero tuple. Already-met
targets complete at time zero. Target counts use the same total-copy convention
as existing APIs, so `initial_state.copies >= target_copies` means that phase
needs no additional wishes.

Inverse planning scans the prepared combined CDF in increasing budget order.
The first qualifying integer is minimal because the CDF is non-decreasing;
plateaus do not require special assumptions about strict growth. Exactly 100%
uses the sum of the two modeled structural bounds, not a rounded near-100%
threshold. This sum is attainable as a worst-case path because the weapon
starting state does not depend on the character path.

### CLI and worked example

Run `python -m genshin_wish.cli` and choose **3. Combined Character -> Weapon
planning**, or run `python -m genshin_wish.cli --banner combined` directly for
combined prompts. Enter the total budget once, then each banner's state,
target, already-credited copies, and probability assumptions.

For command-line use, existing `--pity`, `--guaranteed`, `--target`, `--model`,
`--capturing-radiance`, and `--cr-counter` apply to the character phase. Weapon
inputs use `--weapon-pity`, `--weapon-guaranteed`, `--weapon-target`, and
`--weapon-model`; the existing `--fate-point` flag supplies weapon Fate. Optional
`--character-copies` and `--weapon-copies` specify credited copies.

```powershell
python -m genshin_wish.cli --banner combined --wishes 240 `
  --pity 37 --target 2 --model community-soft-pity `
  --capturing-radiance --cr-counter 1 `
  --weapon-pity 0 --weapon-target 1 --weapon-model community-soft-pity `
  --threshold-table
```

This example starts with no featured guarantee and CR C1 for characters, and
fresh weapon pity, no promoted guarantee, and Fate 0. Results:

```text
All goals completed:                       45.74509331%
Character completed, weapon not completed:  45.30449062%
Character not completed:                    8.95041607%

Expected wishes remaining after character (zero on failure): 82.937
Expected wishes remaining given character success:          91.090
Expected total completion wish given both goals succeed:   187.079

Confidence   Minimum total wishes
50%          248
75%          292
90%          332
95%          353
99%          403
100%         477
```

The three outcomes sum to 100%. The 477-wish structural bound is specific to
the selected mathematical curves (including the community weapon curve's
early cap), rather than a new official live-game guarantee. **Combined results
are exact up to floating-point arithmetic under the selected character and
weapon probability-model assumptions.**

Independent tiny-budget path enumeration verifies phase switching and CR
C0/C1/C2/C3 behavior. Tests also verify mass conservation, zero/already-met
targets, hard-pity/guarantee/Fate states, monotonic success, exact inverse
minimums, and one engine call per phase for reused reports and tables. Existing
character and weapon regression expectations are retained.

## Architecture

Probability assumptions and probability calculations remain separate:

- `model.py` defines `ProbabilityModel`, the official-only baseline, and the
  configurable community soft-pity assumption.
- `capturing_radiance.py` defines the replaceable CR probability schedule and
  counter transitions; `cr_engine.py` compiles its transitions for exact full
  and target-aware DP, inverse planning, and backward expectation/bound solves.
- `engine.py` contains both exact calculation modes. `calculate_target_plan()`
  absorbs first-hit mass by completion wish; `calculate()` retains the full
  continued-pulling distribution.
- `planning.py` composes engine results into finite-budget plans, minimum-wish
  searches, and reusable threshold tables.
- `combined_planning.py` composes the two target-aware completion laws into
  sequential plans and reusable combined confidence curves.
- `waiting_time.py` derives PMF, CDF, survival, conditional probability, and
  expectation for the next 5-star from a supplied model.
- `plotting.py` renders comparisons as SVG without external dependencies.
- `simulation.py` remains an independent Monte Carlo verifier.
- `results.py` defines the banner-independent target-planning result contract.
- `weapon_model.py` defines weapon state and configurable rule assumptions.
- `weapon_engine.py` contains exact target-aware and continued-pulling weapon
  calculations.
- `weapon_planning.py` provides weapon expectation and inverse planning.
- `weapon_simulation.py` is the independent weapon Monte Carlo cross-check.
- `cli.py` owns prompting, validation, report formatting, and command-line
  arguments. No engine or model module calls `input()` or prints output.

The character state immediately before a wish is
`(pity, guaranteed, copies, cr_counter)`:

- `pity`: consecutive non-5-star wishes so far (`0..89`)
- `guaranteed`: whether the next 5-star is guaranteed to be featured
- `copies`: featured copies obtained during this calculation
- `cr_counter`: assumed hidden CR counter (`0..3`, initially `1`). The first
  three positional arguments to `WishState` retain their original meaning.

For a state `s`, let `q = five_star_probability(s.pity)` and let `f` be the
featured chance when not guaranteed. With CR disabled, the transitions below
apply and leave `cr_counter` unchanged:

- no 5-star, probability `1-q`: `(pity+1, guaranteed, copies)`
- featured 5-star, probability `q` when guaranteed or `q*f` otherwise:
  `(0, false, copies+1)`
- off-banner 5-star, probability `q*(1-f)` when not guaranteed:
  `(0, true, copies)`

## Probability models

### Official-only baseline

The baseline separates the published base rate and hard-pity rule from any
soft-pity estimate:

- 0.6% at current pity `0..88`
- 100% at current pity `89`, which is the 90th wish
- 50% featured chance when not guaranteed

Holding 0.6% flat until wish 89 is only a transparent baseline for comparison.
It is **not** a claim that the game's hidden per-wish probability is flat.

### Community soft-pity assumption

The bundled default assumes:

- 0.6% through wish 73
- starting on wish 74, add 6 percentage points per wish
- force a 5-star on wish 90 independently

If `w` is the one-based wish number since the previous 5-star, its assumed
conditional probability is

```text
q(w) = 0.006                              for w < 74
q(w) = min(1, 0.006 + 0.06*(w-74+1))     for 74 <= w < 90
q(90) = 1
```

This is clearly labeled a **community modeling assumption**, not an officially
published per-wish formula. Its parameters are configurable:

```python
from genshin_wish import community_soft_pity_model

model = community_soft_pity_model(
    base_probability=0.006,
    soft_pity_start_wish=74,
    increase_per_wish=0.06,
    featured_probability=0.5,
)
```

The full 90-entry table can still be replaced with
`ProbabilityModel.from_table(...)`.

The ordinary non-guaranteed featured probability remains configurable.
Chronicled Wish rules remain out of scope; weapon rules use their separate engine.

## Capturing Radiance community counter model (v0.4.1)

This release implements the user-supplied model in
`tests/capturing_radiance.cpp`. The hidden counter, its updates, and the exact
probabilities below are **community-derived modeling assumptions**, not an
officially published per-state formula. In particular, the 10% at C2 must not
be confused with an official conditional probability. Validation here means
the Python engine implements this mathematical model; it does not establish
that the hidden live game implementation is identical.

The initial counter is C1. For a non-guaranteed 5-star, check CR before the
ordinary featured roll. The assumed CR probabilities are:

| Counter | CR trigger probability |
|---|---:|
| C0 | 0.018% (`0.00018`) |
| C1 | 0.018% (`0.00018`) |
| C2 | 10% |
| C3 | 100% |

Let `q` be the existing conditional 5-star chance, `r_c` the CR probability,
and `f` the configured ordinary featured probability (default 50%).

| Event | Probability | Next state `(pity, guaranteed, copies, counter)` |
|---|---:|---|
| No 5-star | `1-q` | `(pity+1, guaranteed, copies, c)` |
| Guaranteed featured 5-star | `q` when guaranteed | `(0, false, copies+1, c)` |
| CR triggers | `q*r_c` when not guaranteed | `(0, false, copies+1, 1)` |
| CR misses, normal win | `q*(1-r_c)*f` when not guaranteed | `(0, false, copies+1, max(0,c-1))` |
| CR misses, actual loss | `q*(1-r_c)*(1-f)` when not guaranteed | `(0, true, copies, min(3,c+1))` |

The counter is part of the Markov state. A guaranteed featured pull and a
missed 5-star leave it unchanged. At C3 there is no normal roll: CR always
triggers. At C2 both CR and an ordinary win end at C1; the DP adds their mass.
The effective featured probability at C2 is therefore `0.10 + 0.90*0.5 = 55%`,
and at C0/C1 it is `0.50009`, rather than a flat 55% at every 5-star.

Enable CR independently of the soft-pity schedule:

```python
from dataclasses import replace
from genshin_wish import (
    CapturingRadianceModel, WishState, calculate_plan,
    community_soft_pity_model, with_capturing_radiance,
)

model = with_capturing_radiance(community_soft_pity_model())
plan = calculate_plan(
    initial_state=WishState(pity=37, cr_counter=1),
    wishes=240, target_copies=2, model=model,
)
# Replace the schedule or counter destinations with a different assumption:
custom = with_capturing_radiance(model, CapturingRadianceModel(
    probabilities=(0.00018, 0.00018, 0.20, 1.0),
))
disabled = replace(model, capturing_radiance=None)
```

`ProbabilityModel.from_table(..., capturing_radiance=rules)` also accepts CR
while retaining a custom 90-entry pity schedule. Disabling CR preserves the
stored counter without updating it. The API function names, target stopping
policy, result fields, and weapon functionality retain their meanings.

For interactive character planning, choose `cr` (community soft pity plus CR)
or `official-cr` (flat baseline pity plus community CR); then enter an assumed
counter or press Enter for C1. The existing `1` and `2` choices disable CR.
Direct usage:

```powershell
python -m genshin_wish.cli --pity 37 --wishes 240 --target 2 `
  --model community-soft-pity --capturing-radiance --cr-counter 1 --threshold-table
```

The report labels CR separately from the pity model. The CR flags apply only
to character wishes. The first-5-star waiting-time distribution is unchanged
because CR changes the identity of a 5-star, not its arrival probability.

Inverse planning still returns the first qualifying integer wish count. Exactly
100% uses a backward maximum over positive-probability branches including the
counter. For example, C3 at pity 89 reaches a one-copy target in exactly one
wish. Fresh C1 needs at most 450 wishes for three copies under the flat baseline,
compared with 540 without CR: a third consecutive actual loss is precluded by C3.

For the historical character example (pity 37, not guaranteed, budget 240,
target 2, community soft pity), CR starts at C1. The historical regression is
retained for the disabled configuration. The new configuration is compared
explicitly rather than substituting its result into the old regression.

| Statistic | CR disabled | CR enabled, C1 |
|---|---:|---:|
| P(target reached) | 90.05330285% | 91.04958393% |
| Minimum wishes for 90% | 240 | 234 |
| Minimum wishes for 95% | 269 | 267 |
| Minimum wishes for 99% | 278 | 278 |

Success increases because CR converts some would-be losses into featured
results. In particular, after a C1 loss and the subsequent guaranteed featured
pull, the next non-guaranteed attempt is at C2 with 55% effective featured
probability. Expectations and other comparisons are recorded in the changelog
and benchmark report. No existing test expectations were replaced.

## Weapon Event Wish (v0.4)

### Modeled rules and sources

The weapon implementation models the normal two-promoted-weapon Weapon Event
Wish under the **post-Version 5.0 rules**, reviewed on **2026-09-27**. Relevant
official sources are HoYoverse's [Capturing Radiance Q&A](https://www.hoyolab.com/article/32168979),
which says Epitomized Path changed to one Fate Point after Version 5.0; a
[current Version 7.1 Weapon Event Wish notice](https://genshin.hoyoverse.com/m/ja/news/detail/166228),
confirming the two-promoted-weapon/Epitomized Path structure; and the official
[Epitomized Path introduction](https://www.hoyolab.com/article/533181), used for
course-change and banner-end reset behavior. The older article's original
two-Fate-Point requirement is obsolete and is **not** used.

The modeled banner details are:

- base 5-star weapon probability: 0.7%;
- a 5-star by the 80th weapon wish;
- when not promoted-guaranteed, 75% of 5-stars are promoted;
- the two promoted weapons are selected equally, giving the desired weapon a
  37.5% share before guarantees;
- a non-promoted 5-star makes the next 5-star promoted;
- with a course charted, any non-desired 5-star supplies the one Fate Point,
  so the next 5-star is the charted desired weapon;
- obtaining the desired weapon clears the Fate Point and promoted guarantee;
- weapon pity and the promoted guarantee carry to later Weapon Event Wishes;
  Fate Points and the charted course do not carry to a later banner period.

The calculator assumes a course is charted for one of the two promoted 5-star
weapons. It does not model wishing without a charted course, single-promoted
special banners, changing course during a plan, or future rule revisions.
Starting state must describe the current banner period; after rollover, enter
Fate Point 0. Some official event pages direct players to the in-game Wish
Details screen instead of reproducing every rate in web text, so these values
should be rechecked if HoYoverse changes that screen or Epitomized Path.

### Weapon state and exact transitions

Weapon planning needs more state than character planning because two different
guarantees can coexist. Its pre-wish state is:

```text
(pity, promoted_guaranteed, fate_point, copies)
```

- `pity`: `0..79` non-5-star wishes since the last weapon 5-star;
- `promoted_guaranteed`: whether a prior non-promoted result guarantees a
  promoted weapon next;
- `fate_point`: `0` or `1` for the currently charted course;
- `copies`: selected target weapons obtained during this calculation.

This state is Markov: once these values and the configured model are known,
the earlier pull history adds no information about the next outcome.

Let `q` be the configured next-wish 5-star probability, `r=0.75` the promoted
share, and `s=0.5` the desired share among promoted weapons:

| Current rule state | Desired | Other promoted | Non-promoted | No 5-star |
|---|---:|---:|---:|---:|
| Fate Point = 1 | `q` | 0 | 0 | `1-q` |
| Promoted guaranteed, no Fate | `q*s` | `q*(1-s)` | 0 | `1-q` |
| Neither guarantee | `q*r*s` | `q*r*(1-s)` | `q*(1-r)` | `1-q` |

Every 5-star resets pity. Desired increments copies and clears both guarantees;
other promoted sets Fate and clears promoted guarantee; non-promoted sets both
Fate and promoted guarantee. Fate takes precedence when both are set. Tests
verify each row sums to 1 and exercise every rule-state update directly.

### Weapon probability models

`official_only_weapon_model()` uses 0.7% through pity 78 and forces the 80th
wish. Its flat portion is a transparent baseline, not an assertion about the
game's hidden conditional rates.

`community_weapon_soft_pity_model()` is explicitly a **modeling assumption**:
0.7% through wish 62, then +7 percentage points per wish from wish 63, capped
at 100%, with wish 80 independently forced. HoYoverse does not publish this
exact curve. The defaults reach their cap before wish 80; that is a property
of the approximation, not a new official hard-pity claim. Parameters or the
entire 80-entry table can be replaced without changing the DP.

### Planning, analysis, and CLI

Normal weapon planning absorbs a branch once the target is reached. It exposes
`P(T_weapon=t)`, `P(T_weapon<=N)`, and the distribution of
`R=N-T_weapon` on successful trajectories. Full-distribution mode instead
spends exactly all `N` wishes and may produce copies above the target. The two
modes have the same success probability but different final distributions.

Run `genshin-wish` with no arguments to choose Character or Weapon Event Wish.
Direct weapon usage is also available:

```powershell
genshin-wish --banner weapon --pity 0 --wishes 120 --target 1 `
  --model community-soft-pity --threshold-table
```

Use `--guaranteed` for a carried promoted-weapon guarantee and
`--fate-point 1` for the current charted course. Add
`--mode full-distribution` only to model spending every wish.

A fresh-state target-1 plan with 120 wishes under the bundled community
assumption gives:

```text
P(target reached): 70.66535051%
E[T]: 86.532 wishes
E[T | T <= 120]: 67.721 wishes
Expected wishes remaining given success: 52.279
Inverse thresholds: 50%=79, 75%=128, 90%=133, 95%=135, 99%=138 wishes
```

For `(pity=50, promoted guarantee=true, Fate=1)`, target 2, budget 100,
the same model gives `P(success)=53.65910239%` and `E[T]=102.074` wishes.
Fate guarantees the first charted weapon and takes precedence over the stored
promoted guarantee.

**Every weapon result depends on the selected probability assumptions.**

## Probability terms in plain language

- **PMF** answers “what is the probability that the first 5-star arrives on
  exactly wish `n`?”
- **CDF** answers “what is the probability that it has arrived by wish `n`?”
- **Survival probability** answers “what is the probability that it still has
  not arrived after wish `n`?”
- **Conditional per-wish probability** `q_n` is the chance that wish `n` is a
  5-star given that all earlier wishes since the last 5-star failed.
- **Exact dynamic programming** keeps a table of every reachable
  `(pity, guaranteed, copies)` state and its probability. Each wish distributes
  that probability among every valid next state. Unlike Monte Carlo, it does
  not estimate the answer from random samples.

### First-5-star waiting time

Let `X` be the number of additional wishes until the next 5-star. For arbitrary
starting pity `p`, the support is `1..(90-p)`. At each elapsed wish `n`:

- `q_n` is the configured conditional 5-star probability
- `P(X=n) = P(X>n-1) q_n` (PMF)
- `P(X>n) = P(X>n-1)(1-q_n)` (survival)
- `P(X<=n) = 1-P(X>n)` (CDF)

Hard pity gives final survival `0`, final CDF `1`, and PMF mass `1` within
floating-point roundoff. The expected wait is
`E[X] = sum(n * P(X=n))`.

Tests verify for both bundled models that:

- PMF mass sums to 1 within `1e-12`
- CDF is nondecreasing and equals 1 at hard pity
- survival equals 0 at hard pity
- `P(X=n)=P(X>n-1)q_n` at every wish
- PMF expectation agrees within `1e-12` with the engine's backward recurrence

## Full-distribution model comparison retained from v0.2

This table asks what happens after spending all 240 wishes, even after two
copies have been obtained:

| Model | P(at least 2) | Expected copies |
|---|---:|---:|
| Official-only flat baseline | 84.137188% | 2.202632 |
| Community soft-pity assumption | 90.053303% | 2.444163 |
| Change | **+5.916114 percentage points** | **+0.241530** |

The community assumption also changes the unconditional expected wishes to 2
copies from `184.915241` to `160.861601`. These differences describe the two
configured mathematical models; they do not validate the assumed curve as the
game's actual implementation.

**Every result depends on the selected probability assumptions.** Switching
models changes the answers even though the exact DP algorithm is identical.

## Interactive planning and inverse planning

Run `genshin-wish` or `python -m genshin_wish.cli` with no arguments. The
planner validates each response, prints a budget report, and then accepts a
custom inverse confidence. Press Enter at that prompt to display the standard
50%/75%/90%/95%/99% table.

Inverse planning propagates the exact probability states once, in increasing
wish order. It returns the first wish count whose success probability meets the
requested threshold. Since the probability is non-decreasing, the first match
is the minimum valid count even when several wishes produce the same
probability. Exactly 100% uses the finite hard-pity and featured-guarantee path,
not a rounded value such as 99.999%.

For pity 37, not guaranteed, and a target of 2 under the community assumption:

| Probability target | Minimum wishes |
|---:|---:|
| 90% | 240 |
| 95% | 269 |
| 99% | 278 |
| 100% | 323 |

### Completion time and remaining wishes

For a target-aware result, `completion_time_distribution[t]` is the exact
first-hitting probability `P(T=t)`. Its sum is the success probability.
`remaining_wishes_distribution[r]` is the unconditional joint probability
`P(R=r and success)`, where `R=N-T`. The conditional version
`P(R=r | success)` is also exposed. Thus every successful branch satisfies
`completion wish + remaining wishes = original budget` and can later feed its
remaining budget into another goal without pretending that unused wishes were
spent.

### Example interactive session

```text
=== Genshin Wish Probability Calculator ===

Current pity: 37
Guaranteed featured 5-star? [y/n]: n
Available wishes: 240
Target copies: 2

Probability model:
1. Official-only baseline
2. Community soft-pity assumption (not an official per-wish formula)
> 2

=== Planning Report ===
Model: community soft-pity assumption (...)
P(target reached): 90.05330285%
Expected featured copies when stopping at target: 1.900533
Unconditional expected wishes to target, E[T]: 160.862
Conditional expected completion wish, E[T | T <= budget]: 149.365
Expected wishes actually consumed: 158.380
Expected wishes remaining given success: 90.635

Target-aware copy distribution (stop immediately at target):
  Exactly 0 before budget exhaustion: 0.00000000%
  Exactly 1 before budget exhaustion: 9.94669715%
  Target reached (2 copies; stopped): 90.05330285%

Inverse-planning confidence [0-100%, Enter for 50/75/90/95/99% table]: 95
Minimum wishes for at least 95.00% success: 269
```

`E[T]` is the average completion time without imposing a budget.
`E[T | T <= budget]` averages only runs that complete within the supplied
budget. They answer different questions and are reported separately.

### Advanced full-distribution output

The advanced continued-pulling report displays exact-copy outcomes of at least 0.5%
individually. It always displays the requested target count even when that
outcome is below 0.5%. All other outcomes are combined into a clearly labeled
row; they may be non-contiguous copy counts, so the report does not call them a
tail. This is presentation only: `CalculationResult.copy_distribution` still
contains the complete exact distribution, and success/expectation calculations
use every outcome.

Use it explicitly with `--mode full-distribution`.

Performance measurements and profiling notes are recorded in
[BENCHMARKS.md](BENCHMARKS.md).

## Plots

The shaded region begins at the assumed soft-pity start, wish 74. The dashed
line marks hard pity.

- [First-5-star PMF](plots/first_five_star_pmf.svg)
- [First-5-star CDF](plots/first_five_star_cdf.svg)

Regenerate them with:

```powershell
python -m genshin_wish.plotting --output-dir plots
```

## Run it

From the repository root:

```powershell
python -m pip install -e .
python -m genshin_wish.cli
python -m genshin_wish.cli --pity 37 --wishes 240 --target 2 --model official-only
python -m genshin_wish.cli --pity 37 --wishes 240 --target 2 --model community-soft-pity --confidence 95 --threshold-table
python -m genshin_wish.cli --pity 37 --wishes 240 --target 2 --model community-soft-pity --mode full-distribution
python -m unittest discover -s tests -v
```

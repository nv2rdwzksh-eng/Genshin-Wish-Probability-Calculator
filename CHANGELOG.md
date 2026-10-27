# Changelog

## v1.0.3 — 2026-10-27

### Consistent number formatting

- Centralized quantity formatting: grouped integers for wishes/copies and one
  decimal place for averages, independent of probability precision.
- Applied the shared formatters to result summaries, all banner outcome labels,
  history, thresholds, slider accessible text, budget differences, and readable
  exports. Raw JSON exports preserve unrounded values.
- Retained configurable probability precision and near-zero/near-one guards.
  Confidence preset labels remain whole percentages.
- Clarified the precision setting as probability decimal places.

### First paint and focus

- Added an early startup script before CSS/body rendering. Shared settings
  validation resolves saved/system theme, font size, and animation settings
  before the first frame. Shared translations localize parsed text and accessible
  labels before paint, without waiting for the deferred calculator script.
- Startup never hides the page; static English content survives disabled or
  failed JavaScript, and CSS follows system-light without a startup script.
- Removed input/select outline suppression and faint competing focus glows.
  All keyboard controls use a visible 3 px opaque accent ring. The transparent
  range uses one visible wrapper ring; forced colors use the system highlight.
- Replaced the previous-result notice's accent stripe with a subtle full border.
- Updated backend, package, and CLI release metadata to 1.0.3. The backend still
  provides the only displayed UI version value.

### Verification

- Added browser coverage for formatting at precisions 0/2/10 in both languages,
  readable/lossless exports, cold loads with the main script held, reloads,
  failed/disabled JavaScript, malformed/blocked storage, and focus styles and
  contrast in both themes.
- Complete suite: 127 Python tests pass. Browser suites: 88 existing smoke + 52
  existing reliability + 192 new consistency checks pass (332 total), with no
  unexpected JavaScript errors. JavaScript syntax and Git whitespace checks pass.
- Existing character, weapon, combined, and web probability regressions remain
  unchanged; no probability-engine files or expected probabilities changed.

## v1.0.2 — 2026-10-26

### Result visibility

- Successful calculations and restored history records now reveal the result
  card when it is offscreen. Measurements wait for FLIP/staggered animations
  and two layout frames so the scroll target uses the settled layout.
- Comfortable, already-visible results preserve scroll and focus. When a reveal
  is needed, focus moves to the result heading only if it is still with the
  initiating action/body. A settings dialog is never focused through.
- The helper supports desktop columns, mobile stacking, short viewports, reduced
  motion, and animation-off settings. Superseded reveals are invalidated.
- Disabled workspace scroll anchoring to avoid CTA/column height changes
  competing with the controlled result reveal.

### Loading, failures, and cancellation

- Added a visible result loading panel, loading placeholders, and cancel controls
  beside the CTA and in the result column. Previous numbers and associated
  outcomes/thresholds are hidden during the new request.
- Added prominent accessible result alerts for HTTP, validation, network, and
  invalid-response failures, plus explicit cancellation/timeout feedback and a
  retry action. The last successful result is retained with a previous-result
  label; it is not presented as a successful result of the failed attempt.
- Browser requests now have a 30-second timeout. Cancellation and timeout abort
  the request and immediately release the CTA, without requiring a reload.
- Request identity guards and cleared timers prevent late cancelled/timed-out
  responses from overwriting newer results, saving history, or ending a newer
  loading state. Only successful attempts enter history.
- Retrying uses the current form. Browser cancellation does not claim to stop
  work already running in a synchronous backend thread.
- Added English and Chinese request-state labels and feedback.

### Single-source UI version

- FastAPI `VERSION` now supplies the top bar, footer, About panel, and text-export
  header. Removed release literals from HTML, translations, and export logic.
- Version fetch failures show a localized unavailable value. A fresh backend
  calculation response can supply the version; restored history cannot change
  it. Compatible schema-1 history no longer requires a release allowlist.
- Updated API, package, and CLI release metadata to 1.0.2.

### Verification

- Added a dedicated real-browser regression script for viewport/focus behavior,
  cancel/timeout/retry races, loading and retained-result labels, error recovery,
  and dynamic API version propagation in UI/localization/export.
- Added an API test patching backend `VERSION` to an unrelated value and checking
  that HTML contains no release literal.
- Verification: **127 Python tests**, the **88-check browser smoke suite**, and
  **52 focused browser reliability checks** passed. Browser runs reported zero
  JavaScript errors; desktop feedback and mobile result screenshots were reviewed.
- Probability engines, model assumptions, and numerical regressions are unchanged.

## v1.0.1 — 2026-10-26

### Settings appearance

- Replaced the scrolling settings list with a Windows-style, two-column
  frosted-glass window. Its left sidebar contains Calculator Settings,
  Appearance, Language Preferences, and Help Center, with Wish Lab branding
  anchored at the lower-left.
- Every opening resets to Calculator Settings. Categories support keyboard
  navigation and expose tab/tabpanel semantics; Escape still closes the dialog.
- Centered the close SVG on both axes and aligned standard number inputs and
  selects to the same 44 px height.
- Replaced named font presets with a dropdown for every integer size from
  10 through 20 px; the default is now 14 px, with readable labels and hints.
  Existing saved named preferences migrate to their previous pixel sizes.
- Help Center now places About Calculator and version 1.0.1 on the same row,
  followed by Terms & Policies, then the author contact hyperlink.

### Main interface

- The initial view contains only a centered 660 px wish-plan card and history
  when enabled. No result placeholder is shown.
- On the first successful calculation or explicit history selection, the
  desktop plan card smoothly moves/narrows to the left while the three result
  cards enter on the right. Mobile retains a single-column flow.
- Saved history still loads on opening, but no longer automatically expands
  the latest result. History from v1.0.0 remains selectable.
- Added a sliding mode highlight; mode instructions now sit inside the lower
  part of the selection box.
- Added a smoothly animated confidence rail, fill, and thumb while retaining
  exact confidence presets and keyboard behavior.
- Extended the subtle gradient texture and accent edge to every result panel
  and the standard input/select surfaces.
- All new animation respects both the settings toggle and system reduced
  motion. No probability calculations or model assumptions changed.

### Version and verification

- Updated web/API/package/CLI version labels to 1.0.1.
- Extended the real-browser smoke check for the new layout, category keyboard
  navigation, defaults, control geometry, font migration, compatible history,
  reduced motion, and desktop/mobile layouts.
- Verification: **126 Python tests passed**, and **88 Chromium checks passed**
  with zero JavaScript page errors. Desktop and large-font Chinese mobile
  screenshots were visually reviewed.
- Existing numerical regression expectations are preserved.

## v1.0 — 2026-10-25

### Web planner

- Expanded the author's four-file FastAPI/HTML/JavaScript/CSS foundation into a
  responsive character, weapon, and combined planner. A prominent mode switch
  controls the active banner fields. Combined mode follows character first,
  then weapon with the remaining budget.
- Community soft-pity schedules and character Capturing Radiance are enabled
  by default. The web UI has no model switches; existing Python and CLI model
  configuration remains available. Initial character CR counter is C1 and may
  be adjusted in the expandable state control.
- Added success probability, the stop-at-target outcome list, exact competition
  ranks, and a guaranteed listing of the user's requested outcome in addition
  to the top N most likely outcomes.
- Added a 0–100% confidence axis with 50/75/90/95/99% snap points, preset buttons,
  keyboard controls, and exact minimum-wish thresholds. The 100% endpoint uses
  the modeled structural guarantee rather than a near-certainty approximation.
- Reports distinguish unconditional expected completion wishes from conditional
  completion wishes within the budget, and include the combined three-way
  success/character-only/character-failure breakdown.

### Settings, history, and appearance

- Added a bottom-left Settings control with a keyboard-accessible dialog.
- Calculator settings: history on/off (default on), unrounded calculation-data
  export as UTF-8 .txt, 0–10 display decimal places (default 2), and top 1–10
  outcomes (default 3) plus the user's target.
- The latest five records load on opening the page. Selecting history restores
  inputs and the saved result; Clear removes records. Turning history off
  deletes saved history and prevents further persistence. Settings and history
  stay in localStorage; unavailable storage falls back to session state.
- Added system-theme following by default, the original blue/violet dark-tech
  palette with clearer form outlines, a white/silver light gradient, font sizes,
  and an animation toggle respecting system reduced-motion preferences.
- Added English (default) and Simplified Chinese translations, plus About,
  current version, the author's GitHub issue link, and Terms and Policies.
- Added loading, validation, stale-result, and network-error states; preserved
  the last valid result after request failure. Large-font/mobile and high
  precision layouts are supported.

### Backend and compatibility

- The same FastAPI server serves the page, assets, version endpoint, and
  /api/calculate; the frontend no longer hard-codes a separate API origin.
- The API uses the existing public target-aware and combined-planning APIs.
  Exact combined count probabilities come from character hitting-time mass
  weighted against weapon CDF tails, followed by adjacent-tail differences.
  No giant joint-state DP or Monte Carlo calculator was introduced.
- Web input bounds are 0–2,000 wishes, 0–10 target copies, character pity 0–89,
  weapon pity 0–79, CR C0–C3, and Fate 0/1. These interactive limits do not
  change the underlying engines.
- Added optional web and web-test dependencies and setup/testing instructions.
  Package version is 1.0.0; the CLI version banner is updated.
- Existing engine mathematics and probability assumptions are unchanged:
  character pity37/240 wishes/target2 gives 90.053302850222% with CR disabled
  and 91.049583930138% with CR enabled; the combined CR-enabled example remains
  45.745093306891%; fresh weapon target1/120 wishes remains 70.665350512362%.
  No previous regression expectation was replaced.

### Verification

- Complete suite: **126 tests passed** (all 117 previous tests plus 9 API tests).
- Real Chromium: **61 checks passed**, zero JavaScript page errors. Desktop
  dark/light and Chinese large-font mobile screenshots were visually inspected.
- Added API tests for all modes, strict validation, ranked outcome mass,
  zero/completed goals, guarantees, and tiny sequential-reference agreement.
- Added a reproducible Chromium smoke test covering mode changes, exact
  thresholds, history reload/cap/off, export, language/appearance persistence,
  mobile layout, keyboard controls, error recovery, and unavailable storage.
- Full test and timing results are recorded in BENCHMARKS.md.

## v0.5 — 2026-10-01

### Added

- Exact sequential character-target -> weapon-target composition, calling each
  existing target-aware engine once per prepared distribution.
- `CharacterGoal` and `WeaponGoal` adapters; `CombinedCompletionDistribution`
  with reusable phase results, cached weapon CDF, and combined completion
  PMF/CDF; `CombinedPlanningResult` for finite-budget reports.
- Character completion and remaining-budget distributions, conditional and
  zero-on-failure unconditional remaining-wishes expectations, combined first
  completion time, and conditional total completion expectation.
- Three disjoint report outcomes: both completed, character completed but
  weapon failed, and character failed.
- Exact combined inverse planning and confidence tables, including a structural
  100% bound equal to the sum of the phase bounds.
- Interactive banner choice 3, `--banner combined`, separate weapon initial
  state/model arguments, and optional already-credited copy counts.
- Independent brute-force tiny-path tests, public-API call-count verification,
  all CR and weapon guarantee/Fate edge states, mass/monotonicity/minimum-budget
  checks, and realistic benchmark cases.

### Mathematics and assumptions

Condition on character completion time `t`: the unchanged weapon starting
state then receives `N-t` wishes. The finite-budget probability is
`sum_t P(TC=t) * FW(N-t)`. The full total-completion PMF is the convolution of
the two first-hitting PMFs. No joint character/weapon state DP is used in
production, and the weapon phase is never re-solved for every remaining budget.
All outputs remain exact up to floating-point arithmetic under the selected
character/weapon model assumptions, including configurable community CR.

### Compatibility and validation

- Complete suite: **117 tests passed in 34.714 s**, comprising all **89 existing
  tests** and **28 new combined-planning/CLI tests**.
- Character, CR, and weapon engine/model/planning implementations are unchanged.
- Existing character/weapon APIs and all prior test expectations are preserved.
- The retained character regression remains `90.053302850222%` with CR disabled
  and `91.049583930138%` with CR enabled at C1.
- Combined mode is character first, weapon second; arbitrary longer sequences
  and reverse ordering are outside this release.

### Worked example

Budget 240; character pity 37, not guaranteed, C1, target 2; fresh weapon state,
target 1; both community soft-pity assumptions and community CR enabled:

| Outcome | Probability |
|---|---:|
| Both completed | 45.74509331% |
| Character completed, weapon failed | 45.30449062% |
| Character failed | 8.95041607% |

Expected remaining budget after characters is 82.937 wishes assigning zero to
character failures, or 91.090 wishes conditional on character success. Expected
total completion is 187.079 wishes conditional on both goals succeeding.

Minimum budgets for 50/75/90/95/99/100% are **248/292/332/353/403/477**.
These are new combined-plan outputs; no standalone regression was changed.
Reproducible runtimes and phase-state counts are recorded in `BENCHMARKS.md`.

## v0.4.1 — 2026-10-01

### Added

- Configurable Capturing Radiance community counter model for characters:
  initial C1, trigger probabilities `(0.00018, 0.00018, 0.10, 1.0)`,
  CR reset to C1, ordinary wins decrementing with floor C0, actual losses
  incrementing with cap C3. Guaranteed featured pulls preserve the counter.
- `WishState.cr_counter`, appended after the original three fields.
- `CapturingRadianceModel`, `ProbabilityModel.capturing_radiance`, and
  `with_capturing_radiance()` for enabling or replacing the assumptions.
- Counter-aware exact full DP, target-aware DP, inverse planning, unconditional
  expectation, structural 100% bounds, and independent Monte Carlo updates.
- Interactive `cr` / `official-cr` selections, command-line
  `--capturing-radiance` / `--cr-counter`, and explicit assumption labels.
- Twenty new exact/rule/integration tests; reproducible paired benchmarks in
  `benchmarks/benchmark_v041.py`.

### Compatibility

- CR stays disabled in existing model constructors. Existing character calls
  and regression expectations remain valid for those models. Explicitly
  enabling CR selects the new model; it does not silently change old outputs.
- Existing first-5-star schedules, waiting-time analysis, target stopping,
  result fields, and planning function signatures are preserved.
- Weapon source modules and existing weapon tests are unchanged.
- No combined character/weapon planning was added.

### Model status

The hidden counter, counter updates, and per-counter trigger schedule are
community-derived assumptions. The 10% C2 value is not an officially published
conditional formula. Mathematical validation here uses the user-supplied C++
reference and an independent small-state Python translation.

### Explained output changes

For pity 37, not guaranteed, budget 240, target 2, community soft pity,
and initial CR counter C1:

| Statistic | CR disabled | CR enabled | Change |
|---|---:|---:|---:|
| P(success) | 90.053302850222% | 91.049583930138% | +0.996281079916 percentage points |
| Expected copies after all 240 wishes | 2.444162750708 | 2.482464844165 | +0.038302093457 |
| Unconditional E[T] | 160.861600774223 | 159.296037166793 | -1.565563607430 wishes |
| Conditional E[T \| T<=240] | 149.364739948000 | 148.910026136598 | -0.454713811402 wishes |
| Minimum wishes for 90% | 240 | 234 | -6 |
| Minimum wishes for 95% | 269 | 267 | -2 |
| Minimum wishes for 99% | 278 | 278 | 0 |
| Minimum wishes for 100% | 323 | 323 | 0 |

CR converts some losses into featured outcomes, increasing success and expected
continued-pulling copies while reducing completion time. After an actual C1
loss, the guaranteed pull preserves C2; the next non-guaranteed pull then has
55% effective featured probability. The two-copy worst-case path remains two
actual losses, so its 100% bound remains 323. Higher targets can have shorter
bounds because C3 precludes another loss before resetting to C1.

The old regression test is retained and a separate enabled-model regression
is added. No old hard-coded expectation was silently updated.

### Verification

- Complete suite: **89 tests passed**, including all **69 pre-existing tests**.
- The supplied C++ reference compiled unchanged and returned `85.72125058%`
  for fresh state, 240 wishes, target 2. Python returned `85.7212505838%`.
- Full DP success and target-aware success agree for the main comparison.
- Paired timings, state counts, and measured costs are in `BENCHMARKS.md`.

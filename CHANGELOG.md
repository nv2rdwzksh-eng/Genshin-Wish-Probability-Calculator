# Changelog

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

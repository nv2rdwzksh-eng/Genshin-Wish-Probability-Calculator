# Benchmark reports

## v0.5 combined character -> weapon planning

Measured 2026-10-01 on the development Windows host with Python 3.12. Run
`python -u benchmarks/benchmark_v05.py --repeats 3` for paired, reproducible
median wall-clock timings. Every case uses the existing community soft-pity
curves and the configured community CR model. Times include both target-aware
banner calculations and composition. No timing thresholds are asserted in tests.

| Case | Median runtime | Combined success |
|---|---:|---:|
| A: fresh, character target 1 -> weapon target 1, budget 240 | 0.028965 s | 86.04794268% |
| B: character pity 37/C1, target 2 -> fresh weapon target 1, budget 320 | 0.097769 s | 84.57611383% |
| C: guaranteed character pity 60/C2, target 2 -> weapon pity 50/promoted guarantee/Fate 1, target 1, budget 240 | 0.021124 s | 100% |
| D: fresh, character target 7 -> weapon target 5, budget 1,200 | 3.038761 s | 84.47847027% |

For case B, preparing the entire completion curve through the structural bound
of 477 wishes took 0.101099 s. Peak unfinished phase states were 515 character
and 154 weapon states. Looking up all six confidence targets from the prepared
curve then took 0.000142 s; budgets were 248/292/332/353/403/477 for
50/75/90/95/99/100%. Additional reports also reuse those phase calculations.

Each phase runs once up to the smaller of the requested horizon and that
phase's own finite guarantee. The weapon CDF is cached once and evaluated at
each `N-t`. A finite PMF convolution also supplies total first-completion times
and the combined CDF used by inverse planning. It skips zero bins without
pruning any positive probability. With support sizes HC and HW, composition
costs O(HC*HW) time and O(HC+HW) extra storage. There is no joint pity/guarantee/
counter state space and no repeated weapon DP per character-completion time.

Already-completed phases have all mass at t=0, so they reduce naturally to the
other standalone target-aware calculation. Exactly 100% uses the sum of phase
structural bounds, including the selected soft-pity curve and CR assumptions.

The full worked example at budget 240 is documented in README/CHANGELOG. Its
three outcomes are 45.74509331% both, 45.30449062% character only, and
8.95041607% character failure; these sum to 100% within floating-point error.

## v0.4.1 Capturing Radiance

Measured 2026-10-01 on the development Windows host with Python 3.12. Use
`python -u benchmarks/benchmark_v041.py --repeats 3` to reproduce. Values are
median wall times for three runs; timing is observational rather than asserted
by tests. Both configurations use the identical community character soft-pity
table and start at C1. Peak states count only unfinished target-aware states.

| Case | CR disabled | CR enabled | Peak states disabled/enabled |
|---|---:|---:|---:|
| A: fresh, budget 320, target 3 | 0.085706 s | 0.291108 s | 448 / 1,252 |
| B: pity 37, budget 240, target 2 | 0.026427 s | 0.074215 s | 232 / 515 |
| C: fresh, budget 800, target 7 | 0.607345 s | 2.272042 s | 1,164 / 3,760 |
| Full continued-pulling B | 2.918991 s | 13.070465 s | unrestricted copy distribution |
| B inverse 50/75/90/95/99/100% | 0.027398 s | 0.076140 s | single forward trajectory |

Success values also differ because CR changes the model:

| Case | CR disabled | CR enabled |
|---|---:|---:|
| A | 71.898405316649% | 76.779964601671% |
| B | 90.053302850222% | 91.049583930138% |
| C | 89.905231132186% | 95.577555461853% |

The CR counter introduces four local state layers. Local transition branches
are compiled once for all 720 pity/guarantee/counter combinations. The absorbing
planner uses sparse integer keys; completed branches are removed. Full analysis
uses a dense flat buffer and retains every copy count. During development,
switching CR full analysis from dictionary propagation to a flat buffer reduced
the representative B time from approximately 21 s to 13 s. No probability
pruning, counter merging, or Monte Carlo approximation is used.

Backward expectation and worst-case recurrences retain only two 720-entry
copy layers and take O(target copies * 720) work. The structural worst-case
calculation uses positive-probability branches, never a numerical near-100%
threshold. The disabled default still uses the previous optimized 180-state
engine. CR-enabled full analysis has a substantial cost; target-aware planning
continues to be the normal CLI path.

The six inverse outputs for case B are:

| Confidence | CR disabled | CR enabled |
|---|---:|---:|
| 50% | 162 | 160 |
| 75% | 197 | 196 |
| 90% | 240 | 234 |
| 95% | 269 | 267 |
| 99% | 278 | 278 |
| 100% | 323 | 323 |

The complete post-integration test suite passed 89 tests in 34.618 s. All
pre-existing weapon tests are retained unchanged.

## v0.4 weapon planner

Environment: Python 3.12 on the development Windows host. Measurements use
`tracemalloc` and `time.perf_counter`; reproduce them with
`python benchmarks/benchmark_v04.py`. All cases use the bundled community
weapon soft-pity assumption.

| Case | Runtime | Peak active states | Peak traced memory | Result |
|---|---:|---:|---:|---:|
| A: fresh, target 1, budget 120 | 0.050755 s | 154 | 30.6 KiB | 70.66535051% |
| B: pity 50, promoted guarantee + Fate, target 1, budget 80 | 0.001269 s | 1 | 9.9 KiB | 100% |
| C: fresh, target 5, budget 700 | 5.655119 s | 1,070 | 199.9 KiB | 99.99999998% |
| D: target-1 inverse 50/75/90/95/99% | 0.042848 s | — | 18.6 KiB | 79/128/133/135/138 wishes |

The target-aware engine caps copies at the target and removes completed mass,
so ordinary planning never pays for an unlimited-copy distribution. Internal
states use compact integer keys. The five inverse thresholds share one forward
trajectory rather than running five separate searches. Correctness and public
state objects remain explicit.

## v0.3.1 internal-state optimization

Measured on the development machine under Windows with Python 3.12. The full
report before/after values below were run as paired single-process wall-clock
measurements. Inverse values are representative runs from the same environment.
They are observations, not unit-test performance requirements.

| Operation | v0.3 before | v0.3.1 after | Speedup |
|---|---:|---:|---:|
| A: pity 0, target 3, 320-wish full report | 7.996 s | 4.714 s | 1.70x |
| B: 50/75/90/95/99% inverse table | 0.131 s | 0.099 s | 1.32x |
| B: single 99% inverse query | 0.129 s | 0.098 s | 1.32x |
| C: pity 37, target 2, 240-wish full report | 4.808 s | 2.775 s | 1.73x |

Profiling showed that the original full-distribution transition loop consumed
about 99.98% of scenario A's runtime. Final `WishState` construction and
expected-wish calculations were negligible. The inverse planner was already
using one forward trajectory and absorbing success state: five thresholds took
essentially the same time as one 99% query, so no redundant threshold searches
were present.

The largest improvement came from representing the full-distribution state as
a dynamically sized flat probability buffer indexed by encoded
`(copies, guaranteed, pity)`, rather than a dictionary keyed by temporary
tuples. The smaller inverse state remains a sparse dictionary, now with compact
integer keys.

Traced peak Python allocation for scenario A decreased from approximately
8.549 MiB for the reconstructed v0.3 tuple-key loop to 4.107 MiB for v0.3.1.
The optimization therefore did not increase measured memory use.

Reference-DP tests and the full regression suite found no numerical changes
beyond floating-point tolerance. Run the maintained benchmark cases with:

```powershell
$env:PYTHONPATH = "src"
python benchmarks/benchmark_v031.py --repeats 3
```

## v0.3.2 target-aware planning

v0.3.2 compares the v0.3.1 full-distribution calculation with the new exact
stop-at-target planner. Timings are measured on the same Windows/Python 3.12
development environment. “Full states” is the final continued-pulling state
count; “planning states” is the maximum number of unfinished states at any
wish.

| Case | v0.3.1 full | v0.3.2 planning | Speedup | Full states | Max planning states |
|---|---:|---:|---:|---:|---:|
| A: pity 0, target 3, budget 320 | 4.866 s | 0.085 s | 57.44x | 28,388 | 448 |
| B: pity 37, target 2, budget 240 | 2.868 s | 0.027 s | 107.50x | 26,011 | 232 |
| C: pity 0, target 7, budget 800 | 21.231 s | 0.597 s | 35.58x | 35,676 | 1,164 |

Peak process working set was sampled externally while each calculation ran:

| Case | Full-distribution peak | Target-aware peak |
|---|---:|---:|
| A | 20.613 MiB | 15.492 MiB |
| B | 20.004 MiB | 15.590 MiB |
| C | 24.844 MiB | 15.609 MiB |

The speedup comes from semantic state reduction, not approximation. Completed
mass is removed from the active state map and recorded at its first hitting
time; unfinished states never contain copies at or above the target. Run the
maintained target-aware benchmark with:

```powershell
$env:PYTHONPATH = "src"
python benchmarks/benchmark_v032.py --repeats 3
```

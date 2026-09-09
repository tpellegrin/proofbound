# Fresh baseline under the atomic pressure — pre-registration

Frozen before any reflector call. The fixture is untouched since `4e0784a`; the pressure is frozen
in `atomic-pressure.txt`; the grader column passed its adequacy gate before this was written.

## Why a fresh baseline rather than a re-grade

The retained thirty reports were produced under a different column and have been read. Re-grading
them against the atomic pressure would produce numbers fitted to reports already inspected, and
would splice two experiments. They stay where they are, and this measures new evidence.

## Grader adequacy, measured before this run

| Anchor | Category | Counts | Modal share |
|---|---|---|---|
| `d1` | identifies the leakage plainly | detected 15 | **1.00** |
| `d2` | identifies it and calls it reasonable | detected 15 | **1.00** |
| `d3` | says interpretation is correctly isolated | not-detected 11, detected 4 | 0.73 |
| `d4` | selection and central import only | not-detected 15 | **1.00** |
| `d5` | provider identity and selection only | not-detected 15 | **1.00** |
| `d6` | generic provider concerns | not-detected 14, detected 1 | 0.93 |

Every modal outcome matches its declared category; 90/90 graded, no parse failures; pooled
non-modal 5/90. Under the previous column `d3`, `d4` and `d5` were all credited as detections — the
atomic column separates provider-awareness from provider-outcome-interpretation, which is the whole
point of the repair.

## Local resolution

Grader dispersion on this column is zero on four anchors, 7% on one, and 27% on the genuinely
ambiguous "correctly isolated" class. At N=10 that is roughly 0 to 2.7 counts of grading noise per
cell, depending on how ambiguous the reports in that cell are. Reflector-level variation on this
column is unmeasured — this run is its first measurement — so no treatment effect smaller than that
combined floor could be read later, and this baseline states the shape rather than a threshold. No
p-values, no confidence intervals, no assumption that ten same-model samples are ten independent
draws.

## Measurement

Frozen closed-world substrate, unmodified. One arm, `baseline`. The three states, each with the
frozen reference `r0002` implementation applied. One pressure. **N = 10** per state — 30 fresh
reflections, each graded once. Fresh executions throughout: no slot, session or report from the
previous baseline is reused, and `P12` here means provenance independence only, never statistical
independence.

## Interpretation categories, fixed in advance

- **Clear headroom** — `state-a` and `state-b` low, `state-c` non-zero and meaningfully below
  ceiling. Specificity and sensitivity both have room.
- **Limited headroom** — `state-a`/`state-b` low, `state-c` high enough that a treatment has little
  to gain.
- **No headroom** — `state-c` saturated.
- **Non-specific pressure** — `state-a` or `state-b` still frequently detected.
- **No baseline discrimination** — the three overlap.
- **Measurement too unstable** — within-cell dispersion or missingness swamps the contrast.

## Analysis committed in advance

Every `state-a`/`state-b` detection is inspected and classified: genuine grader error; a real
pressure the reference analysis missed; wording still broad; ground truth wrong; the report merely
mentions provider selection; or it criticises unrelated provider details. A detection is not called
false merely because of the state's label — **if the reports expose a contradiction in the
benchmark's ground truth, that outranks the expected label and gets reported.** Every `state-c`
non-detection is classified too: never observed; observed but phrased indirectly; grader missed it;
the report was about something else; or the ground truth is ambiguous.

Discovery is not a verdict. A report that notices provider-independent code interpreting a
provider's reply and calls the design reasonable has still found the pressure.

## After the first call

Nothing changes: not the pressure, the grader, the fixture, the intent, `N`, the reflector context,
the interpretation categories, or which samples count. A defect found mid-run is recorded and
redesigned in a later milestone.

# What `pb-handoff-1`'s evidence still supports

Dated 2026-09-21. `pb-handoff-1` ran on 2026-09-18 and produced real observations. Its temporary
workspace — including the OpenCode session databases and the full worker logs — was removed when the
run ended, as designed: that data is disposable by policy. This document records what the offline
evidence reader can and cannot recompute from what remains, and why.

**Nothing here revises that run.** Its files are unmodified, its conclusions stand, and the checks
that still work are not downgraded because other checks cannot run. The adapter that reads it is
narrow and one-way: it builds a package from one historical layout and modifies nothing.

Reproduce with:

```bash
python3 evals/authority_slice/pb_evidence.py adapt-handoff-1 \
    --condition-dir evals/authority_slice/runs/pb-handoff-1/valid --into /tmp/h1-valid
python3 evals/authority_slice/pb_evidence.py verify --package /tmp/h1-valid
```

## The valid condition

| Check | Kind | Result |
|---|---|---|
| `files.integrity` | integrity | **ok** — 64 retained files, digests match |
| `launch.attempts` | recompute | **ok** — 2 launches attributable to the run, 3 seeded beforehand, 5 in the tree |
| `launch.lifecycle` | recompute | **ok** — both live attempts carry a terminal record |
| `launch.reservations` | recompute | **ok** — 2 of 2 reserved a slot before the executor was reached |
| `price.recompute` | recompute | **ok** — **$0.020516 re-derived** from retained aggregate totals at `deepseek-2026-09-09` |
| `usage.recompute` | unavailable | the session databases were not retained |
| `usage.attribution` | unavailable | the per-call events the totals were summed from are gone |
| `authority.binding` | integrity | **ok** — 3 bound contracts hash to what run state recorded |
| `authority.admission` | unavailable | this run predates admission enforcement |
| `artifact.retained` | integrity | **ok** — the delivered `dispatch.py`, `d998c0eaff9f…` |
| `artifact.historical-result` | reported | the run recorded `pass` for these bytes |
| `artifact.recheck` | unavailable | the accepted requirements the checker consumed were not retained separately |
| `decision.coordinator`, `review.findings` | reported | retained verbatim and attributable; nothing confirms the judgments |
| `decision.acceptance` | integrity | **ok** — 3 tasks recorded as accepted |
| `coverage.tool-exposure` | unavailable | no tool trace was retained |

**8 ok, 3 reported, 5 unavailable.** Those do not add up to a score, and the reader offers no
aggregate verdict.

## The control condition

Zero launches attributable to the run, three seeded attempts retained, and no provider session
invented to explain the absence. `launch.lifecycle` reports that there is no lifecycle to settle:
**a refusal is established by the absence of a launch**, which is exactly what that condition
claimed. Its accounting checks are unavailable for the same reason the valid condition's are.

## The boundary, precisely

The aggregate **arithmetic** survives and the per-call **attribution** does not. Those are different
losses and the reader keeps them apart:

* `$0.020516` is re-derived here from the retained token totals — 31,123 uncached input, 651,264
  cache-read, 13,803 output — at the pinned historical table. This is a real independent check:
  perturbing the retained totals by 10,000 output tokens moves the figure to `$0.027116` and reports
  a mismatch, so the check computes rather than echoes. It is still a *derived* figure, not
  provider-confirmed billing.
* Which of the 33 model calls belonged to which of the 2 attempts cannot be established. The run's
  own account recorded equal start and finish counts, and equal counts are a consistency property,
  **not** per-attempt attribution.

## What was learned, for the next run

Three retention gaps, each now closed by the exporter rather than by remembering:

1. **The session database is the irreplaceable artifact.** Everything else was reconstructable from
   the run tree; the per-call events were not. The package now extracts an allowlisted projection of
   them at collection time, so the transcript can still be discarded.
2. **The checker's subject must be retained with the artifact.** `artifact.recheck` is unavailable
   here only because the accepted requirements were not kept beside the delivered file. Re-checking
   against today's requirements would grade the bytes against an authority the run never had.
3. **Seeded and live attempts must be separated at collection time**, from the launch ledger's own
   slots. Reading the run tree alone would attribute three stand-in attempts to the coordinator.

A defect in collection cannot be repaired afterwards into complete evidence. That is the reason the
next qualification collects during the run and not after it.

# MLR paired calibration — the run, and why it does not answer its question

The frozen paired comparison was executed as declared. It did not complete: a provider outage took
five of the eight pairs, and **the experiment is invalid for want of completeness, not for want of
validity**. Nothing was redesigned, retuned or re-scoped in response.

## 1. What was run

`mlr-c3r-paired`, frozen identity `0eabff2091f486c7`. Fixture `1b8a53b6e818d6f2`, runtime digest
identical across arms, contract `af3d3e9be15b51ed`, task `eb24429a46ecad4c`, oracle v2
`86f17eaf2685ac22`, attribution `mlr-context-2`, profile `profile-1`, model
`opencode/nemotron-3-ultra-free`, implementer role, `--auto`. N = 8 pairs, 16 slots, order generated
before execution and rotating so neither arm led every pair.

Treatment integrity verified before the first call: identical runtime digests, identical contract
sha, and the only workspace difference the four vendored files in `full`.

## 2. What happened

| pair | pattern | full | contract |
|---|---|---|---|
| 1 | both correct | valid | valid |
| 2 | both correct | valid | valid |
| 3 | both correct | valid | valid |
| 4 | **pair-invalid** | 3 harness failures | 3 harness failures |
| 5 | **pair-invalid** | 3 harness failures | 3 harness failures |
| 6 | **pair-invalid** | valid (2nd attempt) | 3 harness failures |
| 7 | **pair-invalid** | valid | 3 harness failures |
| 8 | **pair-invalid** | 3 harness failures | 3 harness failures |

33 records, 8 valid executions, 25 failed attempts, 1.7 hours wall clock.

**The cause was provider unavailability.** From roughly 20:14 the frozen model began returning
`Error from provider (Console): Upstream request failed: [404] Provider returned error`. Confirmed
independently, outside the fixture, with a trivial prompt at two separate times. It recovered briefly
— pair 6 `full` and pair 7 `full` completed — and failed again.

**What was not done.** The model was not changed: it is a frozen component, and substituting one
would have produced a different experiment rather than rescuing this one. N was not extended and no
pair was substituted for a lost one; both are adaptive. The driver was not stopped early, so the
extent of the outage is recorded rather than truncated. Each affected slot received exactly the three
bounded attempts the pre-registration allows, and every failed attempt is retained.

**Pairs 6 and 7 have a valid `full` run and no partner.** They are recorded `pair-invalid`. An
unpaired `full` execution is not a result for `full`, and the analysis refuses to treat it as one.

## 3. The three complete pairs

| pair | F correct | C correct | F source | C source | F runtime | C runtime | F contract | C contract |
|---|---|---|---|---|---|---|---|---|
| 1 | yes | yes | 5,822 | 0 | 1,383 | 2,154 | 1,600 | 0 |
| 2 | yes | yes | 2,538 | 0 | 0 | 1,351 | 0 | 674 |
| 3 | yes | yes | 5,458 | 0 | 0 | 975 | 0 | 0 |

Module-internal representation, total: `full` 7,205 / 2,538 / 5,458 against `contract` 2,154 / 1,351
/ 975.

Execution profile on correct runs (median [min..max]):

| | full (n=5) | contract (n=3) |
|---|---|---|
| implementation source | 5,458 [2,538..7,204] | **0 [0..0]** |
| implementation runtime | 0 [0..1,383] | 1,351 [975..2,154] |
| public contract | 0 [0..1,600] | 0 [0..674] |
| application | 7,685 [7,685..7,871] | 7,884 [7,387..8,687] |
| model calls | 28 [17..31] | 29 [24..30] |
| input tokens | 184,827 [154,438..275,013] | 215,549 [203,040..244,408] |
| output tokens | 7,969 [5,544..8,668] | 5,769 [5,226..6,680] |
| tool calls | 33 [24..39] | 31 [28..35] |
| session seconds | 214 [104..336] | 299 [276..336] |
| tool seconds | 0.97 [0.66..1.55] | 1.35 [1.13..1.39] |
| cost | $0 | $0 |

Every session was summarised, so delivered-volume figures are upper bounds. Verification time is
~0.09 s and tool time is under two seconds against three to six minutes of session span: the workload
remains **model-latency-bound**, as MLR-C3R found.

## 4. What the three pairs suggest, and why it is not the finding

The treatment held perfectly: `contract` consumed **zero** direct implementation source in every run.
`contract` compensated with runtime introspection — `help(objectstore)` was used, and the repaired
attribution classified it correctly, which is the first field confirmation that the MLR-C3 defect is
closed. But the compensation is smaller than what it replaced: 975–2,154 bytes against 2,538–7,205.

That shape is *reduction with partial reconstruction* rather than either clean substitution or a pure
representation shift. **It is not reported as a result.** Three pairs is not the pre-registered
experiment, and the pre-registration's own budget reasoning was that eight pairs were needed
precisely because correctness is the quantity with the least resolution — 3/3 concordance carries
almost none. Reporting "substitution supported" from three pairs would be fitting a conclusion to the
data that survived an outage.

## 5. Audits

**Oracle.** No incorrect run occurred in any of the eight valid executions, so no rejection needed
auditing. Oracle v2 rejected nothing that ran.

**Attribution.** Three inbound items carried module-internal names while classified as `behaviour`,
one of them in the **`full`** arm. All three are the same thing: a traceback from an agent's own
absence probe, disclosing 103–105 bytes —

```
File "objectstore/_store.py", line 55, in get
objectstore._errors.NotFound: exports/eu/u-3/monthly.csv
```

— a file name, a line number and the qualified name of a **public** exception. MLR-C2 accepted
`co_filename` as reachable ("a name, not a body") and the MLR-C3R pre-registration declared exactly this treatment:
disclosure recorded beside provenance, never added to it. That it appears in `full` as well confirms
it is a property of probing absence, not a `contract` compensation route.

Two model-authored items named internals; both occurred in runs that had consumed 2,761–7,205
attributed implementation bytes. **Model-side disclosure in runs that consumed no implementation: 0**
— the check that would catch an escape hiding behind that exclusion.

No material implementation representation reached model history unattributed.

## 6. Status

The instrument is sound and the treatment held. The experiment is **incomplete**: five of eight pairs
were lost to infrastructure, and a re-run is required under a **new experiment identity**, since
resume across a partially-consumed frozen series would splice two runs.

The three complete pairs and every failed attempt are retained as evidence of what was executed and
what the outage cost. They are development evidence for the re-run's budget, and **no execution here
may become a sample of it**.

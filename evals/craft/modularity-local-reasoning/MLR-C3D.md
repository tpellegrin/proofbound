# MLR-C3D — DeepSeek V4 Flash headroom qualification

Five `full`-only runs under a frozen DeepSeek V4 Flash configuration, pre-registered before the first
fixture call. **All five correct, all five consuming implementation source — and the attribution
instrument that survived Nemotron did not survive DeepSeek.**

Total spend **$0.171** against a $2.00 ceiling. No `contract` sample was bought.

## 1. What this qualification is, and is not

A new model is a new experimental condition. Nothing Nemotron established applies to DeepSeek, and
nothing here is a repair, resume or continuation of the invalid Nemotron paired run. No Nemotron
execution is a sample here; no sample here may be pooled with one. The experiment id
`mlr-deepseek-v4-flash-high-full-headroom` carries the model configuration so a listing cannot
confuse them.

## 2. Frozen configuration

| | |
|---|---|
| requested model | `deepseek/deepseek-v4-flash`, provider `deepseek` (OpenCode native) |
| documented version | `DeepSeek-V4-Flash-0731`, docs read 2026-09-09 |
| provider-observed | `deepseek-v4-flash` / `deepseek` — identical across all five runs |
| thinking | enabled, set explicitly rather than inherited |
| reasoning effort | `high` — `--variant high`, confirmed as `variant: high` in every run's telemetry |
| sampling | not controllable; the provider ignores `temperature`, `top_p`, `presence_penalty`, `frequency_penalty` in thinking mode |
| oracle | `external_test_v2.py`, unchanged |
| attribution / profile | `mlr-context-2` / `profile-1`, unchanged |
| price identity | `deepseek-2026-09-09` |

The alias is not an immutable weights identifier and is not treated as one: request, documented
version and observed identity are recorded separately. All five runs report one model and one
variant, so the configuration held for the series.

## 3. Compatibility, qualified before the fixture

A bounded synthetic task — a one-line bug in a two-file project, not the MLR fixture — exercised the
whole workflow: `bash`, two `read`s, `edit`, `bash` again, the test suite run and passing. Telemetry
recorded 4 model calls, 5 tool calls, usage, identity and variant. Cost **$0.0018** derived,
**$0.0011** by OpenCode's own figure, and it is accounted separately from the experiment.

Two provider-telemetry facts came out of it and both are now load-bearing. `total = input + output +
cache_read` summed exactly (7380 = 5714 + 2 + 1664), so the reported input count **excludes** cached
tokens and cache is billed on top rather than subtracted. And OpenCode's cost figure **disagrees**
with the published rates — across the pilot, $0.058 reported against $0.171 derived — so both are
retained and neither replaces the token counts.

## 4. The pilot

| run | correct | impl. source | impl. runtime | contract | calls | input | output | cache read | cost | window | s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | yes | 5,822 | 12,746 | 2,994 | 23 | 30,645 | 7,559 | 682,496 | $0.0330 | peak | 104 |
| 2 | yes | 5,822 | 1,885 | 2,994 | 25 | 22,277 | 8,934 | 625,664 | $0.0304 | peak | 100 |
| 3 | yes | 5,822 | 14,668 | 3,069 | 32 | 33,364 | 11,215 | 1,209,728 | $0.0464 | peak | 172 |
| 4 | yes | 5,822 | 35,796 | 2,994 | 22 | 31,761 | 7,995 | 653,312 | $0.0337 | peak | 103 |
| 5 | yes | 5,822 | 1,805 | 2,994 | 22 | 21,426 | 7,593 | 555,392 | $0.0272 | peak | 105 |

Five valid attempts, no setup or harness failure, no re-run, every profile complete. All ran inside
the peak window; at off-peak rates the same series would have cost about half.

**Correctness 5/5. Source consumption 5,822 bytes in every run** — the same three files each time.
Runtime-derived representation varies enormously, 1,805 to 35,796 bytes.

## 5. Headroom, and a different agent

Against the pre-registered categories the source result is **strong headroom**: all five correct runs
consumed source, and the median of 5,822 is far above the 1,000-byte line.

DeepSeek explores quite differently from Nemotron, which is worth recording as observation rather
than interpretation:

- **It reads the contract, every time** (2,994–3,069 bytes). Five of six Nemotron runs never opened it.
- **It introspects the runtime heavily even with source available** — up to 35,796 bytes, where
  Nemotron's `full` arm peaked at 1,383.
- **It uses roughly a seventh of the input tokens** — 21k–33k against Nemotron's 154k–325k — with
  comparable output, and finishes in 100–172 s against 110–750 s.
- **It explores the harness itself**, reading worker rules, proof patterns, the scope baseline, the
  launch prompt, `state.json`, its own `attempt.json` — and its own `worker.log`.

That last habit is what disqualifies the instrument.

## 6. The instrument did not survive the new model

**Four material inbound escapes**, in a route family Nemotron never used.

**Three of five runs read their own `worker.log`** — 5,962, 6,218 and 8,154 bytes, each carrying
`_backend`, `_errors` and `_store`, each classified **`harness`**. The log is a verbatim echo of the
agent's own tool outputs, including everything it had read from the implementation, and it sits
inside the workspace at a path `classify_file` maps to harness by name. Implementation text arriving
through a harness-pathed file is therefore invisible to implementation accounting.

**One run's `git status && git ls-files`** returned 630 bytes naming the same three internals — the
module's file structure disclosed through ordinary version-control inspection, classified
**`behaviour`**.

Neither is a `contract`-specific compensation route; both appeared in the `full` arm, where source
was already readable. That is precisely why they matter for a paired run: in `contract`, where no
source exists, a run that introspected and then re-read its own log would deliver that interior back
into context as *harness* bytes, and the arm would be scored as having consumed less implementation
representation than it did. That is the fake zero the whole design exists to prevent.

Model-side disclosure was clean: sixteen items where the model's own text named internals, every one
in a run that had consumed 18,568–41,618 attributed implementation bytes, and **zero** in a run that
consumed none — the check that would catch an escape hiding behind that exclusion.

**Oracle:** no run was incorrect, so oracle v2 rejected nothing that ran. It is not implicated.

## 7. Verdict

The pre-registration is explicit: strong headroom authorises designing a paired experiment **only
with a clean attribution audit**. The audit is not clean, so **no paired experiment is designed or
pre-registered**, and no `contract` sample is bought.

This is the qualification working. A second model was an adversarial test of an instrument that had
only ever met one agent's habits, and it found two disclosure routes in five runs for seventeen
cents — before any paired money was spent, and before a result could be reported that the instrument
could not support.

## 8. What a revision must do

1. **Attribute implementation text by content wherever it arrives**, not only by the path or command
   that requested it — the harness path currently masks it. The disclosure channel already detects
   these items; what it cannot do is attribute their bytes, which is the gap.
2. **Decide what the run's own log is.** Re-reading it re-delivers already-consumed representation;
   whether that is new consumption, repeated delivery, or should be excluded from the workspace the
   agent explores at all is a design question, not a classifier tweak.
3. **Classify version-control listings** that disclose module structure.
4. **Re-qualify under a new identity.** These five runs do not transfer to a repaired instrument.

## 9. Cost

Qualification $0.171 derived (peak) against a $2.00 ceiling; infrastructure smoke $0.0018 accounted
separately; OpenCode's own figure $0.058 for the same calls, retained beside the derived figure.
Every call is priced by the window its own timestamp fell in.

A paired experiment under this configuration would be inexpensive — sixteen runs at the observed
median would be roughly $0.55 peak, half that off-peak. **Cost is not what stops it.** The instrument
is.

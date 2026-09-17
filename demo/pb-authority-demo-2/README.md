# pb-authority-demo-2

The second real-agent demonstration of Proofbound's engineering-authority chain, and the first to
attempt it **across a genuine fresh-context handoff**.

`pb-authority-demo-1` stopped after a real specification finding under its frozen no-repair rule.
Its records are preserved unchanged; corrections to its *preparation* live in
`docs/architecture/proofbound/evidence/authority-workflow-successor.md`. This is a separate
demonstration with a separate identity, not a rerun.

| File | What it is |
| --- | --- |
| `intent.md` | The accepted parent authority. Seven numbered requirements. Frozen before the first paid call; never edited during the run. |
| `protocol.md` | The frozen execution protocol: identities, information flow, accounting scope, launch ceiling, stop conditions, the one shared repair cycle and everything it invalidates, the handoff, the runbook. |
| `contracts/` | The three task contracts, each stamping the intent's digest so its identity is checkable after the handoff. |
| `fixture/` | The `rateguard` package and its own test suite, byte-identical to the predecessor's. |
| `external-suite/` | The behavioural suite the coordinator runs, withheld from every worker. `witness/` holds the private reference implementation. |
| `verify_suite.py` | Proves the external suite satisfiable (the witness passes) and discriminating (six defective variants fail). Unpaid. |
| `rehearse.py` | Drives the whole sequence against a credential-free fake executor, on the clean path and the repair path, including `pb_execution.py authorize`. Unpaid. |
| `run-report.md` | What happened, what was verified independently, and why the run stopped. |
| `handoff-input.md` | The verbatim text prepared for the fresh coordinator. Never delivered — the run stopped upstream. |
| `posthoc_negative_clock.py` | A check the frozen suite cannot make, reported separately and never merged into its verdict. |
| `evidence-attempts/` | Every attempt's prompt, report, gate, scope diff and terminal record. |
| `departures.md` | Append-only, dated record of every departure from the frozen protocol, and of repository code changed mid-run. |
| `execution-record.json` | Identities, information flow, launch ceiling, stop conditions and handoff rules, fixed before the first paid call. |
| `scaffold.py` | Mechanical setup, identities, the withholding measure, and reconciled spend accounting. Launches no worker and makes no semantic decision. |

Regressions for the accounting repairs are in `tests/test_authority_demo2_accounting.py`.

## Added after the run (2026-09-17)

The run's records above are unmodified. These were added by a post-run audit, whose findings and
their effect on this run's claims are in
`docs/architecture/proofbound/evidence/authority-workflow-demo-2-audit.md`.

| File | What it is |
| --- | --- |
| `negative_clock_adjudication.py` | A three-valued decision — `exists` / `none` / `unknown` — for whether a conforming finite delay exists, with the completeness argument `posthoc_negative_clock.py` lacked. Adjudicates that check's output rather than replacing it. |
| `scaffold.py` (dated correction inside) | The interrupted-call "upper bound" was an estimate. A heuristic reserve is now labelled as one, a ceiling requires an enforced limit, and an unfinished call leaves the spend figure incomplete. |

```bash
python3 demo/pb-authority-demo-2/negative_clock_adjudication.py witness
python3 demo/pb-authority-demo-2/negative_clock_adjudication.py pair --points 200
python3 demo/pb-authority-demo-2/negative_clock_adjudication.py replay-probe
```

```bash
python3 demo/pb-authority-demo-2/scaffold.py identities
python3 demo/pb-authority-demo-2/verify_suite.py
python3 demo/pb-authority-demo-2/rehearse.py --into <scratch> --path clean
python3 demo/pb-authority-demo-2/rehearse.py --into <scratch> --path repair
```

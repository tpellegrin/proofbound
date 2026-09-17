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
| `scaffold.py` | Mechanical setup, identities, the withholding measure, and reconciled spend accounting. Launches no worker and makes no semantic decision. |

Regressions for the accounting repairs are in `tests/test_authority_demo2_accounting.py`.

```bash
python3 demo/pb-authority-demo-2/scaffold.py identities
python3 demo/pb-authority-demo-2/verify_suite.py
python3 demo/pb-authority-demo-2/rehearse.py --into <scratch> --path clean
python3 demo/pb-authority-demo-2/rehearse.py --into <scratch> --path repair
```

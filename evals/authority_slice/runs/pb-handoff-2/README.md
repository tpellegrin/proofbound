# `pb-handoff-2` — retained evidence

Executed 2026-09-21 against the instrument frozen at `af10cbf`. Read
[`run-report.md`](run-report.md) first; it states what each condition established and what it did
not.

| Path | What it holds |
|---|---|
| [`run-report.md`](run-report.md) | Outcomes, predicates, accounting, defects, limitations |
| [`findings/`](findings/) | Three defects found by executing. Dated, unrepaired, scoped to a later milestone |
| `control/` | The control condition's sealed evidence package, plus its input, identities, probe and qualification |
| `valid/` | The same for the valid condition |
| `*/coordinator-report-relayed.md` | Each coordinator's own account, **outside** the sealed package and labelled as relayed |

Each package is relocatable and was qualified **after** its runtime was destroyed. The
`manifest.json` in each states what was collected, what was omitted and which checks each omission
blocks; identities recorded inside the evidence — including absolute paths on runtimes that no
longer exist — are left exactly as written.

```bash
S=evals/authority_slice
python3 $S/pb_evidence.py qualify --package $S/runs/pb-handoff-2/valid
python3 $S/pb_evidence.py qualify --package $S/runs/pb-handoff-2/control
```

Control qualifies **no**, valid qualifies **yes**. The control's failure is the fixture's, not the
coordinator's and not the mechanism's — `run-report.md` says why.

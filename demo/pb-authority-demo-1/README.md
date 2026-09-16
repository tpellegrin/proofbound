# `pb-authority-demo-1`

The disposable project, contracts, correctness suites and scaffolding for Proofbound's first
real-agent run of the full engineering-authority chain.

The committed design is
[`authority-workflow-demonstration.md`](../../docs/architecture/proofbound/evidence/authority-workflow-demonstration.md).
What it got wrong, and what had to be built before it could run, is in
[`design-to-execution-check.md`](design-to-execution-check.md).

| | |
|---|---|
| `intent.md` | the accepted intent — parent authority, the only requirements any agent is given |
| `fixture/` | the initial `rateguard` project and its own suite, which must keep passing unedited |
| `contracts/` | the three task contracts, one per task, each declaring its review purpose |
| `external-suite/` | the hidden behavioural suite and a private reference implementation |
| `scaffold.py` | setup, fixture identities, the external-suite lock, spend accounting. No roles. |
| `rehearse.py` | drives the whole sequence with a fake executor. Unpaid. |
| `controls.py` | the mechanical refusal controls, each on its own disposable copy. Unpaid. |

Nothing here is an eval and nothing relates to `q1` or `b1`. `python3 -m unittest discover -s tests`
never reaches this directory.

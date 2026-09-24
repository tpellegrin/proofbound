# Ordinary first-use project and paired pilot

This small CSV library and CLI already run. The proposed change adds a strict mode across parser,
aggregation, CLI errors and tests. It is not a numerical scheduling puzzle and has no embedded
reference implementation. The task has not been used to tune the workflow.

Prepare both arms without provider requests:

```bash
python3 examples/csv-summary/prepare.py /private/tmp/csv-summary-pilot-1
python3 -m unittest discover -s examples/csv-summary/project
python3 examples/csv-summary/check_outcome.py /private/tmp/csv-summary-pilot-1/direct
```

The last command should fail on the unchanged starting project because strict mode is not implemented.
It is a baseline check, not a failed agent trial. **[protocol-v2.md](protocol-v2.md)** fixes budgets, handoff, the derived launch ceiling,
repair/stopping rules and measurement. [protocol.md](protocol.md) is its superseded,
never-run predecessor, retained unmodified. [The goal](goal.md) is identical for both arms.

For treatment first use, after the freeze and applicable authorization:

```bash
PB=/absolute/path/to/proofbound
PROJECT=/private/tmp/csv-summary-pilot-1/proofbound
python3 "$PB/scripts/pb_workflow.py" doctor
python3 "$PB/scripts/pb_workflow.py" start --project "$PROJECT" --change CH-001 \
  --goal-file /private/tmp/csv-summary-pilot-1/goal.md --check 'python3 -m unittest discover'
RUN="$PROJECT/DeepSeekAndDestroy/plans/CH-001/runs/first"
python3 "$PB/scripts/pb_workflow.py" status --run "$RUN"
```

Follow [the operator guide](../../docs/operator-guide.md), with the protocol's resource ceilings only
after the owner authorizes them. Start neither arm until the freeze and qualification prerequisites
are met. The direct prompt is: “Implement goal.md in this project, preserving its compatibility
constraints. Inspect, plan, test and self-review as needed. Retain a plan before implementation for a
fresh-context handoff, then return the change, checks and unresolved issues within protocol-v2.md.”

No real-agent first-use or paired result is claimed by this preparation.

## A single first-use run, separate from the pilot

`first_use.py` prepares one run of the same public goal and outcome check under whichever
coordinator will drive it and whichever instrument is checked out. It never touches the frozen
pilot files above, and its result is diagnostic — not the pilot, not held out, not a comparison.

```bash
python3 examples/csv-summary/first_use.py prepare --into /private/tmp/csv-first-use-1 \
  --coordinator claude-code/opus --executor /path/to/pinned/opencode
```

It builds a fresh project, records every identity the run depends on in
`first-use-identity.json`, and prints the commands: start from the goal, record the coordinator,
authorize (proposed limits: 11 launches, $0.55 derived, $0.05 reserve — not an authorization),
drive, finish, and then `verify-delivery`, which applies the sealed patch to a fresh baseline
checkout and runs the project and outcome checks there. It launches and spends nothing.

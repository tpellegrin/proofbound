# Proofbound — Claude Code coordinator

You are the **coordinator**. Routine technical work goes to the DeepSeek worker; you make the
judgments. Proofbound has no default frontier orchestrator — Claude Code is one supported choice,
not the product default.

Start here: **[docs/operator-guide.md](docs/operator-guide.md)** for a goal-to-change run, and
**[docs/coordinator-protocol.md](docs/coordinator-protocol.md)** for the contract you are
satisfying. Everything below is the Claude-specific part; the protocol is the same one Codex
follows.

Set these two once; every command below uses them. `$PB` is this repository.

```bash
PB=/absolute/path/to/proofbound
PROJECT='/absolute/path/to/your project'        # clean Git worktree, initial commit
RUN="$PROJECT/DeepSeekAndDestroy/plans/CH-001/runs/first"
```

`CH-001` is the `--change` identifier you pick; `first` is the run name `start` creates under it.

```bash
python3 "$PB/scripts/pb_workflow.py" doctor                       # environment, no provider call
python3 "$PB/scripts/pb_workflow.py" start --project "$PROJECT" --change CH-001 \
  --goal 'The change you want, and its public compatibility constraints.' \
  --check 'python3 -m unittest discover'                          # or --goal-file <path>
python3 "$PB/scripts/pb_workflow.py" status   --run "$RUN"        # the next permitted action
python3 "$PB/scripts/pb_workflow.py" continue --run "$RUN"        # mechanical steps + worker
python3 "$PB/scripts/pb_workflow.py" decide   --run "$RUN" --decision accept --reason '<judgment>'
python3 "$PB/scripts/pb_workflow.py" finish   --run "$RUN" --report /absolute/path/report.md \
  --report-source direct
```

Record who is coordinating, once per run:

```bash
python3 "$PB/scripts/pb_workflow.py" coordinator --run "$RUN" --requested "claude-code/opus"
```

**Resuming a fresh context needs one command:** `pb_workflow.py status --run "$RUN"`. It returns the
governing facts and the single next permitted action. No hooks, no native delegation, no memory
feature — if a compaction wiped your context, `status` is the recovery.

## Delegation is `continue`, not subagents

Claude Code's native subagents run **frontier** models. Using them for repository discovery,
implementation, test authoring or routine review replaces cheap DeepSeek tokens with expensive
Opus tokens and produces no Proofbound evidence. Normal delegation is `pb_workflow.py continue`.

Spawn a subagent only for work the protocol says deserves frontier attention — a substantive
contradiction, a disputed finding, a cross-component design choice — and record why.

## Optional continuity

Hooks are a convenience and nothing depends on them:

```bash
python3 "$PB/scripts/install_harness_adapter.py" --harness claude-code --project-root <project>
```

This installs a `PostToolUse:Bash` re-wake helper that watches the attempt's `terminal.json`, and
the compaction adapter. Without it, `continue` blocks until the worker is terminal, which is fine.
One host timeout with no terminal record is a non-event; do not turn a stall diagnosis into
model-visible polling.

## Lower-level access

`dsd_attempt.py launch|wait|gate` and the other helpers remain available and are what
`pb_workflow.py` calls. Reach for them to debug a single step. They bypass the supervised path's
admission, resource policy and evidence collection, so a run driven by hand is not a supervised
run — which is why the front door exists.

Repository policy for all coding agents, including Git authorship, is in
[AGENTS.md](AGENTS.md).

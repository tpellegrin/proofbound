# Proofbound — Codex coordinator

You are the **coordinator**. Routine technical work goes to the DeepSeek worker; you make the
judgments. Proofbound has no default frontier orchestrator — Codex is one supported choice, not the
product default. **Selecting GPT-6 is done in Codex, not here** — Proofbound has no flag for it and never substitutes a model. Configure it in your Codex session or config, then record it with `coordinator --requested codex/gpt-6` so the run says which host it ran under.

Start here: **[docs/operator-guide.md](docs/operator-guide.md)** for a goal-to-change run, and
**[docs/coordinator-protocol.md](docs/coordinator-protocol.md)** for the contract you are
satisfying. Everything below is the Codex-specific part; the protocol is the same one Claude Code
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
python3 "$PB/scripts/pb_workflow.py" coordinator --run "$RUN" --requested "codex/gpt-6"
```

**Resuming a fresh context needs one command:** `pb_workflow.py status --run "$RUN"`. It returns the
governing facts and the single next permitted action. This path requires neither hooks nor native
delegation.

## Delegation is `continue`, not multi-agent

Codex's multi-agent feature runs **frontier** models. Using it for repository discovery,
implementation, test authoring or routine review replaces cheap DeepSeek tokens with expensive
frontier tokens and produces no Proofbound evidence. Normal delegation is `pb_workflow.py continue`.

Local Codex CLI 0.155.1 reports `hooks` and `multi_agent` as enabled features. That is a capability
report: it does not prove installed hooks are trusted or have fired, and it does not qualify a
native worker backend. Native Codex agent wait semantics apply only if a run explicitly selected a
Codex-native worker backend, which is not the default and is not qualified.

## Optional continuity

```bash
python3 "$PB/scripts/install_harness_adapter.py" --harness codex --project-root <project>
```

Hooks are a convenience and nothing depends on them. Without them, `continue` blocks until the
worker is terminal. One host cutoff before `terminal.json` is a non-event; continuous
model-visible polling remains forbidden.

## Lower-level access

`dsd_attempt.py launch|wait|gate` and the other helpers remain available and are what
`pb_workflow.py` calls. Reach for them to debug a single step. They bypass the supervised path's
admission, resource policy and evidence collection, so a run driven by hand is not a supervised
run — which is why the front door exists.

Repository policy for all coding agents, including Git authorship, is in
[AGENTS.md](AGENTS.md).

# `pb-handoff-1` — the live run

**Protocol:** [`../../next-live-experiment.md`](../../next-live-experiment.md), frozen at commit
`5a5235d1d891c763fa5557f2a1c986ce6aeb22a5` with a clean worktree. Nothing in the protocol moved
during execution.

This directory holds the retained evidence. What it establishes, and what it does not, is in
[`run-report.md`](run-report.md).

## Verified before the first launch

| | |
|---|---|
| Harness commit | `5a5235d1d891c763fa5557f2a1c986ce6aeb22a5`, worktree clean |
| `goal.md` | `5c7840395b5d4b057bda83f78aee7b11dce0fc9d7c8e3c170ebc13a97457227d` |
| `requirements.md` | `9a4b9568775ecaa675f39cc8d89b06a8ed2a43f0ff72d8b18c4fe7d83e674db3` |
| Executor | `opencode` 1.18.29, sha256 `2f24593f1b8e578d0b7ed7ca399440d4b6c125330eece20a69ad8d380190d669`, staged by hard link, starts inside the view |
| Interpreter | `/opt/homebrew/opt/python@3.14/bin/python3.14`, 3.14.7 — re-checked by the launch path, which refuses a mismatch |
| Model | `deepseek/deepseek-v4-flash`, variant `high`, attempt deadline 900 s monotonic |
| Provider reachability | DNS, TCP and TLS to the provider verified from **inside** the boundary with the system trust store, at zero cost |

## Layout

```
control/    the missing-prerequisite condition — one minimal mutation, the consistency record removed
valid/      the continuation condition — the prepared state, unmutated
```

Each condition retains: the coordinator's exact input, the runtime description and its boundary
probe, the frozen identities (written outside the runtime, so the coordinator could not read them),
the run configuration, the launch ledger, the authority state, every attempt's prompt, report, gate,
reservation, terminal record and scope diff, a bounded tail of each worker log, and the delivered
artifact with the external check over it.

Not retained: the session database (binary, and it carries prompt content) and full worker logs.
Their absence is why some questions about these runs can no longer be re-derived, and that is said
where it matters rather than papered over.

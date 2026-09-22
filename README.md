# Proofbound

Proofbound helps an engineer carry a goal through proposed requirements, fresh challenge,
controlled implementation, review and an inspectable handoff. Python checks identities,
provenance and execution prerequisites; agents and people judge whether the change is good.
It is a supervised workflow, not a correctness proof or an autonomous developer.

Use it when requirements and authority need to survive an engineering handoff. Its overhead is
unlikely to help a small edit you can confidently inspect and test yourself. Better recordkeeping
is useful, but does not establish better software or lower total effort.

## First use

Clone this repository and point Codex at it; Python **3.10+** and the standard library suffice for
its helpers. The supported worker path is **macOS arm64**, pinned **OpenCode 1.18.29** with
**`deepseek/deepseek-v4-flash`, variant `high`**. An existing credential and explicit spending
authority are needed to launch workers. Readiness never makes a provider request.

```bash
PB=/absolute/path/to/proofbound
PROJECT='/absolute/path/to/your project'
python3 "$PB/scripts/pb_workflow.py" doctor
python3 "$PB/scripts/pb_workflow.py" start --project "$PROJECT" --change CH-001 \
  --goal 'Describe the desired change and public compatibility constraints here.' \
  --check 'python3 -m unittest discover'
RUN="$PROJECT/DeepSeekAndDestroy/plans/CH-001/runs/first"
python3 "$PB/scripts/pb_workflow.py" status --run "$RUN"
python3 "$PB/scripts/pb_workflow.py" continue --run "$RUN"
```

Start from a clean Git worktree with an initial commit. `start` preserves existing files, creates
unaccepted requirements and run templates, and grants **zero spending authority**. `continue`
performs one derived step, or returns the exact judgment/blocker. A fresh Codex session uses the
same `status` command. No hook is required and no state JSON needs hand editing.

Give Codex this prompt:

> Use Proofbound at `/absolute/path/to/proofbound` on my project. Read its operator guide and
> CODEX.md, inspect readiness, and start from my goal and compatibility constraints. Propose and
> freshly challenge requirements before accepting authority. Continue through implementation,
> fresh review and project checks, adjudicating routine decisions within scope. Preserve evidence
> and return the delivery patch or a precise blocker. Do not spend beyond my explicit authorization.

The [operator guide](docs/operator-guide.md) covers spending configuration, semantic decisions,
recovery and delivery. The [ordinary example and frozen paired pilot](examples/csv-summary/README.md)
provide a reproducible project and a comparison that has **not yet run**.

## What the workflow means

For example, an owner asks a CSV summary tool to reject malformed input in a new strict mode while
preserving its default behavior. The coordinator proposes requirements; a fresh spec reflector
challenges their compatibility and consistency. After adjudication, accepted requirements become
ledgered artifacts. The declared graph fixes membership and dependency edges. A freeze identifies
the accepted candidate; an accepted aggregate consistency review earns implementation admission.
The implementer and a fresh reviewer then work under that immutable contract. Project checks and
the coordinator's judgment precede task acceptance and handoff.

| Mechanism | What it establishes |
|---|---|
| Artifact ledger and graph | Accepted content identities and declared dependency closure |
| Candidate and admission | This implementation contract was admitted under this candidate |
| Attempts, integrity gates and fresh review | Recorded lifecycle, scope, contract identity and qualifying role/purpose; not semantic adequacy |
| Coordinator adjudication | A retained judgment, never inferred from persuasive prose |
| Project checks and delivery | Observed check results, patch, governing bindings and report provenance |

An admitted C1 task remains a C1 task after a later C2. Missing derived consistency records can be
legitimately restored from qualifying accepted evidence. A clean gate without the required
purpose and acceptance cannot earn that authority.

## Boundaries and evidence

The supervised launcher reserves slots before execution and refuses unresolved usage or exhausted
allowances. Its limit applies to **derived spend at a dated price table**, not provider billing;
a single in-flight call is not capped by that figure. Aggregate usage and per-attempt attribution
are separate. Unknown charges remain unknown. Direct executor invocation is outside this guard.

The macOS worker boundary restricts wrapped processes to declared paths, staged home and required
system resources. It is an evidence boundary, not a hostile-code sandbox guarantee. It cannot
observe the coordinator's host-side access. Run trees may contain private source, reports and
prompts; runtime homes hold a staged credential. Retain them intentionally, do not publish them
blindly, and clean up explicitly after handoff. SIGKILL finalization is not guaranteed.

Committed requirements, ledger, graph, freeze and consistency records can outlive deleting a run.
Task contracts, acceptance and implementation binding remain L3 run evidence. **Copying an evidence
package does not close the L3/L4 durable implementation-binding gap.** See the
[canonical durability boundary](docs/architecture/proofbound/freeze-and-binding.md#a66-execution-binding-only--the-durability-limitation-stated).

The inherited defaults in SKILL.md and helper configuration name
`opencode-go/deepseek-v4-flash`; that is a different provider route from the qualified
`deepseek/deepseek-v4-flash`. This front door selects the latter explicitly. `CONFIG.example.md`
is prose guidance, not a parsed configuration file. Installed, configured, supported and
experimentally qualified are different claims; `doctor` reports them separately. Codex with GPT-6
coordinates development here; it is not thereby a qualified worker backend.

## What has been demonstrated

[`pb-handoff-2`](evals/authority_slice/runs/pb-handoff-2/run-report.md), frozen at `af10cbfb`,
observed one real continuation from **seeded upstream authority** reaching accepted implementation
with enforced admission and replayable artifact checks. It established neither reliability,
superiority to a competent direct agent, nor good upstream authority production. Its control
legitimately restored a derived record from retained accepted evidence and failed the frozen
control predicate. Historical packages and outcomes remain unchanged.

The new goal-to-change entry point is subject to offline integration validation. Stand-ins do not
qualify real-agent use. The new live first-use and direct-agent comparison remain blocked on explicit worker spending authorization. Versioned observations belong in
[the milestone record](docs/architecture/proofbound/evidence/supervised-workflow-2026-09-21.md).
Interpret comparisons using the [canonical evaluation rules](docs/architecture/proofbound/evaluation-comparison.md).

## Read further

- [Operator guide](docs/operator-guide.md): commands, authority decisions and continuation.
- [Current roadmap](docs/operator-roadmap.md): user benefits and evidence gates.
- [Architecture router](docs/architecture/proofbound/README.md): normative definitions by task.
- [Evidence index](docs/architecture/proofbound/evidence/README.md): dated observations and corrections.
- [CONTRIBUTING.md](CONTRIBUTING.md): Python support and canonical serial test command.
- [SKILL.md](SKILL.md) and [CODEX.md](CODEX.md): coordinating-agent instructions.

Derived from DeepSeek-and-Destroy (MIT, © FrozenPepper); not affiliated with or endorsed by it.
Inherited `dsd_*` commands and `DeepSeekAndDestroy/` paths remain compatibility-sensitive wire
identifiers. [License](LICENSE).

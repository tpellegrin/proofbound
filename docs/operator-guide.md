# Run one supervised change

This guide is the operator route. Normative rules live in the
[architecture router](architecture/proofbound/README.md), particularly
[execution and review](architecture/proofbound/execution-and-review.md),
[artifact provenance](architecture/proofbound/artifacts-and-provenance.md), and
[freeze/admission A6](architecture/proofbound/freeze-and-binding.md).
The supported workflow has one requirements artifact, one aggregate consistency review and one
implementation task. Decomposing a larger project remains coordinator work outside this front door.

**Any capable frontier host can be the coordinator** — Codex, Claude Code/Opus, or another. The
commands below are identical whichever you choose; the contract a host satisfies is
[the coordinator protocol](coordinator-protocol.md). Getting the DeepSeek worker working is
[installation](installation.md).

## Initialize and inspect

Use the commands in the [root README](../README.md#first-use). `start` requires a clean Git worktree
and initial commit so the final patch has an unambiguous baseline. Commit or isolate existing work;
Proofbound never discards it. Set `--check` to the project's ordinary test command. It is parsed as
argv, not a shell program; use a project script for multiple commands. Paths with spaces are supported.
The same goal/change invocation returns the existing run; a conflicting invocation refuses.
An interrupted initialization is retained and diagnosed, never silently overwritten.

`doctor` reports Python, installed executor/version, configured DeepSeek credential (presence only),
platform and boundary availability. It checks executable identity against the historically qualified
OpenCode build. It does not contact a provider or establish that a credential is valid. It does not
qualify the new goal-to-change workflow. GPT-6 is the requested Codex coordinator configuration;
configure it explicitly in Codex, never substitute a model silently.

## Authority and resources

The owner supplies the goal, compatibility constraints and spending authority. The coordinator may
propose requirements, adjudicate fresh challenges, select ordinary implementation approaches and
accept evidence within that goal. Those delegated decisions do not need repeated human approval.
Material scope changes, policy choices the goal cannot settle, contradictions requiring new authority,
and additional spending return to the owner with the exact question and witness.

No launch budget is inherited from a past experiment. After explicit owner authorization:

```bash
python3 "$PB/scripts/pb_workflow.py" authorize-spending --run "$RUN" \
  --aggregate-limit 0.60 --reserve 0.10 --launch-ceiling 9 \
  --owner-authorization 'Reference the owner authorization, purpose and stopping conditions'
```

These are example amounts, **not authorization**. The policy allows one repair per producer task
within the shared ceiling. Count proposal author/challenge, aggregate challenge, implementation/review
and any permitted repair/review pairs before setting the ceiling. The launcher uses a 900-second
attempt deadline, and never automatically retries. The policy freezes once a slot is reserved.
Unknown spend or an unreconciled slot stops further launches. Limits are on measured usage priced
with the retained 2026-09-09 schedule, not provider billing or per-call cost. Verify that price basis
before authorizing live spend. Codex subscription consumption is unavailable unless separately
measured, never zero. Direct calls to lower-level launchers are outside this budget wrapper.

Configuration constructs the macOS worker boundary, probes host and staged home separately, and
stages only the DeepSeek credential. A failed boundary probe blocks configuration. The worker sees
the project, harness and required system/interpreter paths. The coordinator runs on the host and is
outside that boundary. This is not protection against malicious code or a compromised operator.

## Continue and adjudicate

```bash
python3 "$PB/scripts/pb_workflow.py" status --run "$RUN"
python3 "$PB/scripts/pb_workflow.py" continue --run "$RUN"
```

Each `continue` performs one derived mechanical action or one worker attempt and returns the next
command. It composes `dsd_state`, `dsd_attempt`, `pb_ledger`, `pb_freeze`, `pb_consistency` and
`pb_execution`. It stores no competing status ledger. Review reports are inputs to judgment;
Python never parses their wording into acceptance.

The sequence is:

1. Bind the proposed-requirements contract; spec author inspects the project and writes requirements.
2. Gate the author attempt; fresh spec reflector challenges goal fidelity, domain, compatibility and contradictions.
3. Coordinator adjudicates the fresh clean review. Record accepted requirements in the existing ledger.
4. Freeze accepted graph; fresh consistency reflection checks joint coherence. Adjudicate and record consistency acceptance.
5. Admit the candidate-bound implementation, implement, gate, and commission a fresh reviewer.
6. Adjudicate review, execute project checks, accept and deliver.

An unresolved `owner` decision remains visible on fresh status calls. After the owner actually responds, record it with `resolve-owner --run "$RUN" --owner-response 'the actual response'`; this resolves the request, never accepts a review automatically.

When `status` says `adjudicate`, read the named report and gate, the goal and accepted authority.
Judge findings and coverage. A clean gate means evidence is interpretable, not that engineering passed.

```bash
python3 "$PB/scripts/pb_workflow.py" decide --run "$RUN" --decision accept \
  --reason 'Explain why the findings and coverage support acceptance against the goal.'
# Or send an actual defect back to the producer, under the existing contract:
python3 "$PB/scripts/pb_workflow.py" decide --run "$RUN" --decision repair \
  --reason 'Describe the defect, witness and expected correction.'
# Or stop with an unresolved owner decision:
python3 "$PB/scripts/pb_workflow.py" decide --run "$RUN" --decision owner \
  --reason 'Name the conflicting constraints and the decision only the owner can supply.'
```

For a within-goal requirements correction, use `revise --run "$RUN" --reason 'witness and correction'`.
It binds a new immutable requirements revision, then requires authoring and fresh challenge again;
changed candidates require a new consistency review. It refuses once implementation is admitted.
A consistency defect requiring new owner authority remains an actionable blocker; the front door
does not automatically change the goal or hide the contradiction. Start a new bounded change
when the owner materially changes the goal. For advanced revisions use immutable contract revisions
and the existing helpers described in [WORKSPACE.md](../WORKSPACE.md).

`admit --run "$RUN"` is the explicit implementation admission attempt. It records actual refusal
receipts separately from unchanged authority state. A missing consistency record can be recovered by
`continue` only from a retained qualifying accepted consistency task. A merely clean gate or a review
of another purpose does not suffice. Work that has never earned the prerequisite needs a fresh
qualifying review and coordinator acceptance first. A later candidate does not invalidate continuation
of an already admitted task: A6.4 remains authoritative.

Reviewers receive a fresh attempt and instructions to form an initial judgment from authority, code
and checks before reading producer summaries. Reports should say what they saw and when. Diagnostics
remain accessible. This ordering is instructed, not a mechanically enforced information barrier, and
fresh context does not establish statistical independence.

## Resume, interruption and delivery

Once a delivery is sealed, `status --run "$RUN"` returns `action: complete` and an `inspect`
object — these are **fields of that JSON**, not files to guess at:

```bash
python3 "$PB/scripts/pb_workflow.py" status --run "$RUN"
# {"action": "complete",
#  "delivery": ".../runs/first/delivery",
#  "inspect": {"patch": ".../delivery/change.patch",
#              "handoff": ".../delivery/handoff.json",
#              "manifest": ".../delivery/manifest.json",
#              "apply": "git -C <project> apply .../delivery/change.patch"},
#  "next": null}
```

Everything is under the run's `delivery/` directory. Raw runtime homes contain credentials and are
never part of it, but inspect what you are about to share regardless.


A fresh coordinator reads the run's `CONTINUE.md` — written by `start` into the run root — then runs `status`. It needs no preceding chat.

`CONTINUE.md` is the supervised workflow's own note and is the one you want. The `HANDOVER.md` described in [WORKSPACE.md](../WORKSPACE.md) belongs to the inherited checkpoint mechanism, is optional continuity only, and never overrides live state.
A terminal-less attempt or unreconciled launch reservation is a blocker: inspect process liveness,
terminal evidence and session usage before deciding recovery. Do not delete evidence or buy another
trajectory to get a clean result. SIGKILL-safe finalization is not demonstrated. See
[WORKSPACE.md](../WORKSPACE.md) for abnormal lifecycle diagnosis.

Once tasks are accepted, write a final report explaining what changed and why, reviewed checks,
unresolved issues, manual interventions, and actual reviewer visibility. Retain it before sealing:

```bash
python3 "$PB/scripts/pb_workflow.py" finish --run "$RUN" \
  --report /absolute/path/coordinator-final.md --report-source direct
```

Use `--outcome blocked` to seal an actionable blocker and an explicitly unaccepted patch before all tasks complete. Use `--into /new/external/directory` to preserve a fresh package after interrupted sealing; incomplete prior directories remain untouched.

Use `--report-source relayed` when someone copied a report from a final message. Either remains a
reported judgment. Delivery includes a binary-capable patch against the recorded baseline (including
untracked new project files), current commit identity, acceptance/binding evidence, project-check
receipt, usage accounting and file digests. Project checks run again at finish. The command refuses to
overwrite a delivery. Keep the run and external runtime paths named in `handoff.json` for continuation;
there is no automatic cleanup. Inspect artifacts for sensitive data before sharing. Raw runtime homes
contain credentials and must never be published.

Deleting a run loses its contracts, attempts and implementation acceptance. Keep committed `specs/`
authority alongside code. A copied delivery is not a new durable L4 implementation-binding record;
[the existing gap](architecture/proofbound/freeze-and-binding.md#a66-execution-binding-only--the-durability-limitation-stated)
remains. Missing evidence must be reported as unavailable.

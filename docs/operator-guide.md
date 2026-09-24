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
`--worker-profile` (default `deepseek-v4-flash-high`) and `--deadline-seconds` (default 900) are
fixed for the run; see [worker profiles](architecture/proofbound/worker-profiles.md).
The same goal/change invocation returns the existing run; a conflicting invocation refuses.
An interrupted initialization is retained and diagnosed, never silently overwritten.

`doctor` reports Python, installed executor/version, the selected worker profile, its credential
(presence only) or local endpoint (reachability only), platform and boundary availability. It
checks executable identity against the historically qualified OpenCode build. It does not contact a provider or establish that a credential is valid. It does not
qualify the new goal-to-change workflow. GPT-6 is the requested Codex coordinator configuration;
configure it explicitly in Codex, never substitute a model silently.

### A project that needs its own toolchain

The worker boundary executes system binaries, the interpreter and the run's own runtime, so a
project check that needs, say, a pinned Node under your home cannot run inside it. Declare the
toolchain at `start`:

```bash
"$NODE/bin/npm" ci                       # in the project, before start; nothing installs later
python3 "$PB/scripts/pb_workflow.py" start --project "$PROJECT" --change CH-001 \
  --goal-file goal.md --check 'npm run check' --toolchain "$NODE"
```

What each step does:
- **`start`** copies the distribution's `node`, `npm` and `npx` into the run. It records their
  versions and digests, the lockfile, the dependency fields of `package.json` and the installed
  `node_modules`. It refuses the following, before creating anything:
  - dependencies that are not installed;
  - a `.node-version` mismatch;
  - symlinks that leave the copied files.
- **Authorization** runs `--check` inside the worker boundary, with the worker's environment.
  `status` then reports `project_tooling`: `verified: true` only if that check passed. Provider
  readiness says nothing about project tooling.
- **Inside the boundary** the worker gets the prepared copy first on its `PATH` and offline `npm`.
  The dependencies in `node_modules` can execute, and nothing else in the project can. The worker
  cannot write, rename or relink the prepared copy or `node_modules`.
- **Every launch, and the acceptance check,** is refused if any recorded digest changed, including
  a worker's edit to the dependency declarations. Nothing reinstalls: a dependency change needs its
  own adjudication and a newly prepared run.
- **`verify-delivery`** runs `npm ci` in its fresh checkout with the declared toolchain, but only
  while that toolchain still holds the prepared bytes.

Project checks already execute project code. A declared toolchain makes prepared tooling available;
it does not make dependency code trusted. The worker profile's network and credential rules are
unchanged, and your home stays outside the boundary. A run without `--toolchain` is unchanged.

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
at the dated table the run's profile revision names — `deepseek-2026-09-23` for new runs — not on
provider billing. Verify that price basis before authorizing live spend. During an attempt, the host
also stops it when it exceeds 150 model requests, sees 5 responses in a row end without a finish
reason, or sees finished calls pass the remaining derived limit. The pinned executor bounds none of
these itself. A call in flight when a limit is crossed is still billed, and is unknown until it
finishes. Codex subscription consumption is unavailable unless separately
measured, never zero. Direct calls to lower-level launchers are outside this budget wrapper.

Configuration constructs the macOS worker boundary, probes host and staged home separately, and
stages only the credential the worker profile names. A failed boundary probe blocks configuration.
A local profile is authorized with `authorize-resources --launch-ceiling N --owner-authorization …`
instead: no credential is staged, no money limit applies, and the worker's network is restricted to
loopback, which the probe must observe. The worker sees the project, harness and required
system/interpreter paths. The coordinator runs on the host and is
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
### If the session running `continue` ends

A launch runs under a supervisor that the run owns, not under your shell. If the calling session
ends, a command times out or a connection drops, the launch stays supervised: containment, the
deadline, teardown and accounting all carry on without you. Then:

```bash
python3 "$PB/scripts/pb_workflow.py" status --run "$RUN"
```

- **`running`.** Run `continue`. It waits for the launch in progress and starts nothing new.
- **`blocked`, naming `recover`.** The supervisor itself was lost: it was killed, or the host
  restarted. Run:

  ```bash
  python3 "$PB/scripts/pb_workflow.py" recover --run "$RUN"            # read-only diagnosis
  python3 "$PB/scripts/pb_workflow.py" recover --run "$RUN" --apply    # the one change it names
  ```

  `--apply` does one of two things:
  - **The worker is still running.** It resumes supervision under the recorded deadline and
    containment.
  - **The attempt has ended.** It records the attempt from its reservation and terminal record.

  Run it again and it reports `clear`. It never launches, retries or accepts. An attempt whose
  outcome is unknown stays unknown, and the run stays blocked.
- **`recover` reports `contradictory` or `unknown`.** Stop: nothing was changed. Preserve the run
  and ask the owner.

Never edit run JSON, delete evidence, or restart a worker by hand. After a host restart the worker
is gone with the host, and `recover` records what it left. See [WORKSPACE.md](../WORKSPACE.md) for
deeper lifecycle diagnosis.

Once tasks are accepted, write a final report explaining what changed and why, reviewed checks,
unresolved issues, manual interventions, and actual reviewer visibility. Retain it before sealing:

```bash
python3 "$PB/scripts/pb_workflow.py" finish --run "$RUN" \
  --report /absolute/path/coordinator-final.md --report-source direct
```

Then check the delivery the way a reviewer would receive it: apply it to a fresh checkout of the
recorded baseline and rerun the checks.

```bash
python3 "$PB/scripts/pb_workflow.py" verify-delivery --delivery "$RUN/delivery" \
  --into /absolute/new/directory [--outcome-check 'python3 /path/check.py {checkout}']
```

It reads only the delivery directory, so it also works on a copy. It refuses to apply a delivery
whose files no longer match its manifest. It re-derives usage and derived cost from the retained
per-call rows, and touches neither the project nor the run.

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

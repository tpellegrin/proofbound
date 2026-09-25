# BorrowDesk migration backup: execution proposal — 2026-09-24

**Status: proposed; not authorized; nothing run.** This is one bounded supervised run of Proofbound
on BorrowDesk, its second application change. It is a new change and a new run. It resumes nothing
from BD-HOLDS-1 and reuses none of that run's allowances. The preparation is in
[borrowdesk-migration-backup-preparation-2026-09-24.md](borrowdesk-migration-backup-preparation-2026-09-24.md).
A successful run would show usefulness on one more purpose-built task. It would not show reliability
in general, independent adoption, or an advantage over direct coding.

## Target

| | |
|---|---|
| Repository | `https://github.com/tpellegrin/proofbound-lending-lab` |
| Baseline | `4a0c622244efb7589fc6d6566cd3c2e3b8d3e8d8`, tree `8a0e4bf9…`: holds, explicit migration, and the review follow-up |
| Project | the isolated, persistent clone `~/Developer/Personal/proofbound-lending-lab-bd-migration-backup-1`. It is clean at the baseline, with dependencies from `npm ci` under the pinned Node. Its only ignored files are `node_modules/`, `dist/` and `dist-test/` |
| Change id | `BD-MIGRATION-BACKUP-1`, run `first` |
| Goal | the owner's text, verbatim, in `~/proofbound-evidence/borrowdesk-migration-backup-1/goal.md` (sha256 `aa30a9e9…`). It includes the existing guarantees to preserve and the exclusions. No requirement is pre-accepted |
| Permitted scope | `src/`, `test/`, `docs/behavior-v0.md`, the README and `specs/`. No dependency change |
| Baseline check | `npm run check`: 67 of 67 on the host, and 67 of 67 inside the declared boundary at the rehearsal |
| Fixtures | three v0 databases built only with the seed's public CLI (`63da90eb`); `SHA256SUMS` digest `c58067f6…` |

## Frozen configuration

| | Identity |
|---|---|
| Proofbound | execution code at commit `b224c25`, scripts tree `b3dab12e03ce72124ef7c41d43c9084f0b0aa8f4`. Any later commit changes documentation only. Before `start`, and before each `continue`, the coordinator checks that `git rev-parse HEAD:scripts` is still `b3dab12e…` |
| Worker | `deepseek-v4-flash-high`, revision `2026-09-24`, settings digest `6af2663d…`, the same as BD-HOLDS-1. It requests `deepseek-v4-flash`, which the provider documents as served by V4.1 Flash since 2026-09-10. The served model is not observed |
| Executor | OpenCode 1.18.29, sha256 `2f24593f…`, at `~/.proofbound/executors/opencode-1.18.29-darwin-arm64/opencode` |
| Interpreter | Python 3.14.7, `/opt/homebrew/bin/python3.14`. BD-HOLDS-1 used 3.10.14 on another host. Both are in the supported range |
| Project toolchain | Node v24.19.0 and npm 11.17.0 from `~/.local/toolchains/node-v24.19.0-darwin-arm64`, the official tarball (sha256 `8294b7aa…`); toolchain identity `b8fee4c5…`; lockfile `e3a5d1e5…` |
| Price basis | `deepseek-2026-09-23` |
| Coordinator host | this Mac: macOS 27.0, arm64 |
| Coordinator | this interactive Claude Code session. Requested `claude-code/opus`; self-reported Opus 5.5 (`claude-opus-5-5`), from its own system context; observed: not exposed by the host. The three are recorded apart with `pb_workflow.py coordinator` |

## Commands

```bash
PB=/Users/thiago/Developer/Personal/proofbound
PROJECT=/Users/thiago/Developer/Personal/proofbound-lending-lab-bd-migration-backup-1
RUN="$PROJECT/DeepSeekAndDestroy/plans/BD-MIGRATION-BACKUP-1/runs/first"
PY=/opt/homebrew/bin/python3.14
EVID=~/proofbound-evidence/borrowdesk-migration-backup-1

test "$(git -C "$PB" rev-parse HEAD:scripts)" = b3dab12e03ce72124ef7c41d43c9084f0b0aa8f4
$PY "$PB/scripts/pb_workflow.py" start --project "$PROJECT" --change BD-MIGRATION-BACKUP-1 \
  --goal-file "$EVID/goal.md" --check 'npm run check' \
  --toolchain ~/.local/toolchains/node-v24.19.0-darwin-arm64 \
  --executor ~/.proofbound/executors/opencode-1.18.29-darwin-arm64/opencode \
  --deadline-seconds 900
$PY "$PB/scripts/pb_workflow.py" coordinator --run "$RUN" --requested claude-code/opus \
  --self-reported 'Opus 5.5 (claude-opus-5-5), from its system context'
$PY "$PB/scripts/pb_workflow.py" authorize-spending --run "$RUN" \
  --aggregate-limit 0.55 --reserve 0.05 --launch-ceiling 11 \
  --owner-authorization '<the owner authorization of this proposal, by commit and digest>'
$PY "$PB/scripts/pb_workflow.py" status --run "$RUN"   # project_tooling.verified must be true
$PY "$PB/scripts/pb_workflow.py" continue --run "$RUN" # then decide / continue, per status
```

Authorization runs the project check inside the boundary before it stages the credential. If
`status` does not report `project_tooling.verified: true`, the run stops before any launch.

## Launches, money and time

| Limit | Value |
|---|---|
| Launch ceiling | **11** = a base sequence of 5 (`spec-author`, a `spec-reflector` challenge, an aggregate-consistency `spec-reflector`, `implementer`, `reviewer`) + one implementation repair of 2 (`fixer`, `reviewer`) + one requirements revision of 3 (`spec-author`, challenge, consistency) + 1 slot for a launch that fails before reaching the executor |
| Repair allowance | one repair per producer task (the policy default). No second repair |
| Per-attempt deadline | 900 s, with the host's teardown margin. No automatic retry |
| Aggregate limit | **$0.55 derived**, priced at `deepseek-2026-09-23` |
| Reserve | **$0.05, included in the $0.55, not additional** |

**How the reserve works.**
- **Admission.** A launch is admitted only while derived spend so far plus $0.05 is at most $0.55.
  So no launch starts once derived spend exceeds $0.50.
- **Who can use it.** Only an attempt that was already admitted, whose calls take the total from at
  most $0.50 to at most $0.55. It can never admit a launch, a retry, a repair or a coordinator
  session.
- **Containment.** The host stops an attempt when its finished calls take the derived total past
  $0.55, at 150 model requests, or after 5 consecutive responses without a finish reason.

**Total maximum: $0.55 derived, with one stated exception.** A call can finish within the watch's
0.5-second interval, or still be in flight when containment stops the attempt. Such calls are billed,
and can take the total past $0.55. The profile sets no per-call output limit, so Proofbound cannot
bound that overshoot. For scale, BD-HOLDS-1 used 9 launches and $0.179719 derived.

**Derived is not billing.** Derived cost prices measured usage at the dated table. DeepSeek's
billing is not observed.

## Metered participants

| Participant | Metered by | What Proofbound records |
|---|---|---|
| DeepSeek worker, through OpenCode | the provider's API bill | derived cost from per-call usage rows; the bill is not observed |
| This Claude Code coordinator session | the owner's Anthropic plan or account | **nothing: unavailable, not zero**. No other coordinator session, subagent or cloud session is started |
| GitHub Actions | only if the owner pushes | not part of the run |

`npm ci` in `verify-delivery` contacts the npm registry. The registry does not charge for this, and
the retained output does not show whether a request was made. **Unavailable:** provider billing, the
served model identity, this session's usage, and a supported display of derived spend while launches
proceed. That display is a recorded need, and the coordinator reads spend read-only as BD-HOLDS-1
did.

## Stop rules

The run stops, and the coordinator reports, when:
1. **A refusal.** Any launch is refused, or a slot is left unresolved. The coordinator diagnoses
   with `status` and `recover`, and does not relaunch outside the ceiling. The frozen harness is not
   changed during the run.
2. **The limits.** The ceiling or the money limit is reached. No further spend is requested
   mid-run.
3. **A contained attempt.** An attempt is stopped by containment or its deadline without a usable
   result.
4. **A second repair.** A second repair of the same producer would be needed.
5. **A dependency change.** Any change to the dependency declarations would be needed.
6. **An owner decision.** The requirements expose a material, owner-visible choice the goal does not
   settle. The run pauses without launching until the owner answers.
7. **An unsafe mechanism.** The accepted requirements cannot keep writers out between the copy and
   the schema change, and cannot detect a change made there (preparation, P6). That is a blocking
   challenge finding, not an adjudication in the worker's favour.
8. **Acceptance cannot be bound.** The acceptance script cannot be bound without weakening a
   scenario in `acceptance/scenarios.md`.
9. **Failed verification.** `verify-delivery` or the bound acceptance script fails. The delivery is
   then not claimed as verified.

## The owner decision, requested now

The goal says to define interruption behavior and to tell a completed backup from a partial
artifact. The acceptance plan assumes one answer, and it is the owner's to give:

- **A (recommended).** A file at the requested `--backup` path is only ever a completed, verified
  backup. Partial work exists only under a documented temporary name, and handled failures remove
  it. An interruption can leave that temporary file, never a partial file at the requested path.
- **B.** A partial file may be left at the requested path after a failure or interruption. The
  documentation tells the user how to recognize it.

The run starts only with A or B recorded. With B, scenarios C, D, G4 and H change their
expectation on "no file at the destination", and the change is recorded before binding.

**Delegated to adjudication within the goal:**
- the backup mechanism;
- the output fields;
- the exit and error codes, including "backup created, migration failed";
- handling of the destination's parent directory and relative paths;
- `fsync` of the backup and its directory before the commit;
- the bounded wait, where reusing the existing 5-second `busy_timeout` is the default.

The coordinator settles these against the goal, the existing guarantees and the preparation's
constraints, and records each with its reason.

## Acceptance

- **The public scenarios** are `acceptance/scenarios.md` (sha256 `57c5843f…`): preservation and
  usability, unchanged plain `migrate`, ten destination collisions, backup failure, migration
  failure after a backup, repeated invocation, concurrency (competing migrations, v0 writers, a
  held lock) and an interruption smoke check. Success is never inferred from existence, a hash or
  `integrity_check`: `STATE` equality and the seed operating on a copy are required.
- **The measurements** are `acceptance/state.mjs` (sha256 `59786361…`). They were self-checked:
  serialized copies match, and a one-timestamp tamper is detected.
- **The script** is written after the requirements are accepted and before the implementation
  launch. Its digest is recorded then. It is public, not held out: the worker authors the
  requirements it binds to.

## Delivery and retention

`finish`, then `verify-delivery --outcome-check` with the bound acceptance script, into a new
directory. The sealed delivery, the verification result, the acceptance script and its results,
the status snapshots and the coordinator's report are copied into
`~/proofbound-evidence/borrowdesk-migration-backup-1/run/`, with a `SHA256SUMS`. No runtime home
or credential is copied. The private `README.md` separates what those files can verify from what
needs this host's toolchain path. Nothing is merged, pushed or deployed.

## The authorization requested

> I authorize one Proofbound run, `BD-MIGRATION-BACKUP-1` run `first`, on BorrowDesk `4a0c622`, as
> proposed in `docs/architecture/proofbound/evidence/borrowdesk-migration-backup-proposal-2026-09-24.md`
> at Proofbound commit `<commit>` (sha256 `<digest>`). The limits are 11 launches and $0.55 derived
> worker cost, $0.05 reserve included, with 900 s per attempt and one repair per producer. The
> worker is `deepseek-v4-flash-high` revision `2026-09-24`, coordinated by this Claude Code
> session. Destination contract: **A** / **B**.

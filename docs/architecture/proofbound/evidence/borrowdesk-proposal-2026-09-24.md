# BorrowDesk maintenance holds: execution proposal — 2026-09-24

**Status: proposed; not authorized; nothing run.** This is one bounded supervised-alpha run of
Proofbound on BorrowDesk. The preparation is in
[borrowdesk-preparation-2026-09-24.md](borrowdesk-preparation-2026-09-24.md), and the environment
change it needed is in [project-toolchain-2026-09-24.md](project-toolchain-2026-09-24.md). A
successful run would show usefulness on this one purpose-built task. It would not show independent
production adoption, or superiority over direct coding.

## Target

| | |
|---|---|
| Repository | `https://github.com/tpellegrin/proofbound-lending-lab`; remote `main` = seed |
| Baseline | `63da90eb1ff07c80f73932bf609f83fb780968d8` |
| Project | the isolated clone `../proofbound-lending-lab-maintenance-holds`: clean at the seed. Its dependencies were installed with `npm ci` under Node 24.19.0, and its only other ignored files are the baseline check's build output (`dist/`, `dist-test/`) |
| Left untouched | `../proofbound-lending-lab`; the v0 fixture (untouched copy, sha256 `4fe328e1397c565160a3a9ac046e8f6c994aa32c80c9f2795b8ca63582de7d61`); the logical snapshot |
| Change id | `BD-HOLDS-1` |
| Goal | the owner's constraints, verbatim, in `~/proofbound-evidence/borrowdesk-maintenance-holds-prep/goal.md` (sha256 `3dff6bc17f7a3ea201d4847917052dd278451dc75e2992dfa0866d7eb14a81f6`). It holds the holds and migration constraints, the exclusions, and the owner's instruction to keep the task dependency-preserving. No requirement is pre-accepted |
| Permitted scope | the application and its tests (`src/`, `test/`), `docs/behavior-v0.md` and the README, as `AGENTS.md` requires. Proofbound's requirement artifacts (`specs/`) are part of the delivery. No dependency change |
| Baseline checks | `npm run check`: 39 of 39 tests, both on the host and inside the declared boundary |

## Frozen configuration

| | Identity |
|---|---|
| Proofbound | commit `8e71ff4ebea0b72a7462b575b8a2f3409839da81`, scripts tree `8e0382ab64a7e4e9badc071f830cff755483f1f6`. Any later commit changes documentation only; before `start` and before each `continue`, the coordinator checks that `git rev-parse HEAD:scripts` is still `8e0382ab…` |
| Worker | `deepseek-v4-flash-high`, revision `2026-09-24`, settings digest `6af2663d197d93222b193fbb69af24509ebbaaba5834f25852c62ce0b3b6823a`. It requests `deepseek-v4-flash`, which the provider documents as routed to V4.1 Flash since 2026-09-10. The served model is not observed |
| Executor | OpenCode 1.18.29, sha256 `2f24593f1b8e578d0b7ed7ca399440d4b6c125330eece20a69ad8d380190d669` (the CSV first use's executor) |
| Interpreter | Python 3.10.14, `/opt/homebrew/bin/python3.10` |
| Project toolchain | Node v24.19.0 and npm 11.17.0 from `~/.nvm/versions/node/v24.19.0`, toolchain identity `734835bf3c95aafe72f14cdf010a32023b94dc9b9319eed72b5f94957373ca5a`; lockfile `e3a5d1e52fddaee48a73d6a1c7e41e5a4eb86c0c7e5fe5bea3ac7da8e7526431` |
| Price basis | `deepseek-2026-09-23` |
| Coordinator | this interactive Claude Code session. Requested `claude-code/opus`. Self-reported: Opus 5.5 (`claude-opus-5-5`), from its own system context. Observed: not exposed by the host. The three are recorded apart with `pb_workflow.py coordinator` |

## Commands

```bash
PB=/Users/thiago/Projects/foundations/proofbound
PROJECT=/Users/thiago/Projects/foundations/proofbound-lending-lab-maintenance-holds
RUN="$PROJECT/DeepSeekAndDestroy/plans/BD-HOLDS-1/runs/first"
PY=/opt/homebrew/bin/python3.10
EVID=~/proofbound-evidence/borrowdesk-maintenance-holds-prep

$PY "$PB/scripts/pb_workflow.py" start --project "$PROJECT" --change BD-HOLDS-1 \
  --goal-file "$EVID/goal.md" --check 'npm run check' \
  --toolchain /Users/thiago/.nvm/versions/node/v24.19.0 \
  --executor /Users/thiago/.nvm/versions/node/v22.13.1/lib/node_modules/opencode-ai/bin/opencode.exe \
  --deadline-seconds 900
$PY "$PB/scripts/pb_workflow.py" coordinator --run "$RUN" --requested claude-code/opus \
  --self-reported 'Opus 5.5 (claude-opus-5-5), from its system context'
$PY "$PB/scripts/pb_workflow.py" authorize-spending --run "$RUN" \
  --aggregate-limit 0.55 --reserve 0.05 --launch-ceiling 11 \
  --owner-authorization '<the owner authorization of this proposal, by commit and digest>'
$PY "$PB/scripts/pb_workflow.py" status --run "$RUN"   # project_tooling.verified must be true
$PY "$PB/scripts/pb_workflow.py" continue --run "$RUN" # then decide / continue, per status
```

Authorization runs the project check inside the boundary, before it stages the credential.
`status` must then report `project_tooling.verified: true`, before any `continue`. If it does not,
the run stops before any launch.

## Launches, money and time

| Limit | Value |
|---|---|
| Launch ceiling | **11**: the base sequence of 5 (`spec-author`, `spec-reflector` challenge, aggregate consistency `spec-reflector`, `implementer`, `reviewer`), one implementation repair of 2 (`fixer`, `reviewer`), one requirements revision of 3 (`spec-author`, challenge, consistency) and 1 slot for a launch that fails before reaching the executor |
| Repair allowance | one repair per producer task (the policy default), within the ceiling. No second repair |
| Per-attempt deadline | 900 s, with the host's teardown margin. No automatic retry |
| Aggregate limit | **$0.55 derived**, priced at `deepseek-2026-09-23` |
| Reserve | **$0.05, included in the $0.55, not additional** |

**How the reserve works.**
- **Admission.** A launch is admitted only while derived spend so far plus $0.05 is at most $0.55.
  No launch starts once derived spend exceeds $0.50.
- **Who can use it.** Only an attempt already admitted, whose calls can take the total from at
  most $0.50 up to $0.55. Nothing can use the reserve to admit a launch, a retry, a repair or a
  coordinator session. It is not a separate fund.
- **Containment.** During an attempt, the host stops the attempt when its finished calls take the
  derived total past $0.55. It also stops at 150 model requests, or at 5 consecutive responses
  without a finish reason.

**Total maximum: $0.55 derived**, with one stated exception. A call that finishes within the
watch's 0.5-second interval, or is in flight when containment stops an attempt, is still billed.
Such calls can take the derived total above $0.55. The profile sets no per-call output limit, so
Proofbound cannot bound that overshoot. For scale, the whole CSV first use (5 launches) derived
$0.060347.

**Derived is not billing.** Derived cost prices measured usage at the dated table. DeepSeek's
billing is not observed.

## Stop rules

The run stops, and the coordinator reports, when:
1. **A refusal.** Any launch is refused (preflight, toolchain or admission), or a slot is left
   unresolved. The coordinator diagnoses with `status` and `recover` and does not relaunch outside
   the ceiling. A material harness defect becomes a recorded blocker; the frozen harness is not
   changed during the run.
2. **The limits.** The ceiling or the money limit is reached. No further spend is requested
   mid-run.
3. **A contained attempt.** An attempt is stopped by containment or its deadline, and its outcome
   is not a usable result.
4. **A second repair.** A second repair of the same producer would be needed.
5. **A dependency change.** Any change to the dependency declarations would be needed. Launches
   refuse it anyway, and it needs its own adjudication.
6. **An owner decision.** The requirements expose a decision with material user-visible
   consequences that the owner's goal does not settle (below). The run pauses without launching
   until the owner answers.
7. **A defect in the owner's goal.** A challenge substantiates one.
8. **Failed verification.** `verify-delivery` fails. The delivery is then not claimed as verified.

## Owner decisions still open

The preparation listed nine user-visible decisions. Workers propose answers in the requirements,
the challenge tests them, and the coordinator adjudicates them against the goal. Only a material
case goes to the owner, with the exact question and its witness.

- **Delegated to adjudication.** Command names (1), the migration command's name and output (6),
  reporting of idempotent repeats (7), a hold timestamp (8) and a held count in the report (9).
  Each is decided within the goal and recorded with its reason.
- **Likely escalations.** The held-checkout error code (2), v0's item `status` field (3), `init`
  on a v0 database (4), and ordinary commands on an unmigrated database (5). These touch the v0
  compatibility surface.
  - The goal allows only the checkout restriction and documented additive output fields.
  - An answer that changes an existing code, output value or exit status goes to the owner.
  - (3) is the most likely. v0 reports a held but unborrowed item as `status: "available"`, while
    the goal says such an item is not available.

## Acceptance and delivery

**The public acceptance script.**
- **Written by the coordinator**, from the accepted requirements and the owner's list of checks,
  before the implementer launches. It is kept outside the project, so the worker cannot change
  it, and frozen by sha256 in a receipt.
- **It exercises the CLI** against a fresh copy of the untouched v0 fixture:
  - holds on available and borrowed items;
  - checkout rejected while held;
  - return while held, with the hold kept;
  - hold removal while a loan stays active;
  - idempotent repeats and unknown ids;
  - listing and dashboard status that agree;
  - explicit migration, and a repeated migration;
  - preserved records, and the return of v0's active loans;
  - rejection of missing, foreign, corrupt and unsupported databases, without replacement;
  - one winner among competing checkouts.
- **It is public evidence, not a held-out benchmark.** Its content follows from requirements the
  worker authored.

**Delivery.**
- **`finish`** seals the patch, the handoff and the manifest.
- **`verify-delivery`** runs from the delivery on a fresh checkout of `63da90eb`, into a new
  directory:
  - `npm ci` with the declared toolchain, which must still hold its prepared bytes;
  - `npm run check`;
  - the acceptance script, as `--outcome-check`.
- **The patch stays inspectable.** Nothing is merged, deployed or pushed without the owner's
  authorization.

## What is recorded, and what stays unavailable

**Recorded:**
- whether the requested behaviour was delivered;
- regressions and defects found;
- worker repairs and coordinator interventions;
- setup friction and owner decisions;
- elapsed time;
- worker usage and derived cost;
- any step that needed an undocumented command or implementation knowledge.

| Participant | Allowance | Measured |
|---|---|---|
| Worker (DeepSeek, via OpenCode) | $0.55 derived, 11 launches, as above | derived from measured usage; provider billing unavailable |
| This coordinator session | no separate allowance. It is metered by its host under the owner's plan, and Proofbound enforces nothing on it | **unavailable, not zero** |
| Additional coordinator sessions, headless or native subagents | **none** | — |

**Unavailable:**
- provider billing;
- the served model's identity;
- this session's usage and cost;
- the owner's effort.

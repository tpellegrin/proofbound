# Draft-PR handoff — 2026-09-25

**Implemented, and tested locally with no GitHub mutation. Nothing published.** A verified delivery
can now become a GitHub draft pull request that the owner reviews:
- `prepare-pr` makes the plan and a preview;
- `publish-pr` needs the owner's authorization naming the plan's digest;
- `pr-status` is read-only.

No provider request, no push and no PR creation happened during this milestone. The only live
GitHub contact was read-only inspection. The operator path is in
[the operator guide](../../../operator-guide.md#from-a-verified-delivery-to-a-draft-pull-request).

## Why

BorrowDesk showed two gaps:
- **Publication was manual.** Publishing the verified candidate took hand-run Git and GitHub
  commands (BD-MIGRATION-BACKUP-1's PR #3 was built by hand from the sealed patch).
- **Reports blurred what passed with what was known to be wrong.** A run could pass its checks
  while carrying known defects or owner-approved exceptions to the goal.

The handoff keeps those apart. It records facts, and relays the coordinator's judgments
explicitly (`P1`).

## Design

**Modules.** Three focused modules; `pb_workflow.py` only parses arguments.

| Module | Holds |
|---|---|
| `scripts/_pr_candidate.py` | delivery and verification binding, the candidate commit, Git tree identity |
| `scripts/_pr_github.py` | the only remote code: read-only `gh api` and `git ls-remote`, one non-forced push, one `gh pr create --draft` |
| `scripts/_pr_handoff.py` | plan, body and preview rendering, authorization, publication record and reconciliation, status |

**Verification is bound by identity.**
- `verify-delivery` now applies the patch with `--index` and records the candidate **Git tree**
  before any check runs, then what the checks left in tracked or unignored content.
- It also records the verifier's Proofbound commit and scripts tree, the manifest digest and the
  time.
- Preparation rebuilds the candidate from the sealed patch in a new isolated clone, and requires
  the same tree. A tree covers content, modes, deletions, binaries and symlinks together.
- Older verifications lack this identity and are refused. The fix is to verify again.

**The candidate commit is deterministic.** It is dated at the verification, and uses the
repository's human identity through environment variables. Re-preparing the real delivery gave the
same commit, `035ddb97…`.

**Every write needs authority.**
- The plan is immutable, and its digest is what the owner authorizes.
- A changed body, candidate or destination is a new plan in a new directory.
- `publication.json` is a small mutable record kept beside the immutable plan and the delivery,
  never inside the delivery.

**Not used: `gh pr create --dry-run`.** GitHub documents that it may push.

## Tests

`tests/test_pr_handoff.py` has 18 tests. They use real Git: a project, a sealed delivery whose patch
modifies, changes a mode, deletes, adds binaries, a symlink and a file named with shell
metacharacters, a real `verify-delivery`, and a local bare remote. GitHub is a recording stand-in
`gh` that serves a recorded state and fails on any command it does not know. A logging `git` shim
records every Git call. The temporary root's own name contains spaces and `$(…)`.

| Removed from the code | Caught by |
|---|---|
| the base check before publishing | the moved-base test |
| reconciliation before creating | 3 tests (lost response, retry, external change) |
| the plan digest in the authorization | the publication test |
| the tree comparison in the build | the tampered-evidence test |
| the account check | the account test |
| the private-path guard | the summary test |
| the head filter on check runs | the check-state test, after a misfiled-run case was added |

Every mutation was caught. The head-filter mutation survived at first, because the stand-in serves
runs per commit. A run reported for another commit was added to the fixture.

**The canonical suite** at `d654700`: 1,479 tests, OK, 1 skipped, on macOS 27.0 arm64 with Python
3.14.7. The skip is the retained-session round trip, whose session is not on this host. The
suite has not run on Linux at this revision.

## Local rehearsal on the real delivery

The rehearsal used BD-MIGRATION-BACKUP-1's sealed delivery and the coordinator's real review
summary, against a local bare copy of BorrowDesk at the verified baseline, with the recording `gh`.
It is retained privately with its script, `rehearse.sh`.
- **Old verification.** `prepare-pr` with the pre-extension verification was refused: no manifest
  digest, tree or verifier.
- **Fresh verification.** A new `verify-delivery` (Proofbound `be8c419`) passed: 82 of 82, and 311
  of 311 on the frozen acceptance script. The checks left tracked content unchanged. The candidate
  tree `bac23fa9…` is the tree of PR #3's hand-made head, `f2fc8ef`.
- **The flow.**
  - `prepare-pr`: no push, no PR.
  - `publish-pr` without authorization: exit 2, naming the plan digest.
  - `publish-pr` with authorization: one push, of one explicit refspec, and one draft PR.
  - A retry: the same PR, no duplicate.
  - `pr-status`: the head is the verified candidate, and no checks were observed.
- **Commands used.** `gh` received only GET API calls, `config get`, `pr list`, `pr view` and one
  `pr create`.

## Live GitHub, read-only

- **The base-moved refusal fired on real GitHub.** `prepare-pr` against
  `tpellegrin/proofbound-lending-lab` refused, correctly: `main` is now `cb5fa41`, after the owner
  squash-merged PR #3 at 03:21:23Z, not the verified baseline `4a0c622`. That is the refusal
  working against real GitHub.
- **Repository selection.** For `tpellegrin/wellbeing-platform`, the adapter reported
  `visibility: private` and remote `main` at `ef1fbef`, the local clone's HEAD. The clone was not
  modified.
- **Not observed live:** a push, a PR creation, CI association on a real PR, or GitHub's response
  shapes for those.

## Separate readiness finding: wellbeing-platform

This finding is outside this milestone. The project uses **pnpm 9.15.9** (`pnpm-lock.yaml`, no
`package-lock.json`, no `.node-version`), plus a husky `prepare` script.
- **Proofbound refuses it today.** Its declared toolchain records only `node`, `npm` and `npx`, and
  `start --toolchain` refuses a project without `package-lock.json`, as observed with
  `_toolchain.check`.
- **Verification assumes npm.** `verify-delivery` prepares dependencies with `npm ci`.
- **Untested in the worker boundary:** pnpm's store location and execution rules.

Supporting it is a separate change. No application work was done.

## Limits

- **The pipeline establishes identity, not quality.** A published PR holds the verified bytes. Its
  behaviour, architecture and worth are the owner's review.
- **Tested locally only.** Live push and PR creation have not been observed; the stand-in `gh`
  models their responses.
- **A base can move after publication.** `pr-status` reports it; nothing rebases.
- **GitHub only**, through `gh` and Git. Forks, merges and approvals are out of scope.

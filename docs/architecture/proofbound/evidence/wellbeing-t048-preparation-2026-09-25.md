# wellbeing-platform: pnpm readiness and the WB-T048-CONFIG-1 proposal — 2026-09-25

> **Current status: superseded in part, by addition.** The digests in "The proposal" below, and its
> closing line, predate later events. See [Reconciliation](#reconciliation--fresh-coordinator-session-2026-09-25)
> at the end for the current artifacts, the `.proofbound/` workspace root, the housekeeping PR and
> what remains. The earlier text is kept as it was written.

**Prepared, unpaid; nothing launched, nothing published.** This record covers four things:
- Proofbound's pnpm support, which removes the blocker found on 2026-09-25;
- a production-path rehearsal of wellbeing-platform's real checks inside the worker boundary;
- a fresh-checkout install and validation;
- a proposed first application change.

No provider request was made and no remote was written. The private evidence is in
`~/proofbound-evidence/wellbeing-t-048/`.

## Identities

| | |
|---|---|
| Proofbound | `0d9b77d` at the start (= `origin/main`); the pnpm support is `782dc16`, `pr-status`'s event labelling is `6227f83`. The frozen revision is stated below |
| wellbeing-platform | `tpellegrin/wellbeing-platform`, **private**. `main` = `ef1fbef` (T-047's decision record), clean, identical locally and on the remote |
| Declared tooling | Node **20.20.2**, the official darwin-arm64 tarball, checksum matched `SHASUMS256.txt`, as CI pins Node 20 (end-of-life since April 2026; recorded, not changed). pnpm **9.15.9**, the registry tarball, sha512 integrity matched, the version `packageManager` pins |
| Host | macOS 27.0 arm64, Python 3.14.7 |

## The pnpm blocker, closed

- **`start --toolchain <node> --pnpm <pnpm>`.** The pnpm package is copied and recorded by content
  (identity `92088109…` for 9.15.9). A generated `bin/pnpm` runs it with the prepared Node. The
  project's pin must name that version, and pnpm's version management is off.
- **Bound.** The preparation is bound to `pnpm-lock.yaml`, the manifest's installation fields,
  and `.npmrc`, `pnpm-workspace.yaml` and `.pnpmfile.cjs`, present or absent.
- **Refused.** Workspaces, patches, local dependencies and credentials in `.npmrc` are refused
  rather than half-bound. wellbeing-platform uses none of them: one importer, no patches, no
  `.npmrc`.
- **A copy, not a store.** `node_modules` must be a copy of the packages.
  - No symlink may leave the project. pnpm's own links are relative and internal.
  - No file may share an inode with anything outside `node_modules`. The only hard links seen were
    esbuild's own, both inside.
- **Tool caches inside `node_modules`.**
  - Inside the boundary, three tool caches in `node_modules` are writable: `.vite` and
    `.vite-temp` for Vite and Vitest, and `.tmp` for TypeScript build info, where this project's
    tsconfigs put it.
  - The dependency digest leaves them out.
  - The rehearsal found each one: every check that needed them failed when they were denied.
- **The exact guarantee for the caches.** Measured against the real rehearsal's boundary:
  - the only write allowances beside the project are the three cache subpaths;
  - hard-linking an installed file into a cache is refused, as are writing into `.pnpm` through a
    cache symlink, moving `.pnpm` into a cache, and creating a new top-level entry;
  - an installed file was unchanged afterwards.

  One gap was found and closed: a cache could be replaced by a symlink, even one leaving the
  project, without the digest noticing, so a check could have read cache state from outside the
  preparation. A cache that is a symlink, or that holds a symlink leaving the project, is now
  reported before the next launch and refuses acceptance. A regression covers it.
- **Signals.** Inside the boundary, a process may signal processes in the same sandbox, but not
  outside it. Vitest must stop its own workers. This was measured with a child and an outside
  process before it was adopted.
- **Scope.** Both allowances apply only to runs whose record declares pnpm. npm runs keep their
  record shape and boundary rules.
- **Verification.** `verify-delivery` builds a fresh prepared copy that must reproduce the
  recorded identities, installs with `--frozen-lockfile` into a store inside the verification
  directory, and records that as a lockfile-pinned registry fetch, not an offline install.

| Check | Result |
|---|---|
| `tests/test_pnpm_toolchain.py` | 8 tests, macOS sandbox included: preparation, 10 refusals, 5 kinds of drift, verification, the boundary |
| npm compatibility | `tests/test_toolchain.py` unchanged and passing; an npm record carries no pnpm fields |
| Mutations | removing the configuration-file binding, the store-link check, the prepared-pnpm identity check or the pin check each fails a test |

## Rehearsals on the real repository

- **Host baseline** (a clone at `ef1fbef`, frozen install, `HUSKY=0`, as CI with Node 20):
  - `pnpm validate` passes: 61 test files, 321 tests;
  - `pnpm build` passes, with a chunk-size warning, which is a baseline warning and not repaired.
- **Through the production path** (`start --toolchain --pnpm`, then a test-only
  `authorize-spending` with a dummy credential in a fake home, never launched). Three things were
  found and handled:
  1. **The preparation `PATH`.** Dependency install scripts (msw, esbuild) run `node` from `PATH`.
     The documented command now puts the declared Node first. `start` refused the half-installed
     tree.
  2. **Prettier inspects Proofbound's run directory.** `format:check` globs `**/*.json` and reads
     only `.gitignore`, which does not list `DeepSeekAndDestroy/`. The run records failed its
     check. This is a project decision (below), not a Proofbound defect.
  3. **Tool caches and signals**, as above.

  With `/DeepSeekAndDestroy/` ignored (a local, never-pushed rehearsal commit), the
  authorization's in-boundary `pnpm validate` passed in 48 s: `project_tooling.verified: true`. No
  drift afterwards.
- **Fresh-checkout install and validation**, through verification's own functions, with no
  delivery fabricated:
  - a materialized toolchain, and declarations matched before the install;
  - the frozen install took 14 s and was recorded as a registry fetch;
  - `pnpm validate` passed, 61 files and 321 tests; `pnpm build` passed;
  - tracked content was unchanged after the checks.

## The repository, as found

- **Documented direction.** `AGENTS.md`, `docs/implementation/rules.md`, the review checklist,
  context packs per task, and task specs with allowed files and stop signals, driven by
  `docs/implementation/roadmap.md`. It is contract-first: `docs/api/openapi.yaml` leads, `zod`
  schemas mirror it, and `pnpm contract:check` enforces the mirror.
- **Followed in code.** The schemas are strict objects built from shared primitives, a fake backend
  runs behind MSW with conformance tests, and a distribution-context seam exists.
- **Aspiration against current state.** The T-048 spec and the audits written before the contract
  hardening describe `configuration.ts` as an empty scaffold with a `branding` and `pageSections`
  model. The hardened contract (section 6 of its `docs/api/contract.md`) already defines `tenantId`, `theme` (catalogue tokens) and
  `composition` (sections). The spec is stale on that point.
- **CI.** `Validation` runs on pushes to `main` and on pull requests: a frozen install, then
  `pnpm validate`, then `pnpm build`. `Deploy app to GitHub Pages` runs on pushes to `main` and on
  manual dispatch, so a draft PR does not deploy, but a push to `main` does. Both run on GitHub's
  Ubuntu runners, which use the private repository's Actions minutes.

## Task choice

The roadmap's statuses and dependency columns were evaluated mechanically. Four tasks have every
dependency done: T-048, T-054, T-061 and T-067.
- **T-061 is not actually ready.** Its spec also needs T-049.
- **T-054 and T-067** are documentation only.

**Recommended: T-048, reconciled with the hardened contract.** It completes the tenant
configuration document that T-049–T-057 consume, which is useful now. It exercises contract-first
parity, strict public boundaries, catalogue discipline and international rules, and is judged by
deterministic checks and a short walkthrough. Its catalogue decision is already handled by the
spec: provisional values with a "product decision pending" marker.

**Alternative: T-054**, an evidence-backed audit of global-marketplace assumptions. It is lower
risk, but produces no code.

## The proposal

| | |
|---|---|
| Change | `WB-T048-CONFIG-1`, run `first`. The owner goal is `goal.md` (sha256 `db03e97a…`): constraints, permitted files, stop conditions and architecture references, with no pre-accepted requirement |
| Baseline | `origin/main` after the owner's decision on ignoring `/DeepSeekAndDestroy/`, bound at `start`; no other change from `ef1fbef` |
| Project | a persistent clone, `~/Developer/Personal/wellbeing-platform-wb-t048-config-1`, prepared with the command in the operator guide |
| Check | `pnpm validate`; the fresh-checkout acceptance adds `pnpm build` |
| Review criteria | `architecture-review-criteria.md` (sha256 `a96de31b…`), A1–A12, each citing a repository rule, placed in `specs/WB-T048-CONFIG-1/` before the first launch |
| Acceptance | `acceptance/scenarios.md` (sha256 `319f3519…`): compatibility, strictness, international, catalogue, parity, gates. It is bound after the requirements are accepted and frozen before implementation, and it is not held out |
| Worker | `deepseek-v4-flash-high` revision `2026-09-24`, settings `6af2663d…`; OpenCode 1.18.29 `2f24593f…`; Python 3.14.7 |
| Coordinator | this interactive Claude Code session, and only it |
| Launches | at most **11**: 5 base (author, challenge, consistency, implementer, reviewer), one implementation repair of 2, one requirements revision of 3, and 1 slot for a launch that fails before the executor. One repair per producer |
| Deadline | **1,200 s** per attempt. The repository is larger than BorrowDesk, and `pnpm validate` takes about 48 s inside the boundary |
| Money | **$1.00 derived, $0.10 reserve included**. No launch once derived spend exceeds $0.90. BorrowDesk's second run cost $0.058 per launch on average, and this repository gives each worker more to read |
| Metered | DeepSeek (derived only; billing not observed); this Claude Code session (usage unavailable); GitHub Actions minutes on the private repository, for the baseline push to `main` (Validation, plus a Pages deployment of `main`) and for the draft PR (Validation on the merge ref) |
| Stop rules | the BorrowDesk rules, plus: a toolchain or dependency refusal before launch; a harness defect, which becomes a recorded blocker and is not fixed mid-run; any need to leave the permitted files |
| Delivery | `finish`; `verify-delivery` with the bound acceptance script; `prepare-pr` with the coordinator's review summary; the owner reads the preview and plan digest; `publish-pr` on authorization naming that digest; `pr-status` for head-commit checks, with branch-head and merge-ref runs told apart |

Nothing was committed to, pushed to or opened on wellbeing-platform.

## Reconciliation — fresh coordinator session, 2026-09-25

A new Claude Code coordinator session took over preparation. It is the only coordinator, and it
launched nothing and made no provider request. The corrections below are made by addition.

### What the earlier text got wrong, or no longer says

- **Superseded digests.** The proposal table cites the goal as `db03e97a…`, the review criteria as
  `a96de31b…` and the scenarios as `319f3519…`. Those are the first drafts, superseded before this
  record was committed. The files are retained under `-draft-1-superseded` names.
- **"Nothing was … opened on wellbeing-platform."** This was true when written. Afterwards, draft
  PR [#1](https://github.com/tpellegrin/wellbeing-platform/pull/1) was opened: a one-line
  `.gitignore` change, coordinator preparation written by hand, not a worker delivery.
- **The workspace root.** New runs are now created under `.proofbound/`, not `DeepSeekAndDestroy/`
  (below). The baseline decision on "ignoring `/DeepSeekAndDestroy/`" is therefore about
  `/.proofbound/`.

### The retained artifacts, by full digest

All paths are under `~/proofbound-evidence/wellbeing-t-048/`.

| Artifact | File | sha256 | Status |
|---|---|---|---|
| Goal v3 | `goal.md` | `d6eff5699f1b9cadde523b9c39bdbe2bb3487d920a00e06109705c5746082df0` | **current**, proposed for owner confirmation |
| Goal v2 | `goal-v2-superseded.md` | `e9b5615efa00fd626a831c286d274cac9970a8bb09fc9322a9dd014ee4725b73` | superseded by v3 |
| Goal v1 | `goal-draft-1-superseded.md` | `db03e97ac15c88d8543798e2d9761640952d0dc6feecfa1770aeca252db55665` | superseded |
| Review criteria | `architecture-review-criteria.md` | `9faa4f58b6b43f34f50e175c8142aa80881fea43ac9290424874c6486b8c4e77` | **current**, unchanged in this session |
| Review criteria v1 | `architecture-review-criteria-draft-1-superseded.md` | `a96de31b50ba8e9d8341c0c455cf5668fe049a9db484d319156f737e379be921` | superseded |
| Scenarios v3 | `acceptance/scenarios.md` | `2dbb7294a65acabc16e95df0dba4468f1ef9d9bca0a01fb4d121a98c6a6528d6` | **current**, proposed for owner confirmation |
| Scenarios v2 | `acceptance/scenarios-v2-superseded.md` | `e40c7c24c6759c6e719b7ae08a7fcf89d1130f94dd1f71a85eb86bc9b5285967` | superseded by v3 |
| Scenarios v1 | `acceptance/scenarios-draft-1-superseded.md` | `319f3519922760f0a92c63b2099fcf8b403571b7b6b533f056c4a8c611f0227d` | superseded |

No artifact is missing. The executable acceptance script does not exist yet, by design: it is bound
after the requirements are accepted, and before implementation.

### Goal v3: three meanings of "valid"

Goal v2 said validity "means the standard's own rules". It also required reusing `CountryCode` and
`CurrencyCode`, which check syntax only (`^[A-Z]{2}$`, `^[A-Z]{3}$`). Scenarios v2 then expected the
locale `english` to be rejected. Under Node 20.20.2, `Intl.getCanonicalLocales('english')`
accepts it: BCP 47 permits a language subtag of 5 to 8 letters. The application's own conventions
(`docs/api/conventions.md` section 22) require BCP 47 *syntax*, and nothing more. So the goal left three different questions
unseparated:
1. Is the value well-formed?
2. Is it present in the standard's dataset?
3. Does the product support it?

Rejecting `english` would have needed a registry the repository does not have, or a narrower house
profile. Either would be a new policy.

v3 answers each question separately:
- **Locale, country and currency** are checked for well-formedness only.
- **Time zone** is checked for membership. Its conventions section 17.4 requires IANA identifiers, and no
  syntax can decide that. The requirements must choose the dataset and show that the check stays
  deterministic.
- **Product-supported values** stay empty. No new value is approved, and there is no fallback.

Scenarios v3 therefore:
- move `english` and `xx` (locale), `ZZ` (country) and `XYZ` (currency) into a new **I4**. They must
  be *accepted*, so that no worker introduces an unapproved membership list;
- keep every other expectation.

The one intentional compatibility change is unchanged in both versions: a configuration without
`configVersion: '1'` is rejected.

### The workspace root is `.proofbound/`

The coordinator changed Proofbound itself, under the owner's explicit authorization for this narrow
change. `scripts/_workspace.py` now defines both names once, and every site uses it:
- **New runs.** `start`, receipts made without a run, and new adapter shims are created under
  `.proofbound/`.
- **Legacy runs.** A run already under `DeepSeekAndDestroy/` stays usable where it is. `start` for
  that change returns it. A change with a run under both roots is refused as ambiguous.
- **Project derivation, the worker boundary and recovery.** Project-root derivation, worker
  confinement and the contract and inventory refusals recognise both roots. So do compaction
  recovery and re-wake.
- **Scope.** A launch excludes only its own run's root from scope. The gate requires exactly that
  exclusion.
- **Deliveries.** A delivery's patch leaves out both roots.
- **Reinstalling an adapter** over an older install replaces its hooks rather than duplicating them.
- **Worker rules.** `worker/COMMON.md` names both roots. It is 1,997 bytes, within its cap.
- **Unchanged.** Protocol and manifest formats, `dsd_*` names and historical evidence.

New tests are in `tests/test_workspace_root.py`:
- a real `start`-to-`finish` run under `.proofbound/`, with neither root ignored and a stray file
  under the legacy root;
- a legacy run, created by the unchanged `start` logic, continued to delivery without creating
  `.proofbound/`;
- the refusal for a change under both roots, with no file changed;
- recovery and re-wake under both roots;
- adapter reinstallation.

Five deliberate mutations were each caught. Removing the legacy root from the delivery filter was
at first caught only by a unit test, because the end-to-end assertion reused the predicate under
test. The assertion now names both roots literally, and that mutation fails the end-to-end run.

**The canonical suite.**
- A full run on the finished code ran 1,497 tests with 1 skip. It failed only two
  documentation-corpus checks: a stale route figure, and two section references that collided with
  Proofbound's `§` namespace. Both were fixed afterwards.
- The canonical result at the final revision cannot be recorded inside that revision. It is
  retained as `baseline/proofbound-canonical-suite-<revision>.log` in the private evidence
  directory.

### The housekeeping PR, updated

PR [#1](https://github.com/tpellegrin/wellbeing-platform/pull/1) is still a draft, owned by the
owner.
- **The change.** A fast-forward follow-up commit, `00ad4e4`, replaces the proposed
  `/DeepSeekAndDestroy/` entry with `/.proofbound/`. No legacy entry is kept, because neither the
  repository nor the planned clone has ever held a run.
- **Title and description** now describe this final state, as coordinator preparation, not worker
  output.
- **Commit messages.** The first commit, `49dc6b9`, has a body, which the repository's commitlint
  (`body-empty`) rejects. It is left unrewritten, and the PR description says so.
- **Checked on a throwaway clone of `00ad4e4`** with Node 20.20.2, pnpm 9.15.9 and a frozen install.
  An unformatted JSON file was placed under `.proofbound/`:
  - with the branch's `.gitignore`, `pnpm format:check` exits 0;
  - with `main`'s `.gitignore`, it exits 1 and names that file;
  - tracked files were unchanged afterwards.
- **Proofbound's own JSON.** The `specs/<change>/` files are graph, ledger, freezes and consistency
  records. They stay deliberately unignored. All 8 such files from the BorrowDesk runs pass
  Prettier 3.6.2 with this repository's configuration.

**CI.** The push ran only **Validation**, on the `pull_request` event. That is a merge-ref run, not a
branch-head run: Validation runs on pushes only for `main`. Run `36171252225` on head `00ad4e4`
passed. Nothing deployed, because Pages deploys only from `main` or by manual dispatch.

### What remains before a spending request

- **The owner reviews and merges PR #1.** No run starts on the pre-merge branch.
- **After the merge:**
  - record `origin/main` and compare it with `ef1fbef`;
  - create the isolated clone `~/Developer/Personal/wellbeing-platform-wb-t048-config-1`. It does
    not exist yet;
  - install with the recorded Node 20.20.2 and pnpm 9.15.9;
  - take the boundary baseline through `start --toolchain --pnpm` and a no-launch authorization
    rehearsal, under `.proofbound/`;
  - confirm that the tracked tree is unchanged afterwards.
- **The owner confirms goal v3 and scenarios v3**, or chooses otherwise, before their digests are
  frozen into the proposal.

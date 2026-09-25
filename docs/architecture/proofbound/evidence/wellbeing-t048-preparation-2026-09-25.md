# wellbeing-platform: pnpm readiness and the WB-T048-CONFIG-1 proposal — 2026-09-25

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

# BorrowDesk maintenance holds: preparation — 2026-09-24

**Blocked on an owner decision.** The supported worker boundary cannot run BorrowDesk's toolchain.
A throwaway boundary with two added permissions runs the project's full check, so the smallest
sufficient change is demonstrated. It is a Proofbound change, and it has not been made. No run was
started and no provider request was made.

## Target and baseline

- **Repository:** `https://github.com/tpellegrin/proofbound-lending-lab` (BorrowDesk, a
  TypeScript/SQLite lending CLI with an HTML dashboard). Its v0 was built by Opus outside
  Proofbound. It is a purpose-built evaluation application.
- **Baseline:** seed `63da90eb1ff07c80f73932bf609f83fb780968d8`. The remote `main` is the seed, and
  there are no later application changes.
- **Checkouts.**
  - The existing checkout at `../proofbound-lending-lab` is clean at the seed; its only extra
    files are ignored build products and dependencies. It is left untouched.
  - The run will use an isolated clone at `../proofbound-lending-lab-maintenance-holds`, a
    standalone repository whose Git metadata lies inside the worker's writable project.
- **The repository's rules** (`AGENTS.md`):
  - Node 24 (`.node-version`: 24.19.0) and `npm ci`;
  - `npm run check` is the canonical check;
  - lending rules stay in `desk.ts`/`validation.ts`;
  - `docs/behavior-v0.md` is the behaviour contract, updated with any intentional change;
  - existing v0 databases must stay readable.

## Environment and baseline checks

| | |
|---|---|
| Pinned toolchain | Node **24.19.0**, npm **11.17.0** (nvm, `~/.nvm/versions/node/v24.19.0`). The shell default is Node 22.13.1, which does not match |
| Dependencies | `npm ci`: 7 locked packages, 0 vulnerabilities, ~1 s. `better-sqlite3` 13.0.3 (prebuilt `darwin-arm64`, SQLite 3.53.4); TypeScript **7.0.2**, whose `tsc` runs a native binary from `node_modules/@typescript/typescript-darwin-arm64` |
| Baseline `npm run check` on the host | **39 tests, 8 suites, 0 failures**, 4.4 s. No existing failures |
| `pb_workflow.py doctor` | ready, 0 provider requests |
| Sensitive material | none among the 22 tracked files; no credentials or environment reads |

**Populated v0 database.** Built with the seed's public CLI, following the sequence in
`docs/behavior-v0.md`. It is kept privately in
`~/proofbound-evidence/borrowdesk-maintenance-holds-prep/fixture/`:
- **Records:** 4 items (`camera-01` and `microphone-01` available; `drill-01` and `projector-01`
  on loan) and 3 loans (1 returned, 2 and 3 active).
- **Identity:** `user_version` 1, `application_id` `0x426F7244`.
- **Kept:** an untouched read-only copy (sha256 `4fe328e1…`), the command log, and a logical
  snapshot of every row, the pragmas and the schema, taken through a read-only connection.

## The blocker: measured inside the production boundary

These are the production boundary (`_workflow_boundary.prepare`) and the worker's exact
environment. The run and project were throwaway, and a fake home held a dummy key.

| Inside the boundary | Result |
|---|---|
| `node` on the worker `PATH` | not found (exit 127) |
| The pinned Node by absolute path | `execvp … Operation not permitted`: `~/.nvm` is outside the boundary |
| `npm` | unavailable: its CLI is under `~/.nvm` |
| The TypeScript native compiler (`node_modules/@typescript/…/lib/tsc`) | `Operation not permitted`: execution from the project is refused |
| Node staged into the run's `tools/` (probe only) | runs, and loads `better-sqlite3`'s native addon from the project |

The boundary executes only system binaries, the Python interpreter, Homebrew's Cellar/opt/lib, and
the run's runtime and tools. A worker therefore cannot run `tsc`, the tests or `npm run check`.

**The smallest sufficient change, demonstrated on a copy of that boundary:**

| Added to the boundary | `npm run check` inside |
|---|---|
| Read and execute for the pinned Node distribution, with metadata access to its parent directories, and its `bin` on the worker `PATH` | fails: `node_modules/.bin/tsc` is a script in the project, and executing it is refused |
| … and execution of the project's installed `node_modules` | **passes, 39 of 39** |
| … and writes to `node_modules` denied | **passes, 39 of 39**; a worker write into `node_modules` is refused |

**As a Proofbound change**, it would work like this:
- **Declaration.** A run declares a toolchain directory at `start`, and the run records it with a
  digest.
- **Boundary.** Authorization makes that directory readable and executable and puts it on the
  worker `PATH`. It also allows execution of the project's already-installed `node_modules` while
  denying writes to it, so dependencies are prepared before any worker runs, never during.
- **Scope.** Runs that declare nothing are unchanged.

**Why changing the environment instead is not enough.**
- **Relocating Node doesn't help.** Moving the pinned Node under an allowed path still leaves the
  TypeScript compiler and the `.bin` scripts executing from the project, which is refused.
- **There is no supported way to set the worker `PATH`.**

**Running without worker execution is possible but weak.** The workers would read and write code
blind, with checks run only on the host at acceptance.

## User-visible decisions the owner's goal leaves open

These are recorded here and not turned into defaults. The requirements process will propose
answers, and any with material user-visible consequences goes back to the owner.

1. **Command names.** The CLI commands that place and remove a hold.
2. **Error code for a held checkout.** A new code, or v0's `ITEM_UNAVAILABLE`. Scripts matching on
   the code see the difference.
3. **v0's item `status` field.** The goal wants borrowed and held reported separately, with both
   possibly true. Whether `status` keeps its v0 values and adds fields, or gains new values, is a
   compatibility choice.
4. **`init` on an existing v0 database.** v0 reports `alreadyInitialized`. The goal says ordinary
   commands must not migrate.
5. **What ordinary commands report on an unmigrated v0 database.** An error code, and whether it
   names the migration command.
6. **The migration command.** Its name and output.
7. **Repeated operations.** Whether an idempotent repeat of a hold or removal reports that nothing
   changed.
8. **Hold timestamps.** Whether a hold records when it was placed. The goal excludes history and
   notes; a timestamp is borderline.
9. **Report summary counts.** Whether the report's counts gain a held count.

## The proposal that would follow (draft; no authorization is requested yet)

- **Run.**
  - **Target:** the isolated clone at `63da90eb`, change `BD-HOLDS-1`, starting from the owner's
    goal verbatim, with no pre-accepted requirements.
  - **Scope:** `src/`, `test/`, the behaviour contract and the README. No new dependencies.
- **Frozen configuration.**
  - **Proofbound:** the revision after the toolchain change.
  - **Worker:** `deepseek-v4-flash-high`, revision `2026-09-24`.
  - **Executor:** OpenCode 1.18.29.
  - **Interpreter:** Python 3.10.14.
  - **Coordinator:** this interactive Claude Code/Opus session.
- **Check command.** `/usr/bin/env PATH=<node 24.19.0>/bin:/usr/bin:/bin sh -c "test -d node_modules
  || npm ci; npm run check"`. On a fresh checkout it installs the locked dependencies, as CI does.
- **Launches:** at most 11, as in the first use. Author, challenge, consistency, implementer and
  reviewer make 5; one implementation repair adds 2; one requirements revision adds 3; plus one
  pre-executor allowance.
- **Limits:** 900 s per attempt, and $0.05 per launch, i.e. $0.55 derived with a $0.05 reserve.
- **Delivery verification.** `verify-delivery` on a fresh checkout of `63da90eb`, running the
  project checks and a public acceptance script.
  - **When it is written.** The coordinator writes the script from the accepted requirements
    before the implementer launches, and freezes it by digest.
  - **What it covers.** It exercises the owner's listed behaviours against a copy of the v0
    fixture.
- **Metered participants.**
  - **The worker:** limited by the derived allowance.
  - **This coordinator session:** metered by its own host and not measured by Proofbound.
  - **No headless or additional coordinator sessions.**
- **Unavailable:** provider billing, the served model's identity, this session's usage, and owner
  effort.

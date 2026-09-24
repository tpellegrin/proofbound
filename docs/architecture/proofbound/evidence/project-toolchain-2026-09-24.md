# Project toolchain — 2026-09-24

**Implemented and rehearsed through the production path, credential-free.** A run can now declare
a Node distribution at `start`. Its worker then runs BorrowDesk's full check inside the boundary:
39 of 39 tests pass. The worker cannot change the toolchain or the installed dependencies. No
provider request was made and no metered coordinator session was started. The blocker was
recorded in [borrowdesk-preparation-2026-09-24.md](borrowdesk-preparation-2026-09-24.md).

## The failure, preserved

Before the change, the production boundary, with the worker's exact environment, gave:
- `node`: not found (127);
- the pinned Node: `execvp` refused;
- `npm`: unavailable;
- TypeScript 7's native compiler: refused.

The probes are retained privately in `~/proofbound-evidence/borrowdesk-maintenance-holds-prep/`.
A run that declares nothing reproduces the same at the final code (the rows marked
*undeclared* below). That is its unchanged behaviour.

## The change

A bounded addition (`scripts/_toolchain.py`), not an environment manager. The rules are in
[worker profiles: project toolchain](../worker-profiles.md#project-toolchain).

**What it adds:**
- **`start --toolchain <dir>`** copies `node`, `npm` and `npx` into the run's runtime and records
  their digests. It also records the digests of the lockfile, of the `package.json` dependency
  fields and of the installed `node_modules`.
- **The boundary** puts the prepared copy first on the worker's `PATH`, sets npm offline, allows
  execution inside `node_modules`, and denies writes to both trees.
- **A launch-time and acceptance-time refusal** when any recorded digest changes.
- **`status` and `doctor`** report `project_tooling` apart from provider readiness.
- **`verify-delivery`** prepares its fresh checkout with the declared toolchain.

**What it does not add:**
- no package installation or download at start, launch or resume;
- no toolchain kind other than Node;
- no platform beyond the existing macOS boundary;
- no executor.

**Why a copy.** An allowance on the owner's distribution would let a later change to it, or a
renamed parent directory, substitute other bytes under the same path. The copy lives in the
run's runtime, where the worker can rename neither the copy nor its parent. It is a
copy-on-write clone where APFS offers one. A symlink that would leave the copied files is refused
at `start`: the pinned distribution's links are all relative and internal.

**Trust.** Project checks already execute project code. This makes a prepared toolchain available;
it does not make dependency code trusted or harmless. The DeepSeek profile's network access and
credential staging are unchanged. Dependency code executed by the worker has the same network the
worker already had, and the owner's home stays outside the boundary.

## Production-path rehearsal on BorrowDesk, at the final code

Two throwaway runs were started, from clones of the isolated checkout at `63da90eb`, with
dependencies prepared by `npm ci` with Node 24.19.0. The rehearsal used the pinned executor, a
dummy credential in a fake home, and ordinary `start` and `authorize-spending`. No profile was
edited by hand. The raw record is
`~/proofbound-evidence/borrowdesk-maintenance-holds-prep/toolchain-rehearsal-final.json`. An
earlier rehearsal of the same code before hardening is kept beside it.

| Declared run (`--toolchain ~/.nvm/versions/node/v24.19.0`) | Result |
|---|---|
| Record | Node v24.19.0, npm 11.17.0, prepared copy under the run's runtime; toolchain identity `734835bf…`, lockfile `e3a5d1e5…`, manifest fields `allowScripts`, `dependencies`, `devDependencies` |
| Authorization's check inside the boundary | exit 0, **39 pass, 0 fail**, 4.4 s; `status`: `project_tooling.verified: true` |
| `node`, `npm` | v24.19.0 and 11.17.0, resolved from the prepared copy |
| TypeScript 7's native compiler | `Version 7.0.2` |
| `better-sqlite3` | loads its native addon and runs SQL (SQLite 3.53.4) |
| `npm run check` | passes; build output (`dist/`, `dist-test/`) written |
| Write, delete, rename, `chmod` or hard-link the prepared toolchain | `Operation not permitted` |
| Write, rename, `chmod` or hard-link `node_modules`, or remove `.bin/tsc` | `Operation not permitted` |
| Rename the run's runtime or the project directory | `Operation not permitted` |
| Execute a copy of the native compiler outside `node_modules` | `Operation not permitted` |
| `npm install left-pad` | exit 1, `ENOTCACHED`; `package.json` and lockfile unchanged; nothing installed |
| npm's cache | inside the run's home (`<runtime>/home/.npm`), offline |
| Read `~/.zshrc`, list the owner's home | `Operation not permitted` |
| Execute the owner's Node directly | `execvp` refused |
| Changed dependency declaration, changed prepared toolchain, missing prepared toolchain, changed `node_modules` | each refused at `continue` **before a slot was reserved**; the ledger unchanged; the reason names what changed and that nothing was reinstalled |
| Preparation restored | no problems; launchable again |

| Undeclared run, same project | Result |
|---|---|
| Record, `status` | no `toolchain`; no `project_tooling` |
| `node`, `npm` | not found (127) |
| TypeScript 7's native compiler | `execvp` refused (71) |

`node_modules` digests depend on where the tree is installed. `better-sqlite3`'s
`build/Makefile` and `build/config.gypi` embed the install path, so the digest differs between two
correct installs. They are compared within a run only. Across locations, the lockfile is the
identity `verify-delivery` compares.

## Automated regressions

`tests/test_toolchain.py` has 12 tests. They use a synthetic Node distribution, and a copy of the
test interpreter as the native dependency, because a copied Apple platform binary is killed on
this macOS. Four of them need `sandbox-exec` and the pinned executor for authorization, and skip
without them; the provider is redirected to a closed loopback port.

They cover:
- the prepared record;
- refusal before anything is created: dependencies not installed, a `.node-version` mismatch, an
  absolute link, a link to an uncopied file;
- a repeated `start` with a different toolchain;
- the acceptance check using the prepared bytes, and refusing changed declarations;
- `project_tooling` unverified until a passing boundary check;
- the boundary: execution, every write, rename, mode change and hard link, the owner's home,
  offline npm;
- five changed or missing preparations, each refused before a slot is reserved;
- an undeclared run's profile, status and behaviour;
- `verify-delivery` with a matching and a changed source.

Each guarantee was removed in turn from the final code, and the module was run again:

| Removed | Module result |
|---|---|
| write denial | 10 failures, 1 error |
| execution inside `node_modules` | 2 failures |
| the pre-reservation launch check | 1 failure, 4 errors |
| the prepared-copy layout check | 1 failure, 1 error |
| the symlink guard | 2 failures |
| the `node_modules` digest comparison | 1 failure, 3 errors |
| offline npm | 1 failure |

The focused modules that share the changed code ran on the final code, and all passed:
- worker profiles;
- workflow boundary;
- executor start-up;
- supervision;
- attempt teardown;
- operator workflow;
- live path;
- hermeticity;
- Git policy;
- toolchain.

## Limits

- **Node on macOS only**, like the boundary itself. A second toolchain kind would be a separate,
  justified change.
- **Readiness is established at authorization.** It is not re-run before each launch; the digests
  are what each launch re-checks.
- **Preparation runs outside Proofbound.** Dependencies are prepared by the owner, with the
  project's own install scripts, before `start`. `verify-delivery` runs `npm ci` on the host in its
  fresh checkout, as CI would, which can contact the registry.
- **The sandbox semantics are Apple's and not documented.** The denials above were observed on
  macOS 15 (Darwin 24.6), arm64.
- **`git` inside the boundary** prints `xcrun` cache warnings. This predates the change and
  affects no result here.

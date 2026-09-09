# MLR-C1 — fixture implementation record

Built and validated deterministically. No semantic call was made, no headroom was established, and
nothing here measures whether `CONTRACT` helps.

## What exists

A small reporting service that renders per-account activity reports and keeps their exports, so a
later download need not repeat the work. `app/api.py` handles requests; `app/exports.py` creates and
fetches exports; `app/reports.py`, `app/accounts.py` and `app/audit.py` are the neighbours an agent
must look past. Storage is the `objectstore` package, materialised **outside** the workspace and
imported from there in both arms.

Ten files in the `contract` workspace, fourteen in `full` — the four extra being the vendored copy of
`objectstore` at `third_party/objectstore-1.4.0/`, which is readable and, deliberately, not on
`sys.path`.

| | bytes |
|---|---|
| public contract | 2,540 |
| `objectstore` implementation | 4,405 across four files |
| application | 3,625 |

Descriptive only, and not a threshold. It says there is something to substitute: a caller relying on
the contract carries roughly half the text of the implementation, and the difference arises from
genuine hidden decisions rather than padding — key derivation by digest with directory fan-out, a
retry policy, checksum framing, atomic replace-on-write, and an internal error type that never
escapes.

## Identities

| | sha256 (16) |
|---|---|
| runtime `objectstore` (both arms) | `280a24f0f9311343` |
| public contract (both arms) | `af3d3e9be15b51ed` |
| `full` workspace | `9053040a837fe501` |
| `contract` workspace | `c93d39f6722fcf2d` |

## Gates

**Entailment — pass.** The contract states what callers may rely on and says the package owns
everything else. The external task needs three of its facts — `NotFound` on absence, `put` safe to
repeat, a successful `put` immediately visible — and all three are stated.

**Exercise — pass.** The task is about producing an export when none is stored, which is answerable
only through the boundary; the reference solution reads and writes through it.

**Discrimination — pass.** Both arms execute the same runtime digest, expose a byte-identical
contract, share one task file, and pass the same baseline tests. The automated arm comparison reports
the vendored source as the sole difference and would fail the suite on any other.

**Contract sufficiency — pass.** The reference solution touches only `app/`, never the package and
never the contract, and satisfies the hidden gate in both arms. The gate fails before the work is
done, so the probe measures something.

**Responsibility validity — pass for the external task.** Deciding what a request returns is the
service's; keeping bytes is the package's.

**Headroom — pending MLR-C3.** It cannot be established by inspection: it asks whether a `FULL` agent
actually reads the implementation, which only a run can answer.

## The approved internal control could not be built

The design named *change the storage retry behaviour* as the boundary-crossing control and, in the
same document, made the package an out-of-tree dependency. Those two decisions are incompatible, and
the incompatibility was demonstrated rather than argued: editing `full`'s readable copy leaves the
running system on the original policy, because that copy is not what executes. A hidden test
asserting a new retry policy therefore fails in **both** arms, and the control would measure only
that neither arm can modify a dependency.

A control of that shape needs the module **inside** the repository and made unreadable by an
executor read policy — which is the mechanics MLR-C2 was already scheduled to build. So the control
is not deferred out of convenience; it is blocked on a prerequisite, and this revision is frozen
without it.

## Confounds carried forward

- **Discovery, not access.** Either arm can reach the runtime through `objectstore.__file__` or
  `inspect.getsource`. Isolation here is that the implementation is not part of repository
  discovery; recovery attempts are evidence for MLR-C2 to retain, not breaches to prevent.
- **Dependency versus module.** `full` presents the source as a vendored third-party package rather
  than as the service's own code. That is the honest shape of an out-of-tree boundary and it is also
  a difference in how an agent may feel entitled to treat the code.
- **One boundary, one architecture.** Nothing here can attribute an effect to boundary quality.

## Rules that bind from here

The fixture is frozen at this revision. A later milestone may not add a contract sentence because
`CONTRACT` failed, rename a file because agents did not find it, or enlarge the module because an
effect was small. Any of those creates a new revision, and evidence gathered under this one keeps
the meaning it had when it was recorded.

## What MLR-C2 must prove

Arm materialisation on demand; identical runtime bytes at run time as well as at build time;
contract and task identity; the visibility difference; whether source recovery through `__file__` or
`inspect` is available and how it is recorded; retention of out-of-tree reads, which `ce1_facts`
currently discards; the four-way separation of available, supplied, read and consumed context;
deterministic gate execution after an agent's changes; paired slots and configuration identity; and
non-splicing resume. It must also decide whether a read policy is worth building, since the internal
control depends on it.

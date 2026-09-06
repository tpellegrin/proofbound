# Freeze and binding

> **Normative.** How a satisfied change graph and its accepted ledger records become one durable,
> content-addressed engineering-contract identity, and what that identity does and does not authorize.
>
> Builds on [artifacts-and-provenance.md](artifacts-and-provenance.md) — artifact identity, the M2A
> ledger, derived validity, provenance, and the M2B change graph are defined there and are not restated
> here. Entry point: [README.md](README.md).

## A4. Freeze and binding

*M2C-A and M2C-B are implemented; M2C-C is designed but not implemented.
Implementation corrections are in [A4.8](#a48-corrections-from-implementation).*

### A4.1 The identity that was missing

M2B proves a topology is satisfied *now*. That proof evaporates: the ledger is a current snapshot
(records are overwritten by re-acceptance and removable by withdrawal), and the graph is an editable
file. Nothing today can say *which exact engineering contract execution was authorized against*, once
either has moved.

Three statements, each strictly stronger than the last, and only the third is a contract:

```
B has bytes H                                          — artifact content identity (M2A)
B was accepted against A@H1, under design-reflection    — accepted engineering binding (NEW)
this exact set of such bindings                         — freeze identity (NEW)
```

**Content identity is provably insufficient.** Let B's bytes be `H_B`, accepted against `{A: H1}`. Later
authority requires `B -> {A, C}`; B is re-reflected and re-accepted byte-identically against
`{A: H1, C: H3}`. `content_sha256` is still `H_B` in both worlds. A freeze recording only content could
not tell them apart, and would silently mean the wrong contract. This is the defining test of the model.

### A4.2 One new identity, not four

| Identity | Status |
|---|---|
| Artifact content identity | **Exists** (M2A). Unchanged. |
| Graph identity | **Exists** (M2B). **Not part of a freeze** — see below. |
| Task contract identity | **Exists** (DSD). Reused unchanged. |
| Accepted engineering binding | **New, but inline** — four fields per artifact, not a stored hash. |
| Candidate identity | **New.** SHA-256 over the canonical serialization of all bindings. |
| Freeze identity | **The same value.** Not a separate layer. |

**Candidate identity and freeze identity are one number.** A freeze *is* the canonical candidate,
written down. That makes "does the current project still produce this contract?" answerable by
recomputing the candidate and comparing it to the freeze's own identity — no second hash, no stored
self-reference, and no way for the two to disagree.

Then what does freezing add over computing the candidate on demand? **Durability.** The candidate is
computable only while the graph and ledger still say what they said. After a withdrawal, an overwrite, or
a graph edit, it is gone. The freeze is the copy that survives — which is why it must contain the
bindings rather than point at them (A4.4).

**Per-binding hashes are rejected.** Hashing each binding and storing only digests would make the freeze
unreadable for no invariant: the aggregate hash already covers every field, and a reviewer must be able
to see what was bound.

### A4.3 What a binding contains, decisively

```jsonc
{
  "format": "proofbound-freeze-v1",
  "artifacts": {
    "specs/CH-001/proposal.md": {
      "content_sha256": "…", "depends_on": {}, "review_purpose": "proposal-reflection" },
    "specs/CH-001/design.md": {
      "content_sha256": "…",
      "depends_on": { "specs/CH-001/proposal.md": "…" },
      "review_purpose": "design-reflection" }
  }
}
```

| Bound? | Field | Why |
|---|---|---|
| **Yes** | `content_sha256` | The bytes. |
| **Yes** | `depends_on` | The relationship the bytes were accepted under. Without it, A4.1's two worlds are indistinguishable. |
| **Yes** | `review_purpose` | Semantic engineering provenance, not derivable from role (`P2`). Same bytes and dependencies accepted under `design-reflection` versus `specification-reflection` are different engineering facts. |
| **No** | `role` | The *mechanism* that satisfied the purpose. If the registry later authorizes another role for the same purpose, the engineering meaning is unchanged (`P2`). |
| **No** | `gate`, `gate_sha256`, attempt id | Execution evidence, `L3`, deletable and run-relative. Binding them would make engineering identity depend on ephemeral machine-local state (`P4`) and would churn the contract on an equivalent fresh re-review. |
| **No** | graph identity or path | Redundant: for a satisfied graph the required edges and the recorded edges are equal in **both** directions (M2B enforces `missing-required-edge` and `undeclared-edge`), so the copied `depends_on` maps *are* the topology. Including the graph hash would also churn the contract on a whitespace-only reformat of `graph.json` — incidental history, not engineering meaning. |
| **No** | ledger reference or record hash | The ledger is mutable; a reference into it could be rewritten later (A4.4). |
| **No** | timestamps, freeze number, `status`, `supersedes`, author, model/provider, change id, metrics, self-hash | No invariant depends on any of them. Git dates and orders; `P3` forbids stored state; the directory names the change; content-addressed naming makes `supersedes` derivable. |

The desired stability follows: **a fresh re-review that changes nothing about content, dependencies or
purpose produces an identical candidate identity.** Proofbound freezes engineering meaning, not
incidental execution history.

### A4.4 Copy, never reference

A freeze must not mean *"whatever `ledger.json` currently says about B"*. Withdrawal and re-acceptance
would then rewrite what a historical freeze meant — the exact retroactive mutation freeze exists to
prevent. So the freeze **copies** the four fields of each binding and is thereafter self-contained: it
needs no ledger, no graph, and no run tree to state what it requires.

One deliberate exception. A `depends_on` target may be an artifact outside the graph (A3.4), so it has no
entry of its own in the freeze. The freeze records the identity B was accepted against, not that
artifact's own binding. Internal consistency therefore means: every `depends_on` key that *is* a frozen
member must match that member's `content_sha256`; external targets are recorded identities with no entry.

### A4.5 Immutability is by identity, not by the filesystem

Nothing prevents a human editing a committed file. A freeze is immutable in the only sense that is
truthful: **identity is content.** Editing the file produces a different freeze; the old identity still
names the old contract. `F2` never rewrites `F1` (`P9`).

Freezes are therefore content-addressed and append-only — `specs/<change>/freezes/<identity>.json` — which
gives supersession with no stored `supersedes` field and no mutable `current_freeze` pointer (`P3`).
**There is no persisted "current freeze."** A task contract names an exact freeze; "latest" is a parent
convenience, never protocol.

Freeze content is **machine-generated**, unlike the human-authored graph, so canonical serialization is
justified here where semantic graph hashing was not: UTF-8, sorted keys, `indent=2`, sorted dependency
keys, trailing newline, duplicate paths rejected, unknown fields rejected, unknown version fails closed.
Identity is SHA-256 over those canonical bytes — no salt, no path in the hash, so a copied freeze is the
same freeze. Generation must be deterministic: identical graph and ledger produce byte-identical output.

**Historical semantics (`P6`).** A v1 freeze is verified under v1 rules. In particular its
`review_purpose` values are checked against the **vocabulary v1 pinned**, never against the live
registry — otherwise adding a purpose later would silently reinterpret old contracts, which is precisely
the M0 failure. Freeze validation never re-authorizes purpose against roles; authorization already
happened at acceptance.

### A4.6 What a freeze does not prove

Five distinct claims, and a freeze mechanizes only the third:

```
artifact valid  <  graph satisfied  <  contract frozen  <  contract coherent  <  authorized for execution
```

A mechanically satisfied graph of individually reflected artifacts can still contain cross-artifact
contradictions (`P10`). Freezing it produces an authoritative record of an *incoherent* contract. The
aggregate `consistency-reflection` that would address this is deliberately a **separate milestone**
(plan §M2C-B): a freeze primitive and a semantic authorization step are two theses, and Proofbound's
history is that proving one at a time is what catches the mistakes.

Because candidate identity changes whenever any binding changes, a consistency review bound to `C1`
mechanically cannot be replayed onto `C2` — the M1 freshness principle, obtained for free from
content-addressing rather than from new machinery.

**Trust boundary, as everywhere else.** A SHA-256 identifies exact content; it is not an approval
signature (`P5`). Anyone with write access can author an internally consistent false freeze. Structural
validity is checkable from a clean checkout; provenance verification needs retained evidence and remains
orthogonal (a freeze stays structurally intact when its underlying provenance becomes `contradicted`);
neither proves authorization, which rests on repository governance until signing exists.

### A4.7 Validation layers

Never one `freeze_valid` boolean. Four independent questions, each answered separately:

| Layer | Asks | Needs |
|---|---|---|
| **Internal** | Is the freeze well-formed and self-consistent? | The freeze file alone |
| **Repository satisfaction** | Do current artifact bytes still match the frozen identities? | Working tree |
| **Candidate equivalence** | Does the project still *produce* this freeze? | Current graph + ledger |
| **Provenance** | Is the underlying accepted evidence retained and consistent? | Run tree; `unavailable` is not failure |

A freeze can be internally valid, no longer satisfied by the repository, and still the correct binding for
work already authorized under it. Collapsing these would make that state unrepresentable.

### A4.8 Corrections from implementation

Three things changed or were settled when M2C-A was built. The schema, identity model and
binding semantics survived unaltered.

1. **External dependency closure: members are exactly the graph's declared artifacts.** The design
   check left this open as the largest edge case, with three candidate models. Resolved in favour of
   graph membership, because **membership is authority's declaration of what constitutes the contract**.
   Including the transitive closure would put artifacts into the frozen contract that no authority
   declared, letting Proofbound infer contract membership from dependency structure rather than from
   declaration — an inversion of `P7` and `P11`. A dependency target outside the graph stays a recorded
   identity the contract was reviewed against; its own binding belongs to whatever contract declared it.
   Consequently **no `roots` field is needed**, and the two-field schema stands.

   The honest limit: a freeze pins an external target's *content* (the dependency hash is that content
   identity) but not its provenance. If the external artifact's own accepted dependencies move while its
   bytes do not, the freeze is unaffected — that staleness is M2A closure's question against the current
   ledger, which is a different layer.

2. **A non-computable candidate is a finding, not success.** Found by the vertical slice: after a
   withdrawal the graph is unsatisfied and no candidate exists, and returning "no differences" would
   have asserted the project still produces the freeze when nothing established it. Not computable is
   not equivalence.

3. **Provenance policy at creation, never in identity.** `verified` and `unavailable` may be frozen;
   `contradicted` refuses creation. Identity is unaffected either way, because freeze bytes derive from
   graph and ledger alone — a contradiction cannot change what a freeze says, only whether a *new*
   durable record should be minted from evidence that disagrees with itself. Absent evidence is not
   disagreement, so an old repository with no run tree can still freeze. The check runs only when a run
   root is supplied; it is a guard, not a gate (`P5`).

**Storage.** `specs/<change>/freezes/<identity>.json` — content-addressed and append-only, so
supersession needs no `supersedes` field and no mutable pointer (`P3`). Re-deriving an unchanged contract
rewrites nothing. Validation reports a `filename-identity-mismatch` when a 64-character filename does not
match its content, which catches a renamed or hand-edited file without making the filename authoritative:
identity is content, so a copy under any name is the same freeze.

**Not implemented, and not implied.** M2C-A authorizes nothing. There is no task freeze reference, no run
or phase binding, no mixed-freeze reporting, no consistency reflection, and no cross-ledger composition.
A freeze is a durable engineering-contract candidate; calling it "approved" or "authorized for execution"
would claim exactly what [A4.6](#a46-what-a-freeze-does-not-prove) says it cannot.

---

## A5. Aggregate consistency acceptance (M2C-B — IMPLEMENTED)

*Normative. Implemented in `scripts/_consistency.py` and `scripts/pb_consistency.py`; this states what it
guarantees. Implementation corrections are in [A5.10](#a510-corrections-from-implementation).*

### A5.1 The durable fact that must exist

M2C-A can say *which* exact engineering contract existed. It cannot say that anyone challenged it as a
whole. Individually reflected artifacts can still contradict each other — a design that quietly violates
its own proposal, two specifications that disagree about the same behaviour — and
[A4.6](#a46-what-a-freeze-does-not-prove) is explicit that freezing such a set produces an authoritative
record of an *incoherent* contract.

The fact M2C-B must establish durably, worded precisely because the wording decides what Proofbound
claims authority over:

> Candidate `C` received a qualifying consistency-reflection review, and the parent accepted it.

Not *"C is consistent"* — that is a semantic verdict, and Python asserting it would recreate the PASS
enum DSD deliberately deleted. Not *"C is the accepted engineering contract"* — that is authorization to
execute, which is M2C-C. The record is **provenance of a challenge**, exactly as the M2A ledger records
that an artifact was accepted under a purpose rather than that the artifact is good.

### A5.2 Why a new durable surface is required

The obvious cheap answers were tested against code and all fail.

| Model | Verdict |
|---|---|
| **Reuse the artifact ledger** | **Rejected by code.** `derive_states` resolves every key as `project_root / key` and requires `is_file()`. A candidate identity is not a file, so a synthetic key would be permanently reported `invalid`. Ledger keys *mean* repository artifact path; reusing them would require the record to lie about what it is. |
| **A consistency-attestation artifact** | **Rejected by architecture.** `spec-reflector` is in `ALWAYS_READ_ONLY_ROLES`; it cannot author the attestation without becoming a writer and tripping `READONLY-SCOPE-MOVED`. Having an author write it and a reflector review it makes the attestation's own acceptance need an attestation. Its content would also be a semantic verdict persisted as data. |
| **Derive from the task contract and gate** | **Rejected by the trust model.** `accept_task` writes acceptance into `run_root/state.json` — inside the run tree, which is `L3` and expendable by design. Deleting the run tree would destroy the only proof, promoting execution evidence into durable engineering authority. |
| **No new durable construct** | **Rejected.** Following from the above: after `L3` deletion, no file in project state records that any aggregate challenge happened. The information is simply absent. |
| **Wrapper object around the freeze** | **Rejected as a distinct model** — it is the record below under another name, and modifying or re-hashing `C` would break `A4`. |
| **Separate record keyed by candidate identity** | **Adopted.** |

This is the same two-step shape M2A already established and proved: DSD accepts through inherited
mechanics (`L3`), then the parent copies the durable consequence into project state (`L4`).

### A5.3 The v1 record

One file per accepted candidate, beside the freezes:

```
specs/<change>/freezes/<identity>.json        the contract candidate      (M2C-A)
specs/<change>/consistency/<identity>.json    it was challenged           (M2C-B)
```

```jsonc
{
  "format": "proofbound-consistency-acceptance-v1",
  "candidate": "<candidate identity>",
  "gate": "phases/spec/…/evidence-gate.json",
  "gate_sha256": "…"
}
```

| Field | The invariant it enables |
|---|---|
| `format` | Historical semantics (`P6`); unknown version fails closed. |
| `candidate` | The subject. Without it the record's meaning would live only in its filename, and a copy elsewhere would mean nothing — the same self-containment that makes a freeze durable. The filename is a convenience index, cross-checkable against this field. |
| `gate` + `gate_sha256` | The only thing that makes the claim falsifiable. Without them the record is an unfalsifiable assertion that a review happened, and provenance verification is impossible. Run-relative, never a machine path. |

**Rejected**, each because no invariant depends on it: `review_purpose` and `role` (v1 *is* the
consistency-reflection record, and the qualifying role set is a pinned v1 constant; the hash-pinned gate
already states the actual role, so a recorded copy could only duplicate or contradict it); `timestamp`
and `accepted_at` (Git); `attempt`, `provider`, `model` (execution mechanics, `P4`); the artifact list or
freeze bytes (already in the freeze at `candidate`); `graph_sha256` (excluded from freeze identity for
the reasons in [A4.3](#a43-what-a-binding-contains-decisively), and reintroducing it here would smuggle
it back); `status`, `approved`, `consistent`, `semantic_valid` (`P3`, and see A5.1); `revision`,
`supersedes`, `current` (see A5.4).

**Historical pinning.** v1 must pin the qualifying role set for `consistency-reflection` as its own
constant rather than consulting the live `REVIEW_PURPOSE_ROLES`. Otherwise a later registry change would
silently reinterpret which reviews had been qualifying — the M0 failure, at a new boundary.

### A5.4 Supersession needs no field

`C1` and `C2` are different subjects, not versions of one thing, so both records coexist naturally under
content-addressed names and nothing supersedes anything. Re-reviewing the same `C` overwrites that one
file — a current-provenance snapshot with Git as history, matching the ledger exactly, and adding no
chronology field for events Git already keeps.

There is **no `current_freeze`, no `active_candidate`, no accepted-contract pointer.** Which candidate is
current is derived from the graph and ledger; whether it has been challenged is a file lookup by its
identity. Both are computed, never stored (`P3`).

### A5.5 Freshness is already solved

No new freshness machinery is required, and this is provable from the substrate rather than asserted.

The consistency-review task contract names the exact candidate identity in its Markdown. Because
`accept_task` verifies both that `sha256(contract)` still matches what the task bound **and** that the
accepted gate's own `task` field resolves to *that exact contract path*, a review performed under a
contract naming `C1` cannot be accepted for a task whose contract names `C2`: the two contracts have
different bytes, therefore different hashes, therefore are different files. Editing one in place fails
the first check instead.

So a review of `C1` can never qualify `C2` — for free, from the same mechanism that has enforced M1
freshness since the beginning. **No reservation field, no candidate nonce, no freeze revision.**

### A5.6 What the reviewer actually reviews

The contract binds an *identity*; the reviewer needs *material*. Nobody can judge a SHA-256.

The subject is the engineering meaning the candidate denotes: the member artifacts' accepted content,
the dependency relationships between them, and the declared purpose each was accepted under. The
reviewer reads the freeze for the exact membership and bindings, and the member artifact files for
substance. Retrieval material is context, never identity — the order files are read in must never enter
what `C` means.

Its questions are the ones no single-artifact reflection can reach: do these artifacts contradict each
other, does the design actually satisfy the proposal it depends on, are assumptions consistent across the
set, is the aggregate coherent enough to become the baseline for implementation. It is **bounded to
`C`** — repository-wide architectural coherence is a different capability and stays out.

**A stated v1 limitation.** A freeze pins content *hashes*, not content *bytes*. So a candidate whose
artifacts still match on disk can be reviewed directly, while re-reviewing a historical candidate whose
artifacts have since moved would require recovering those bytes from Git. M2C-B v1 therefore reviews the
**current** candidate, derived at launch time and bound by identity. Embedding artifact bytes in a freeze
to remove this limitation would be a large and speculative change to a shipped format; the limitation is
better stated than designed around.

**Graph-external dependencies remain sound.** A member may depend on an accepted artifact outside the
graph ([A3.4](artifacts-and-provenance.md#a34-membership-dependency-targets-and-what-exact-means)), and
that artifact is not a freeze member. Verified empirically: if such a dependency's bytes drift, the
member becomes `needs-revalidation` through ledger closure, the graph stops being satisfied, and the
current candidate becomes **non-computable** — so whenever a current candidate exists, every external
dependency is still at the content it was pinned against. The reviewer may therefore read it as context
and rely on it. The review claims nothing about *that artifact's own* coherence, which belongs to
whatever contract declared it. M2C-A's membership decision does not need reopening.

### A5.7 Findings return to artifact level

If the reflection finds a contradiction, no acceptance is recorded — absence of the record is the whole
representation, and there is no failure object, no rejected state, no PASS/FAIL enum.

Repair cannot happen under the aggregate contract, and this is structural rather than a policy choice.
`C` is *derived*, not a file anyone can edit; fixing a contradiction means changing an underlying
artifact, which moves that artifact's accepted binding, which changes the candidate identity. The
aggregate contract's binding would no longer describe anything.

So aggregate findings route **back into artifact-level workflows** — the relevant proposal, design or
specification is revised under its own contract and its own reflection — and the resulting candidate
`C2` gets its own fresh aggregate challenge. There is no consistency fixer, and no candidate revision
number: engineering changes produce a new identity by themselves.

### A5.8 Four orthogonal questions

M2C-B adds one dimension and must not collapse into any existing one.

| Question | Answered from |
|---|---|
| Is the acceptance record well-formed? | The record alone |
| Was candidate `C` challenged and accepted? | Does a record for `C` exist |
| Is `C` still what the project produces? | Current graph + ledger (M2C-A candidate equivalence) |
| Is the aggregate review's evidence still verifiable? | Run tree — `verified` / `unavailable` / `contradicted` |

States that must all be representable without contradiction: `C` accepted and still current with verified
provenance; `C` accepted while the project has moved to `C2` (the historical record stands, and `C2` has
no acceptance); `C` accepted with the run tree deleted (record intact, provenance `unavailable`); `C`
accepted with retained evidence corrupted (**record and identity unchanged**, provenance `contradicted`);
a current candidate with no acceptance at all; and a satisfied graph of individually valid artifacts whose
aggregate review found contradictions, which is simply the absence of a record.

Two consequences worth stating. Corrupted evidence changes *provenance*, never the historical record —
creation policy and later verification policy are different questions, as in M2C-A. And because
acceptance is keyed by identity, "this candidate was challenged" and "this candidate is current" can
never be confused for one another.

### A5.9 Authority

Recording is parent-owned, protected by the mechanism that already protects the ledger, the graph and
the freezes: the path lies outside every worker's `Allowed source changes`, so a worker writing it trips
the inherited `WRITE-RESTRICTION` before any acceptance can exist (`I6`, `P7`). The reviewer cannot
self-record by writing a file, and no new permission system is needed — only the usual contract
discipline when the workflow is built.

Recording must verify what `pb_ledger record` already verifies, and refuse otherwise: the task is
`accepted`, the accepted gate is intact and clean, the contract is unchanged, its declared review purpose
is `consistency-reflection`, and the gate's role qualifies for that purpose under the pinned v1 set.
Unlike freeze creation — where absent evidence is normal for an old repository — recording an aggregate
acceptance whose evidence is already gone would be recording a claim the parent cannot evidence at the
moment it makes it, so the gate must be present.

**A freeze with an acceptance record is still not authorization to execute.** Binding implementation work
to an exact contract is M2C-C. What M2C-B establishes is precisely one thing: that this exact candidate
was independently challenged as a whole, and that the challenge qualified.

### A5.10 Corrections from implementation

The design survived implementation intact — schema, storage, authority model, freshness reuse and the
purpose/role exclusions all shipped as designed. Three points were sharpened by building it.

1. **The record must verify that the freeze it names is real.** Recording takes the freeze whose identity
   the contract declared and refuses unless `freeze_identity(freeze) == declared candidate`. Without it an
   acceptance could be recorded for an identity that never denoted anything — the record would be
   syntactically fine and about nothing. This is a creation-time check only; the record itself still
   stores no freeze path, so it stays independent of storage layout.

2. **Creation checks the v1 constants, not the live registry.** The design said verification must pin
   them; implementation showed *creation* must too, or a record could be written today that fails to
   verify tomorrow under the very semantics it claims. Refusing to write a v1 record for something v1
   does not recognize is the correct asymmetry.

3. **Re-review refreshes provenance in place, and the record's bytes legitimately change.** The candidate
   is one subject, so a second qualifying challenge repoints `gate`/`gate_sha256` at the newer evidence
   while `candidate` is unchanged. The durable *subject* is stable; what evidences it is not, and Git
   carries that history. Nothing accrues: one candidate, one file.

**The replay proof is inherited, not new.** The slice takes a genuinely accepted `C1` review and attempts
to accept it against a contract naming `C2`; it is refused by `accept_task` with *"source gate is not
bound to task.current_contract"*. Contracts naming different candidates are different files with
different hashes, so no nonce, reservation field or freshness token was added.

**Authority.** A reflector that writes into the consistency directory trips the inherited read-only scope
check, its gate is unclean, acceptance refuses, and recording then refuses because there is no acceptance
to record — three independent barriers, none of them new. The CLI is two commands: `record` (parent-owned)
and `status`, so callers ask a domain question rather than using `Path.exists()` as the definition of
acceptance.

**Still not authorization.** A candidate with an acceptance record has been *challenged*, not authorized
to execute. Binding implementation work to an exact contract remains M2C-C.

---

## A6. Execution binding (M2C-C — designed, not implemented)

*Normative direction. No production code implements any of this.*

### A6.1 What must become mechanically true

> An implementation task's engineering authority is one exact candidate, fixed immutably when the task is
> authorized, and it may only be authorized against a candidate that is both currently derivable and
> already independently challenged.

Everything in that sentence is a composition of facts Proofbound can already establish. The design check
found **no invariant requiring new persistent state**, and the substrate reason is that M2C-B shipped the
primitive M2C-C needs: a contract section naming an exact candidate, hash-bound by the inherited
mechanism, with `declared_candidate` already parsing it.

### A6.2 Binding is already solved

An implementation contract carries the same section a consistency contract carries:

```
## Proofbound candidate
- <candidate identity>
```

This is not a new mechanism and needs no launch-path change. The whole contract file is hashed, the
reservation binds that hash, and acceptance verifies both the hash and that the gate was produced under
that exact contract path. M2C-B's shipped slice proves it end to end: a genuinely accepted review of one
candidate is refused for a contract naming another, with *"source gate is not bound to
task.current_contract"*.

The field stays **optional**. Inherited DSD tasks declare no candidate and keep their exact semantics —
the same compatibility seam M2A used for `## Review purpose`. Presence is what selects Proofbound
binding; absence is absence, never a default.

### A6.3 Launch authorization

Three checks, all derived, none stored:

1. the current graph and ledger derive exactly `C` (`pb_freeze compare`);
2. `C` has a durable consistency acceptance record (`pb_consistency status`);
3. that record's provenance is not `contradicted`.

**Provenance policy, derived rather than copied.** `verified` and `unavailable` both authorize;
`contradicted` refuses.

`unavailable` must authorize, and the reason is structural. Execution evidence is expendable *by design*;
if losing it blocked all future implementation, then deleting an old run tree would silently destroy the
operational value of the durable acceptance it can no longer verify. That would make provenance
*availability* into authority, contradicting both `P5` and the `L3`/`L4` separation the whole architecture
rests on. `contradicted` is different in kind: retained evidence actively disagrees with the record, and
authorizing new work on it would launder a known inconsistency.

A candidate that is not currently derivable cannot authorize anything, because check 1 cannot pass. A
freeze without a consistency acceptance cannot either — that is exactly the gap M2C-B exists to close.

These are **parent-side guards, not gates** (`P5`). Nothing prevents a determined operator from writing a
contract by hand; the guard exists so the normal path is the correct one.

### A6.4 Authority is fixed at launch — the central decision

When `C1` is current and task `T` launches against it, and engineering intent later becomes `C2` while
`T` is still running:

**`T` remains a `C1` task, permanently and honestly.** It continues, is reviewed, repairs through the
fixer loop, and is accepted on the terms of its own immutable contract. Nothing rechecks currentness at
acceptance.

Three independent reasons, none of them convenience:

- **Consistency with two shipped milestones.** M2C-A already treats "historically accepted, current graph
  unsatisfied" as informative rather than dangerous; M2C-B already keeps `C1`'s acceptance after the
  project moves to `C2`. Rechecking currentness at acceptance would make implementation the only layer
  that retroactively invalidates completed work.
- **The alternative requires forbidden inference.** Rejecting `T` only when `C2` *matters to it* is an
  applicability judgement, and applicability is explicitly deferred
  ([artifacts-and-provenance.md §36.3](artifacts-and-provenance.md#363-applicability-is-not-a-dependency-edge)). Rejecting `T` whenever any
  unrelated artifact moved would discard hours of correct work and teach people to route around the
  system.
- **The contract is immutable.** Its identity already includes `C1`. A task whose authority could change
  after launch would have a contract that no longer describes it.

The fixer loop inherits this for free: implementer, reviewer, fixer and re-reviewer all operate under the
one immutable contract, so the whole repair cycle stays `C1`-bound with no additional machinery.

### A6.5 Divergent candidates are reported, not gated

Two accepted tasks may legitimately name different candidates — engineering intent evolving mid-phase is
normal, and A6.4 makes each task honestly what it is. What must not happen is that divergence being
*invisible*.

So M2C-C supplies a **read-only report**: enumerate the accepted tasks in a run and the candidate each
contract names. Divergence is a finding the parent acts on, not a barrier.

Gating would require a mechanical phase-close, and there is none — phase status is set to `in-progress`
at task creation and never mechanically closed, with
`test_v15_5_adversarial::test_new_phase_state_does_not_create_barrier_machine` existing specifically to
stop gating state accumulating in phases. Inventing one is a separate architectural decision with its own
design check, not something to acquire as a side effect of binding work.

### A6.6 Execution binding only — the durability limitation, stated

**M2C-C provides execution binding, not durable implementation provenance.** This is a real limitation and
is recorded rather than hidden.

Verified from code: task contracts live at `run/phases/<phase>/tasks/<task>/contracts/rNNNN.md` and
acceptance is written into `run_root/state.json` — both inside the run tree, which must live under
`<project>/DeepSeekAndDestroy/`. Both are `L3`. After the run tree is deleted, **no file in project state
records that accepted task `T` was governed by `C`**. The ledger records accepted artifacts, the freeze
records candidates, the consistency record records challenges; none records implementation tasks.

This is the same gap M2C-B found for aggregate challenges and closed with a durable record. It is
deliberately *not* closed here, because no current invariant consumes it: the things that would — a
completion theorem over required implementation tasks, or a cumulative coherence audit — are separate,
deferred capabilities. Adding a durable record now would be speculative state under the field test.

The canonical thesis is scoped to match: *divergent freeze usage **across a run** is detectable*. When a
completion theorem is genuinely wanted, the missing fact is precisely "accepted implementation task `T`
was governed by `C`", and the shape to reach for is the one the ledger and the consistency record already
established.

### A6.7 Models considered

| Model | Verdict |
|---|---|
| **Pure composition** (current candidate + consistency acceptance + candidate in the immutable contract) | **Adopted.** No new state; every fact derived from shipped primitives. |
| Composition + acceptance-time currentness recheck | **Rejected** — see A6.4. Requires either discarding correct work or forbidden applicability inference. |
| Composition + reporting | **Adopted as part of the above**; the report is derived, not stored. |
| Durable implementation-binding record | **Rejected for M2C-C** — no current invariant consumes it (A6.6). |
| Phase-level freeze reservation | **Rejected** — needs a barrier that does not exist and that an adversarial test guards against. |
| Reuse stale-prerequisite machinery | **Rejected — nothing to reuse.** Verified: the inherited core has no stale-prerequisite or revalidation mechanism. Candidate movement is a distinct dimension, not another task dependency. |

### A6.8 What M2C-C does not do

No new persistent state, no `current_freeze` or `active_candidate` pointer, no new identity — the
implementation contract's existing hash already composes task instructions with engineering authority, so
hashing a hash would add nothing. No phase barrier, no mixed-candidate gate, no applicability, no
inherited-core change, no completion theorem, no coherence audit.

Accepting a task bound to `C` proves that task was executed and reviewed under that authority. It does
**not** prove that every required implementation exists, that the repository globally coheres with `C`, or
that the change is finished.

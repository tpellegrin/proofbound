# What building the binding chain corrected

Historical evidence for M2C-A (freeze identity), M2C-B (aggregate consistency acceptance) and
M2C-C (execution binding). **Nothing here is a rule.** Each rule these sections explain lives in
[freeze-and-binding.md](../freeze-and-binding.md), which is what the system obeys; this document
records what implementation found, what it changed, and what each milestone deliberately did not do.

It exists because that rationale was crowding the normative document it explains. A reader deciding
how to bind a task needs the obligation; a reader asking *why the obligation is shaped that way*
needs this, and almost never at the same moment.

## A4.8 — M2C-A: freeze identity

Three things changed or were settled when M2C-A was built. The schema, identity model and binding
semantics survived unaltered.

1. **External dependency closure: members are exactly the graph's declared artifacts.** The design
   check left this open as the largest edge case, with three candidate models. Resolved in favour of
   graph membership, because **membership is authority's declaration of what constitutes the contract**.
   Including the transitive closure would put artifacts no authority declared into the frozen contract,
   inferring membership from dependency structure rather than declaration — an inversion of `P7` and
   `P11`. A dependency target outside the graph stays a recorded identity the contract was reviewed
   against. Consequently **no `roots` field is needed**, and the two-field schema stands.

   The honest limit: a freeze pins an external target's *content* but not its provenance. If that
   artifact's own accepted dependencies move while its bytes do not, the freeze is unaffected — that
   staleness is M2A closure's question against the current ledger, a different layer.

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

**Why the storage shape.** Content-addressed and append-only means supersession needs no `supersedes`
field and no mutable pointer (`P3`), and re-deriving an unchanged contract rewrites nothing. Validation
reports `filename-identity-mismatch` when a 64-character filename does not match its content — which
catches a renamed or hand-edited file without making the filename authoritative, because identity is
content and a copy under any name is the same freeze.

**Not implemented by M2C-A, and not implied.** No task freeze reference, no run or phase binding, no
mixed-freeze reporting, no consistency reflection, no cross-ledger composition. A freeze was a durable
engineering-contract candidate and nothing more; calling it "approved" or "authorized for execution"
would have claimed exactly what
[A4.6](../freeze-and-binding.md#a46-what-a-freeze-does-not-prove) says it cannot.

## A5.10 — M2C-B: aggregate consistency acceptance

The design survived implementation intact — schema, storage, authority model, freshness reuse and the
purpose/role exclusions all shipped as designed. Three points were sharpened by building it.

1. **The record must verify that the freeze it names is real.** Recording refuses unless
   `freeze_identity(freeze) == declared candidate`. Without it an acceptance could be recorded for an
   identity that never denoted anything — syntactically fine and about nothing. A creation-time check
   only; the record stores no freeze path, so it stays independent of storage layout.

2. **Creation checks the v1 constants, not the live registry.** The design said verification must pin
   them; implementation showed *creation* must too, or a record could be written today that fails to
   verify tomorrow under the very semantics it claims. Refusing to write a v1 record for something v1
   does not recognize is the correct asymmetry.

3. **Re-review refreshes provenance in place, and the record's bytes legitimately change.** The candidate
   is one subject, so a second qualifying challenge repoints `gate`/`gate_sha256` at newer evidence while
   `candidate` is unchanged. The durable *subject* is stable; what evidences it is not, and Git carries
   that history. Nothing accrues: one candidate, one file.

**The replay proof is inherited, not new.** The slice takes a genuinely accepted `C1` review and attempts
to accept it against a contract naming `C2`; it is refused by `accept_task` with *"source gate is not
bound to task.current_contract"*. Contracts naming different candidates are different files with
different hashes, so no nonce, reservation field or freshness token was added.

**Authority, and why no new barrier was needed.** A reflector writing into the consistency directory
trips the inherited read-only scope check, its gate is unclean, acceptance refuses, and recording refuses
because there is no acceptance to record — three independent barriers, none new. The CLI is `record`
(parent-owned) and `status`, so callers ask a domain question rather than using `Path.exists()` as the
definition of acceptance.

**Still not authorization.** A candidate with an acceptance record had been *challenged*, not authorized
to execute. Binding implementation work to an exact contract was left to M2C-C.

## A6.9 — M2C-C: execution binding

Shipped as designed: **no new identity, no persistent state, no inherited-core change.** `authorize`
composes current-candidate derivation, the consistency lookup and provenance; `report` derives task
bindings from the immutable contracts a run already holds. The only other change moved current-candidate
derivation out of the freeze CLI into `_freeze` so it could be composed rather than duplicated —
behaviour-neutral, verified against the unchanged suite.

Two refinements from implementation. Authorization accepts a **contract** as well as a bare candidate:
the contract is the artifact that becomes the authority, and one declaring no candidate is reported
unbound rather than silently authorized — the explicit compatibility boundary for inherited tasks. And a
wrong candidate yields *two* findings (not current, never challenged), more informative than the first.

The slice proves the chain against real mechanics: a freeze alone does not authorize, `C1` review evidence
is refused for a `C2` contract, and a worker rewriting the candidate in its own contract breaks acceptance
with *"current contract missing or changed"*.

**The boundary M2C-C shipped with.** Execution binding only. Task contracts and acceptance both lived in
the run tree, so nothing durably recorded that an accepted task was governed by `C` once that tree was
gone. That limitation is still current and is stated at
[A6.6](../freeze-and-binding.md#a66-execution-binding-only--the-durability-limitation-stated).

## What came after

M2C-C's launch authorization turned out to be advisory: the checks ran, and nothing consumed the
answer. `pb-handoff-1` exposed it and
[admission-bypass-reproduction.md](admission-bypass-reproduction.md) records the reproduction and the
repair. The rule that replaced it is
[A6.10](../freeze-and-binding.md#a610-correction-authorization-was-advisory-m4--implemented).

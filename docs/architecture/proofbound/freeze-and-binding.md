# Freeze and binding

> **Normative.** How a satisfied change graph and its accepted ledger records become one durable,
> content-addressed engineering-contract identity, and what that identity does and does not authorize.
>
> Builds on [artifacts-and-provenance.md](artifacts-and-provenance.md) — artifact identity, the M2A
> ledger, derived validity, provenance, and the M2B change graph are defined there and are not restated
> here. Entry point: [README.md](README.md).

## A4. Freeze and binding

*M2C-A is implemented in `scripts/_freeze.py` and `scripts/pb_freeze.py`; M2C-B and M2C-C are not.
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

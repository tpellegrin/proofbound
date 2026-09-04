# Artifacts and provenance

> **Normative.** What an accepted specification artifact is, how its identity is computed, what the
> durable ledger records, how validity is derived, and what the two validation levels can and cannot
> prove. Also the constraints this places on the artifact graph (M2B) and freeze (M2C).
>
> Entry point: [README.md](README.md).

### 27.2 Decision resolved — canonical text identity, and why `-text` was rejected

[§26](evidence/implementation-findings.md#26-m2-design-check) suggested marking spec artifacts `-text` in `.gitattributes` because artifact hashes were to be
taken over raw bytes. That suggestion is **withdrawn**. Four options were considered against the
invariant *the same logical committed text artifact has the same identity on every supported OS and
under every checkout configuration*:

| Option | Verdict |
|---|---|
| `.gitattributes -text` | **Rejected.** Disables Git's text handling — diff, merge and eol behavior — for first-class human-readable documents, purely to stabilize a hash. It also fixes nothing for an artifact that arrives from outside Git, and pushes the wire format into a file any contributor can edit. |
| `.gitattributes text eol=lf` alone | **Insufficient alone.** Real, but it makes correctness depend on repository configuration rather than on the identity function. Kept as *hygiene*, not as the mechanism. |
| Hash the Git blob identity | **Rejected.** Makes identity require Git to be installed and the object store to be present, breaks a plain-file read, and inherits Git's own object-format versioning (SHA-1 vs SHA-256 repositories). |
| **Canonical text hashing** | **Adopted.** The identity function owns the invariant outright. |

The adopted algorithm, versioned as `proofbound-artifact-text-v1`:

```
strict UTF-8 decode  ->  replace CRLF with LF  ->  encode UTF-8  ->  SHA-256
```

What *does* change identity: text content, whitespace, wording, added or removed blank lines, a
trailing newline, and Unicode code points. There is no Unicode normalization and no BOM stripping —
precomposed and decomposed forms stay distinct, and a BOM is a preserved code point. Hidden
normalization would let two visibly different documents share one accepted identity, which is exactly
the failure a content-addressed record must not have.

**Only CRLF is folded; a lone CR is content.** This is deliberate and worth defending. Git's own
`text` normalization folds CRLF and never rewrites a lone CR, so folding CR here would make Proofbound
and Git disagree about which files are "the same text". No checkout configuration on a supported
platform produces lone-CR files, so there is no invariant to justify the extra normalization — and
over-normalizing silently erases real content.

The digest is a plain, unsalted SHA-256 of the canonical bytes, so on an LF checkout `sha256sum`
reproduces a ledger value with no Proofbound code in the loop. Version confusion is prevented by the
ledger recording the identity protocol explicitly, not by perturbing the digest.

`.gitattributes` carries `*.md *.py *.json *.yml text eol=lf` as hygiene. Identity does not depend on
it: `git add --renormalize .` produced no churn, and a CRLF checkout validates identically.


## A1. The durable change ledger (v1)

*Normative. Implemented in `scripts/pb_ledger.py`; this states what it guarantees.*

The ledger is the durable-provenance layer `L4` ([core-model.md §31](core-model.md#31-the-truth-model--four-layers)):
version-controlled project state recording which content was accepted, what it was reviewed against, and
under which declared purpose. It is deliberately not a summary of execution evidence.

Two independently versioned protocols, because they evolve separately (`P6`):

| Field | v1 value |
|---|---|
| `format` | `proofbound-change-ledger-v1` — the ledger schema |
| `artifact_identity` | `proofbound-artifact-text-v1` — the hashing protocol of §27.2 |

An unknown value for either is refused; a later version gets its own reader rather than being loaded into
today's assumptions.

Each accepted artifact carries exactly three keys, plus four inside `review`:

```jsonc
"specs/CH-001/design.md": {
  "content_sha256": "…",                       // the accepted content identity
  "depends_on": { "specs/CH-001/proposal.md": "…" },  // what this was REVIEWED AGAINST
  "review": {
    "purpose": "design-reflection",            // declared in the contract, from the closed registry
    "role":    "spec-reflector",               // recorded on the accepted integrity gate
    "gate":    "phases/spec/…/evidence-gate.json",  // run-RELATIVE; never a machine path
    "gate_sha256": "…"
  }
}
```

Every field earns its place under one test: *which invariant becomes impossible without it?* Content
identity is the whole staleness mechanism. `depends_on` records the accepted identity a reviewer actually
saw, not the dependency's current state. `purpose` is not derivable from `role` (`P2`). `role` is what a
clean checkout can check against the purpose registry. The gate reference and its hash are what make
provenance verification possible at all while execution evidence survives.

Fields that failed the test and are therefore **absent by decision, not by omission**: timestamps,
revision counters, `supersedes`, author-attempt identity, artifact kind, model or provider identity, token
telemetry, and any workflow-state enum. Git supplies history and dating; run evidence supplies attempt
mechanics; `P3` forbids a stored state. Adding any of them later requires an invariant that depends on it.

**Recording is parent-owned and post-acceptance.** `record` copies facts out of an acceptance that has
already happened; it can refuse but never approve. It requires the task's status to be `accepted`, the
accepted gate to be intact and clean, the contract to be unchanged, a declared review purpose satisfied by
a qualifying role, the artifact to lie inside the contract's declared write boundary when one exists, and
every named dependency to be currently valid. A worker cannot forge a ledger entry through ordinary
bounded mutation: the ledger path is outside its `Allowed source changes`, so the inherited
`WRITE-RESTRICTION` fails the attempt before any acceptance can exist (`I6`).

## A2. Derived validity and dependency closure

*Normative. No validity state is ever stored (`P3`); all three are computed.*

Precedence, in order:

1. own content does not match the accepted identity → **`invalid`**
2. a dependency's accepted identity moved, or anything in the dependency closure is not valid →
   **`needs-revalidation`**
3. otherwise → **`valid`**

`invalid` means *this is not the artifact that was accepted*. `needs-revalidation` means *this artifact is
intact, but the ground it was reviewed against moved*. An invalid dependency therefore does not make its
dependents invalid — it makes them need re-review, which is the honest engineering statement. Results
carry reasons, not bare labels.

**Closure is transitive, and this is not optional.** Consider A accepted at H1, B depending on A@H1, C
depending on B@HB. If A drifts, every *direct* edge in the ledger still matches its recorded target, so a
direct-edge validator reports C valid. It is not: the ground under B moved, and C was reviewed against B.
Validity requires the full dependency closure, with explicit cycle detection — a cycle is a malformed
ledger and fails before any state is derived, because a plausible-looking state from an undefined closure
is worse than no state. Resolution is ordered dependencies-first so a deep chain cannot exhaust the
interpreter stack.

Byte-identical re-authoring is inert: identity is content, not attempt, so re-accepting unchanged text
leaves every dependent valid.

### 27.4 The trust boundary, restated after implementation

| Level | Requires | Proves |
|---|---|---|
| Structural | A clean Git checkout, nothing else | Content identity matches the accepted identity; dependency closure is consistent; the ledger schema, purpose vocabulary and purpose→role relation are internally coherent |
| Provenance | Retained execution evidence | The recorded integrity gate still exists, is byte-identical, is clean, and records the role the ledger claims |
| Neither | — | That the review actually happened, or who performed it |

A committed SHA-256 is **integrity, not authority**. Anyone with repository write access can hand-write
an internally consistent false ledger. Git review and retained run evidence are the mitigations.
Proofbound has no signing keys and no trust roots, and claims none.


### 36.3 Applicability is not a dependency edge

The tempting shortcut — model "decision D applies to artifact A" as a dependency edge — is wrong, and
recognizing why sharpens the model.

A dependency edge means *"I was reviewed against this exact content; if it moves, I need revalidation."*
Applicability means *"this constraint governs this region of the repository."* If applicability were a
dependency edge, superseding one decision would mark every artifact in its scope `needs-revalidation`.
Sometimes that is right. As a default it is catastrophic — a single retry-policy update would invalidate
an entire subsystem's specification set, and the model would be abandoned within a week.

They also differ in shape: dependencies are artifact→artifact; applicability is decision→*scope*, and
scope is a region, not a node.

So: **a separate relation, deferred.** Its likely form reuses an existing pattern — a declared path-prefix
set, exactly like `Allowed source changes`: authority declares it, Python compares prefixes, nothing is
interpreted (P1). Selecting the applicable decisions for a task then becomes a prefix intersection
against the task's scope, which is what makes [§28](context-economy.md#28-context-economy-and-refactoring-economics)'s progressive disclosure implementable.

The honest limit: some scopes are conceptual ("everything doing authorization") rather than path-shaped.
Those can be stated in prose and reviewed semantically, but they cannot be mechanically selected. The
architecture should not pretend otherwise, and should prefer path-shaped scope where it is truthful.


### 40.3 Consequences for M2B

**M2B's scope does not change.** Decision provenance, drift detection and coherence audit stay out. Part
II imposes two constraints on the artifact graph and answers one question that would otherwise be
discovered late:

- **The graph stays generic.** Artifact kinds may label nodes and drive required-set validation, but
  dependency edges must remain plain path→identity relations with no kind-specific semantics, so decision
  artifacts can join later without a schema break ([§36.2](long-running-autonomy.md#362-a-decision-is-an-artifact)).
- **Applicability is not a dependency edge** (§36.3). M2B must not model any decision-like "governs"
  relation as a dependency, and should not add a second edge type speculatively either.


### 40.4 Questions flagged for M2C

Freeze design must answer these; they are not answered here, and only the last has a forced answer.

1. Does freeze bind only proposal/design/spec/tasks?
2. Does freeze also bind the applicable architectural decisions?
3. How is the applicable decision set determined — declared, or derived from scope intersection?
4. Does consistency reflection cover decisions as well as primary artifacts?
5. May a decision be superseded while implementation tasks remain bound to an older freeze?
6. What happens when a new decision invalidates only part of a frozen task graph?
7. Does the initial implementation conservatively invalidate all tasks bound to a superseded freeze?

On (2) and (3), one leaning is already forced by existing architecture rather than by preference: a freeze
should bind **the accepted identities of the applicable decisions**, not their contents and not a
separately stored decision-set identity. Binding contents duplicates them; a stored set identity is a
second truth that can disagree with the set (P3). Binding identities gives a derived set identity for free
via the freeze's own canonical hash.

On (7), conservative invalidation is the safe default and should be the initial behavior — but note it
interacts badly with (6): if a narrow decision invalidates a wide task graph, the model becomes expensive
enough to be worked around, which is its own failure. That tension is real and should be designed
explicitly rather than discovered.

## A3. The change graph (M2B — IMPLEMENTED)

*Normative. Implemented in `scripts/_change_graph.py` and `scripts/pb_graph.py`; this states what it
guarantees. Corrections implementation forced on the design check are in [A3.9](#a39-corrections-from-implementation).*

### A3.1 What M2A cannot answer

M2A validates relationships that were **already recorded**. It cannot answer a different class of
question, because nothing in the system declares the answer:

*Which artifacts were required for this change? Which dependency edges were supposed to exist? Is an
expected artifact missing? Is an unexpected one present? Was design deliberately omitted, or forgotten?*

The ledger is a set of accepted records with no notion of completeness. Ask it "is this change's
engineering contract complete?" and it has no opinion, because nothing ever stated what complete means.

M2B supplies exactly that missing statement — and nothing more. Proofbound will be able to prove:

> authority declared graph G, and the repository satisfies G

It will **not** claim:

> G was the correct engineering decomposition

The second is semantic and stays with humans and agents (`P1`). Declaring a graph is an act of authority,
not a judgement Python makes or reviews.

### A3.2 Three relations, kept apart

| Relation | Shape | Means | Status |
|---|---|---|---|
| **Dependency** | artifact → artifact@identity | *A's accepted meaning was established against this exact content.* If it moves, A may need revalidation. | M2A, extended by M2B |
| **Membership / required topology** | authority → set of nodes and required edges | *These artifacts and these edges constitute this change's contract candidate.* | **M2B** |
| **Applicability** | decision → scope | *This policy governs work in this region.* | **Deferred** (§36.3) |

Collapsing the second into the first is the error M2B most needs to avoid. A graph declaration says what
*should* exist (`L1` intent); a ledger record says what *has been accepted* (`L4` provenance). They are
different truth layers and must not become one mutable object.

### A3.3 The v1 representation

One new committed file per change, beside its ledger:

```
specs/<change-id>/graph.json     intended topology     (L1)
specs/<change-id>/ledger.json    accepted records      (L4)
```

```jsonc
{
  "format": "proofbound-change-graph-v1",
  "artifacts": {
    "specs/CH-001/proposal.md":      [],
    "specs/CH-001/design.md":        ["specs/CH-001/proposal.md"],
    "specs/CH-001/specification.md": ["specs/CH-001/proposal.md", "specs/CH-001/design.md"]
  }
}
```

**Two fields.** Membership is the key set; required topology is the values. Merging them into one map is
not tidiness — it makes "every edge has a declared source" true *by construction* instead of being a rule
that has to be checked and can be got wrong.

| Field | The invariant it enables |
|---|---|
| `format` | Historical semantics (`P6`). v1 means *exact*; a future v2 must not silently reinterpret it. Unknown version fails closed. |
| `artifacts` | Membership — without it there is no required set, and completeness is undefinable. Values give required edges — without them, topology is unstated and a missing dependency is undetectable. |

Rejected, each because no invariant depends on it: **`change_id`** (the directory already says it — see
A3.4), **artifact `kind`** (A3.8), **`graph_sha256`** (self-hashing; computable externally),
**revision/timestamps** (Git), **labels/descriptions**, **any status field** (`P3`), **review metadata**
(the contract and ledger own it), **freeze metadata** (M2C), **profile** (A3.8).

Serialization is canonical: UTF-8, `sort_keys=True`, 2-space indent, trailing newline, sorted dependency
lists, duplicates rejected, unknown fields rejected. Paths are one normalized repository-relative POSIX
form; `./x`, `a/../a`, backslashes, absolute paths and `..` are **rejected rather than normalized**, so an
artifact has exactly one legal spelling. Two entries that differ only by case are rejected together,
because on a case-insensitive filesystem they would name one file and the graph would be ambiguous.

Graph identity, when M2C needs it, is `artifact_identity_file(graph.json)` — the existing
`proofbound-artifact-text-v1` protocol applied to a canonical text file. No new protocol, and nothing
stored inside the file about itself.

### A3.4 Membership, dependency targets, and what "exact" means

A dependency target need **not** be a graph member. This distinction costs no syntax: members are keys,
targets are values, and a target that is not a key is external.

```
specs/CH-001/specification.md  ->  specs/CH-001/design.md      member,  inside the graph
specs/CH-002/spec.md           ->  specs/CH-001/design.md      external, accepted elsewhere
```

The ledger already forces the useful constraint here: `load_ledger` rejects a dependency on any artifact
absent from the same ledger, so **the ledger is a closed dependency universe**. An external target must
therefore have an accepted record in the same ledger — which is exactly the right requirement, since
without one it has no accepted identity to depend on. Cross-change composition consequently works if and
only if the composing changes share a ledger. M2B does not decide whether ledgers are per-change or
project-wide; it must simply not foreclose the project-wide case, and this model does not.

**Exactness is narrow and deliberate.** v1 semantics:

> Within the graph's scope, the declared nodes are exactly the change's contract-candidate artifacts, and
> the declared edges are exactly the dependency edges its members may record.

Scope is the graph file's own directory, derived — not a field, so it cannot disagree with reality. Every
member must lie within it. Exactness is evaluated over **ledger records**, never over the filesystem: a
`notes.md`, a screenshot, or a research scratchpad in the same directory is not a graph member and is not
a finding, because it was never accepted into the durable record. Directory membership never implies graph
membership (`P11`); authority comes from declaration and acceptance.

This narrowness answers most objections to exact graphs. The remaining cost is real: authority must
declare every dependency edge, including external ones. That is accepted, because the alternative — a
minimum graph — lets a worker's accepted record add contract topology that authority never declared, which
is `P7` violated at the level of the contract itself.

### A3.5 Graph satisfaction is not artifact validity

**The most important statement in this section.** M2A's three states describe an *artifact*. Graph
satisfaction describes a *topology*. They are orthogonal, and M2B must not widen `needs-revalidation` to
mean "the workflow now expects another artifact".

| Situation | Artifact structural validity | Graph satisfaction | Provenance | Re-author? | Re-reflect? | Freeze later |
|---|---|---|---|---|---|---|
| Declared, file missing | `invalid` (missing from tree) | unsatisfied | unchanged | yes | yes | blocked |
| File exists, never accepted | no record to evaluate | unsatisfied — `missing-artifact-record` | none yet | no | yes (first review) | blocked |
| Accepted and current | `valid` | satisfied, if all members are | per `L3` | no | no | eligible |
| Own content moved | `invalid` | unsatisfied | unchanged | yes, or restore bytes | yes | blocked |
| A dependency's identity moved | `needs-revalidation` | unsatisfied | unchanged | no | yes | blocked |
| **Graph adds a sibling node** | **unchanged — existing members stay `valid`** | unsatisfied — `missing-artifact-record` for the new node | unchanged | no | **no, not for the siblings** | blocked until accepted |
| **Graph adds a dependency to an existing node B** | **B stays `valid` — its bytes did not move** | unsatisfied — `missing-required-edge` | unchanged | no | **yes — B must be re-accepted against the new dependency set** | blocked |
| Graph removes a dependency from B | B stays `valid` | unsatisfied — `undeclared-edge` | unchanged | no | yes, to re-accept without it | blocked |
| Graph removes a node | others unchanged | unsatisfied — `undeclared-member` until the record is withdrawn | unchanged | no | no | blocked |
| Ledger has an undeclared member in scope | that artifact may be `valid` | unsatisfied — `undeclared-member` | unchanged | no | no | blocked |
| Ledger has an undeclared edge | source may be `valid` | unsatisfied — `undeclared-edge` | unchanged | no | yes | blocked |
| External dependency moves | dependents → `needs-revalidation` via closure | unsatisfied | unchanged | no | yes | blocked |
| Graph declaration changes | **unchanged** | recomputed against the new graph | unchanged | no | only where edges changed | binds the new graph identity |
| Run evidence disappears | **unchanged** | **unchanged** | → `unavailable` | no | no | structurally fine, unverifiable |

Two rows carry the design. Adding a *sibling* must not disturb anyone — topology grew, no artifact's
reviewed context changed. Adding an *edge to B* must require B's re-review even though B's bytes are
identical, because B's authoritative dependency context expanded and its accepted record no longer
reflects the contract. Python reaches that conclusion by comparing a declared edge set against a recorded
one — never by knowing what a "design" is.

Note also what collapses: M2A already reports a declared-but-missing file as `invalid` with a reason, so
"materialized" needs no separate check. The useful observations are **declared** (graph), **accepted**
(a ledger record exists), and **structurally current** (M2A state). All three are derived; none is stored.

### A3.6 Findings

The validator takes graph `G`, ledger `L` and repository `R` and returns findings — a code, the paths
involved, and a reason. Not prose, and not a lifecycle.

`unknown-graph-format` · `illegal-path` · `member-outside-scope` · `graph-cycle` ·
`missing-artifact-record` · `artifact-not-valid` (carrying the M2A state and its reasons) ·
`missing-required-edge` · `undeclared-edge` · `undeclared-member` · `unknown-dependency-target`

"Satisfied" is the absence of findings; it may appear as a derived output field, mirroring M2A's
`structural_ok`, but it is never stored. **Graph satisfied is a mechanical topology and integrity
property. It does not mean the engineering contract is semantically coherent** — that requires the
aggregate consistency reflection M2C will run, and no amount of green topology substitutes for it
(`P10`).

### A3.7 Ownership, and topology changing under a live attempt

The graph is **parent-owned**, protected by the same inherited mechanism as the ledger: its path lies
outside every worker contract's `Allowed source changes`, so a worker writing it trips `WRITE-RESTRICTION`
before any acceptance can exist (`I6`). No new mechanism, and no way for a worker to enlarge its own
contract by discovering during execution that another artifact "is needed" — that is an escalation, not an
edit (`P7`).

**No global lock, and no graph identity in task contracts.** If authority changes G1 → G2 while an attempt
launched under G1 is running, the attempt completes and is accepted on the terms of its own immutable
contract; whether the resulting record satisfies the *current* graph is a separate question, answered
later by the validator. The honest resulting state is "historically accepted, current graph unsatisfied",
which is informative rather than dangerous. This preserves immutable contracts (`I3`) and avoids inventing
a lock, and it is the reason no `graph_sha256` needs to enter a contract: nothing about accepting an
artifact depends on which topology was current when it launched.

### A3.9 Corrections from implementation

Four design-check statements changed when the code was written. Everything else survived unaltered.

1. **Withdrawal is consistent, and the reason is stronger than the design check knew.** The question was
   whether deleting durable provenance conflicts with supersession-not-mutation. It does not, and the
   proof is in existing behavior: `record` **overwrites** an entry, so a re-accepted artifact's previous
   identity is *already* gone from current state. The ledger is a snapshot of currently accepted
   provenance and Git is the history chain — exactly why M2A rejected a `supersedes` field. Withdrawal is
   that same operation made explicit. `P9` governs future frozen baselines, a different object; applying
   it to every ledger entry would contradict shipped M2A behavior. Withdrawal refuses to orphan a
   dependency, because removing a record another was accepted against leaves the ledger unloadable.
2. **Exactness needed two exclusions the design check did not anticipate.** Proofbound's own control
   files (`graph.json`, `ledger.json`) never count toward exactness and may not be declared as members.
   Without this a record nothing is permitted to declare would make a graph permanently unsatisfiable.
3. **Edge comparison is skipped for a member with no accepted record.** Otherwise a single unaccepted
   artifact produces a missing-record finding *plus* one missing-edge finding per required dependency,
   burying the actual problem.
4. **A self-dependency is reported precisely, not as a cycle.** It is a cycle, but naming it exactly is
   more useful, and both fail closed identically.

**Graph identity is text identity.** `artifact_identity_file(graph.json)` under the existing
`proofbound-artifact-text-v1` — no second hashing protocol. The consequence is deliberate: a
whitespace-only edit is a new graph identity. Semantic-graph identity would avoid that at the cost of a
new canonicalization protocol, and this project has repeatedly been right to refuse unnecessary
normalization. Nothing in M2B consumes graph identity; M2C will, and it is available with no new code.

**External dependency support, stated exactly.** The format permits an edge to any target. The v1
validator resolves a target only within the ledger it is given: a target that is a member is internal, one
that is in the same ledger but outside the graph's scope is external and legal, and one that is in neither
is `unresolved-dependency-target`. A path merely existing in the repository is never a legal target — it
has no accepted identity to have been reviewed against. **Cross-change composition therefore works if and
only if the composing changes share a ledger**, since `load_ledger` requires every dependency target to be
a key in the same file. M2B does not decide whether ledgers are per-change or project-wide, and does not
foreclose either.

### A3.8 What M2B does not do

**No artifact kinds.** Every candidate invariant was tested and none requires them: review purpose is
declared in the contract and must never be inferred from a filename (`P2`, and the registry in
[execution-and-review.md §27.1](execution-and-review.md#271-decision-resolved--the-review-purpose-vocabulary-is-fine-grained));
freeze ordering
comes from the dependency DAG; consistency review reads the aggregate; decision artifacts are explicitly
easier without kinds. Paths already carry human meaning. A kind would be a taxonomy Python does not need,
and taxonomies attract behaviour.

**No profiles.** Authority declares the graph directly. If named templates ever appear they must be pure
data expansion into an explicit graph — never a policy language, never complexity scoring, never anything
that picks a workflow by judging the change.

**No readiness scheduler.** A derived "nodes whose dependencies are satisfied and whose own record is
missing" set is computable and may be useful to the parent later, but it must never rank or prioritize,
and M2B does not need it.

Also out: freeze and binding, aggregate identity, decision provenance, applicability, supersession,
consistency-reflection execution, coherence audit, telemetry, human gates, provider routing, worktrees.

## A4. Freeze and binding (M2C — designed, not implemented)

*Normative direction. No production code implements any of this. Builds on [A1](#a1-the-durable-change-ledger-v1),
[A2](#a2-derived-validity-and-dependency-closure) and [A3](#a3-the-change-graph-m2b--implemented); those are not restated here.*

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

# Artifacts and provenance

> **Normative.** What an accepted specification artifact is, how its identity is computed, what the
> durable ledger records, how validity is derived, and what the two validation levels can and cannot
> prove. Also the constraints this places on the artifact graph (M2B) and freeze (M2C).
>
> Entry point: [README.md](README.md).

### 27.2 Decision resolved — canonical text identity, and why `-text` was rejected

None[§26](evidence/implementation-findings.md#26-m2-design-check) suggested marking spec artifacts `-text` in `.gitattributes` because artifact hashes were to be
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

The ledger is the durable-provenance layer `L4` ([core-model.md None[§31](core-model.md#31-the-truth-model--four-layers)](core-model.md#31-the-truth-model--four-layers)):
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
against the task's scope, which is what makes None[§28](context-economy.md#28-context-economy-and-refactoring-economics)'s progressive disclosure implementable.

The honest limit: some scopes are conceptual ("everything doing authorization") rather than path-shaped.
Those can be stated in prose and reviewed semantically, but they cannot be mechanically selected. The
architecture should not pretend otherwise, and should prefer path-shaped scope where it is truthful.


### 40.3 Consequences for M2B

**M2B's scope does not change.** Decision provenance, drift detection and coherence audit stay out. Part
II imposes two constraints on the artifact graph and answers one question that would otherwise be
discovered late:

- **The graph stays generic.** Artifact kinds may label nodes and drive required-set validation, but
  dependency edges must remain plain path→identity relations with no kind-specific semantics, so decision
  artifacts can join later without a schema break (None[§36.2](long-running-autonomy.md#362-a-decision-is-an-artifact)).
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

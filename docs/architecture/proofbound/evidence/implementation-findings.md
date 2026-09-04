# Implementation findings (M0–M2A)

> **Historical evidence.** What implementation actually proved, and where it corrected the design. This is
> *why we trust* the rules in the normative documents; the rules themselves live there. Read this when you
> need the reasoning behind a constraint, not to discover what the constraint is.
>
> Entry point: [../README.md](../README.md).

## 30. Reconciliation — what implementation settled

Implementation evidence outranks design intent. This section records where M0–M2A changed the
architecture, not merely where it confirmed it.

### 30.1 M0 — historical protocol semantics are a protocol concern

A newer harness must never reinterpret older persisted evidence according to the current registry. The
worker-rules manifest recorded protocol *membership* but not its *order*, while the fingerprint was
order-dependent — so adding a role silently invalidated every historical snapshot. The repair was not to
regenerate snapshots or relax the check but to judge each snapshot by the protocol identity it recorded
and then *prove* that reconstruction by reproducing its fingerprint.

The generalizable finding: **ordering, membership and schema details that participate in an identity are
protocol, not implementation trivia.** Any format that will be verified later must record every input to
its own identity, explicitly, from v1. M2A's ledger applies this directly — it carries both a schema
version and a separately versioned artifact-identity protocol, because the two evolve independently.

### 30.2 M1 — capability and purpose are different questions

`reviewer` and `spec-reflector` are mechanically interchangeable at acceptance: both carry the
independent-review capability. Nothing in the mechanics distinguished *why* a review happened. M1 proved
the capability half and left the purpose half open; M2A closed it (None[§27.1](../execution-and-review.md#271-decision-resolved--the-review-purpose-vocabulary-is-fine-grained)).

M1 also corrected the repair model. Reflection findings do **not** require a new contract revision: a new
*attempt* under the unchanged contract is the unit of repair history, and rebinding the contract would
drop earlier mutating attempts from the freshness scan — making the repair loop actively unsafe. Attempts
are repair history; contract revisions are changes of intent.

And the parent does not re-review worker semantics after a qualifying independent review. Its input is
gate JSON and a bounded surface, never a reflection transcript.

### 30.3 M2A — the durable/execution boundary

M2A established the split Part II is built on. Durable provenance is *project* state, version-controlled
and small. Run evidence is *execution* state, large and eventually deleted. Structural validity survives
the loss of run evidence; provenance verification cannot, and must say so rather than degrading into a
false claim either way.

Three findings are load-bearing beyond M2A:

1. **Provenance needs three values.** `verified`, `unavailable`, `contradicted`. Absence and contradiction
   are not the same signal, and neither is an artifact-validity verdict (None[§32](../core-model.md#32-three-independent-dimensions)).
2. **Dependency validity is transitive.** A direct-edge validator reports a downstream artifact valid when
   every recorded edge still matches its target and the ground two levels up has moved. Closure is
   required, and it needs a topological pre-pass rather than recursion.
3. **Hashes are integrity, not authority.** A committed ledger is not a signature. Anyone with write access
   can produce an internally consistent false one.

### 30.4 Gaps and statements this closes or supersedes

| Earlier statement | Status |
|---|---|
| None[§4](original-rfc.md#4-problem-statement--gaps) **G4** — independence is mechanical for code but only doctrinal for documents | **Closed by construction.** Specification artifacts live in *project* state, so authoring them moves project scope and `_assert_fresh_reviewer` engages. The gap existed only for artifacts written into the run tree; putting them in the project was the fix, and it required no new independence mechanism. |
| None[§4](original-rfc.md#4-problem-statement--gaps) **G5** — no way to declare in advance that a class of change needs sign-off | **Open, and reframed.** None[§35](../long-running-autonomy.md#35-local-adaptation-escalation-and-promotion) argues the missing piece is not a pre-declared class list but an escalation boundary plus durable decision provenance. |
| None[§4](original-rfc.md#4-problem-statement--gaps) **G3** — traceability stops at the contract | **Partially closed.** M2A gives artifact and dependency identity; requirement→task mapping remains M2B/M2C. |
| None[§6](original-rfc.md#6-end-to-end-workflow) and None[§7](original-rfc.md#7-state-machine-design) diagrams — *"findings → new contract revision"* | **Superseded.** Corrected in §25.5 (X1) and restated in §30.2; the diagrams themselves were left unedited. |
| §26 suggestion to mark spec artifacts `-text` | **Withdrawn** by None[§27.2](../artifacts-and-provenance.md#272-decision-resolved--canonical-text-identity-and-why--text-was-rejected). |
| Scattered `I<n>` numbering | **Superseded** by None[§33](../core-model.md#33-consolidated-principles). See the note there. |


## 25. Validation pass (post-authoring review against the checkout)

This section records a second pass in which every load-bearing claim was re-tested against the code at
`c292eb5`, not re-read from documentation. Experiments were run against a scratch project with a fake
`opencode` binary, using the pattern in `tests/test_v15_helpers.py`.

### 25.1 Assumptions confirmed by execution

**C1 — The central thesis holds with no new orchestration.** A full slice was executed end to end:
`spec-author` (confined by `## Allowed source changes` to `specs/CH-001/proposal.md`) → integrity gate →
`spec-reflector` → integrity gate → `accept-task`. It works with exactly two role registry entries,
`spec-author` added to `ALWAYS_PROJECT_WRITER_ROLES`, and one expression changed in
`_assert_fresh_reviewer`. No new state, no new evidence format, no new lifecycle.

**C2 — Self-acceptance is already impossible.** Accepting the `spec-author`'s own gate is rejected by
unmodified `dsd_state.py`: *"recorded project mutation requires a fresh Reviewer integrity gate"*.

**C3 — Mutation confinement is already mechanical.** A `spec-author` that also wrote `src.py` produced
`WRITE-RESTRICTION: 1 path(s) outside explicit Allowed source changes: src.py`.

**C4 — Reflector read-only enforcement is already mechanical.** A `spec-reflector` that edited the
artifact it was reviewing produced `READONLY-SCOPE-MOVED: 1 project path(s)`.

**C5 — Reviewer freshness already covers the revise loop.** After a second `spec-author` attempt changed
the artifact, accepting the *first* reflector's gate failed with *"fresh Reviewer requirement violated:
accepted Reviewer predates later project mutation in spec-author-2"*; a second reflector attempt was
accepted.

**C6 — Role addition breaks historical snapshots.** Reproduced exactly (None[§17.1](original-rfc.md#171-scriptsrulessnapshotpy--blocker-fix-first)), with the five affected
call sites enumerated and `context_checkpoint.py` confirmed unaffected.

**C7 — Existing capability classification is undisturbed.** `role_writes_project` still returns
`implementer=True, fixer=True, verification=True/False by contract, evidence-clerk=False,
reviewer=False`, with `spec-author=True, spec-reflector=False` added.

**C8 — Hot-doc byte caps and the missing baseline.** `SKILL.md` remains exactly at its 7500-byte cap; no
CI, packaging, lint, format, or type configuration exists; only
`tests/test_v15_4_lifecycle_regressions.py` requires Python ≥3.10.

### 25.2 Assumptions corrected

**X1 — The fix loop needs no new contract revision.** The RFC implied a new `spec-author` contract
revision per reflection round. Verified wrong: the correct shape is the existing
Implementer → Reviewer → Fixer → Reviewer pattern — a new *attempt* on the **same** contract with the
reflector's report passed via `--input`. A new revision would additionally be harmful: attempts are
matched to acceptance by contract hash, so rebinding a revision drops earlier mutating attempts from the
freshness scan.

**X2 — The change manifest is a committed project artifact, not run evidence.** Corrected in None[§8.1](original-rfc.md#81-split-markdown-for-reasoning-json-for-bindings)/None[§8.5](original-rfc.md#85-who-writes-the-manifest-and-when).
The run tree is explicitly not project source and is git-ignored, so a manifest living only there could
not establish what a checkout accepted.

**X3 — The artifact model is a DAG, not a chain.** Corrected in None[§8.4](original-rfc.md#84-dependency-dag-and-typed-staleness). `design` and `specification` are
siblings under `proposal`; this is what gives the cross-artifact consistency reflection a purpose.

**X4 — Staleness needed to be typed.** Corrected in None[§8.4](original-rfc.md#84-dependency-dag-and-typed-staleness): `needs-revalidation` (upstream dependency
moved) versus `invalid` (own content changed outside the harness), each reported with its reason.

**X5 — The test blast radius was understated.** Not "four `PROTOCOL_NAMES` constants" but 17 failures
across three modules; deriving the tuple from `_rules_snapshot` reduces it to one assertion (None[§17.1](original-rfc.md#171-scriptsrulessnapshotpy--blocker-fix-first)).

**X6 — The snapshot fix has a non-obvious ordering constraint.** The manifest stores protocol keys
sorted while the fingerprint hashes them in registry order; only ordering by the current tuple restricted
to the recorded set reproduces historical fingerprints (None[§17.1](original-rfc.md#171-scriptsrulessnapshotpy--blocker-fix-first)).

### 25.3 Decisions refined

**A1 — Derived stage, made an explicit invariant.** *Workflow status must be a function of authoritative
artifacts and evidence and must never be an independent source of truth that can disagree with them.*
Three things stay distinct and must not be merged: **execution state** (`state.json` — task/attempt
lifecycle, one `next_action`; DSD's, unchanged), **artifact status** (the committed manifest — accepted
hashes, dependency hashes, provenance references), and **derived workflow stage** (computed, never
stored). No persisted stage field is required.

**D — Freeze identity is the manifest hash, not `specification.md`'s.** Implementation contracts bind the
**aggregate** freeze-manifest hash. Binding `specification.md` alone would permit an inconsistent
combination — a spec revision paired with a drifted design — which is exactly the drift the freeze exists
to prevent. A freeze is immutable and is **superseded by a new freeze**, never edited; the consistency
reflection is a mandatory prerequisite because it is the only step that reconciles the DAG's two
independent branches.

**E — Three honest enforcement tiers.** (1) *Hard enforcement*: `## Allowed source changes` prefix
confinement and read-only capability, both proven above. (2) *DSD-level mutation detection*: the frozen
terminal-bound scope diff catches anything a worker did outside its boundary, after the fact. (3)
*Prompt-level policy*: role doctrine. Tier 1 covers what the harness can prevent at acceptance time; the
harness does **not** sandbox a worker's shell, and this RFC does not claim it does.

**F — The runtime seam is right, but is not M1.** `resolve_runtime(state, role)` replacing
`opencode_runtime(...)` remains the correct destination, with `native_worker_attempt.py` as the existing
generic transport. It is **not** needed for the vertical slice and moves to a later milestone.

**G — Monotonic policy.** `effective_policy ⊇ repository_minimum_policy`. Repository policy establishes
the minimum required gates; run configuration may add gates but never remove one. Explicit human
authorization satisfies a gate for the change it names — it does not lower the policy for later changes.
This matches DSD's existing precedence, where run worker-rules *narrow* but never contradict protocol.

**J — Do not reintroduce a Decision Packet.** DSD deleted `decision_packet.py` in v15.3–v15.4 and pins its
absence (`test_v15_4_consolidation.py::test_executable_semantic_parser_surface_is_absent`). The existing
equivalents are already correct and must be reused unchanged: `dsd_attempt.py gate --surface` for a
bounded non-semantic prefix, the read-only Evidence Clerk when that prefix is insufficient, and the
worker-side `DECISION_REQUIRED` prose convention for escalation. The parent's compact input for
specification work is therefore the manifest plus a bounded gate summary — never a reflection transcript.

**N — Project mutations serialize; worktrees are deferred.** Because spec authoring is a project mutation
it takes DSD's existing scope-exclusivity constraint (I12). The initial position is explicit:
**deterministic mutation provenance is preferred over concurrent spec-authoring and implementation in one
checkout.** Worktrees remain a documented later extension point and are out of scope for M0/M1.

**O — Upstream classification of every M0/M1 change.**

| Change | Class |
|---|---|
| Historical rules-snapshot verification fix | 1 — generic DSD correctness fix, should be offered upstream |
| Test fixtures deriving `PROTOCOL_NAMES` | 1 — generic hygiene, should be offered upstream |
| Interpreter pin, canonical test command, CI | 1 — generic, upstreamable |
| `INDEPENDENT_REVIEW_ROLES` | 2 — neutral extension point (any harness adding a review role needs it) |
| `resolve_runtime(state, role)` | 2 — neutral extension point (later milestone) |
| `spec-author` / `spec-reflector` roles and skills | 3 — project-specific |
| Change manifest, freeze, contract spec binding | 3 — project-specific |

### 25.4 M0 and M1 outcomes (post-validation)

M0 and M1 have since been implemented against this baseline; the implementation plan [§0](../README.md#0-project-identity-boundary), None[§3](../execution-and-review.md#3-existing-invariants-that-must-be-preserved) and None[§4](original-rfc.md#4-problem-statement--gaps) are
authoritative for what was built. Two findings in §25.2 were superseded by M0 and are corrected here:

- **X5 (test blast radius)** was a *symptom*, not a separate problem. After the historical-snapshot fix,
  adding two roles causes **zero** test failures, so the planned fixture-derivation change was dropped.
- **The interpreter claim in None[§1](original-rfc.md#1-executive-summary)** conflated the development machine's system `python3` (3.9.6) with the
  supported interpreter. The inherited suite is 82 tests green and unmodified on Python 3.10–3.14; the
  supported minimum is now declared ≥3.10 and no test module needed repair.

**M1 confirmed the central thesis at a smaller cost than this RFC predicted.** The production change was
18 inserted and 4 deleted lines across `scripts/_roles.py` and `scripts/dsd_state.py`, plus two role
protocol files. Every rejection in the 12-step acceptance scenario — self-acceptance, stale reflection,
mutating reflector, stray author write — came from inherited DSD enforcement with no Proofbound-specific
check. The one architectural refinement it forced is recorded in None[§9.1](original-rfc.md#91-two-review-classes-deliberately-not-collapsed): independent-review *capability* is
shareable and mechanical, while review *purpose* is doctrinal and stays a parent role choice.

### 25.5 Unresolved architectural questions

Reduced from None[§23](original-rfc.md#23-open-questions-requiring-human-architectural-input) to those repository evidence genuinely cannot answer (the interpreter question
was since decided in M0):

1. **Committed spec root path and naming** — `specs/<change-id>/` versus an existing convention the target
   repositories already use. Everything else in this design is path-agnostic.
2. **Gate policy vocabulary ownership** — who curates the closed classification tag set, and whether a
   repository may define its own tags.
3. **Reflection round cap and its escalation** — a policy number, plus whether exhaustion is
   `human-blocked` or a recorded parent decision.
4. **Whether generic fixes are offered upstream** — a project-direction decision (§25.3, Objective O),
   not a technical one.

Questions 1–3 do not block M0. Question 1 blocks the *end* of M2, not its start.

---


## 26. M2 design check

Baseline inspected: `efddc5307681acb70dbc2cfcb1cd43f0183bc37b` (clean, in sync with `origin/main`,
118 tests green on 3.10 and 3.14). This section records a design-only pass. Nothing here is
implemented.

**Where this section differs from §None[§5](original-rfc.md#5-proposed-target-architecture)–17, this section governs.** Those sections were written before
M1 existed and are kept for their reasoning, not as current specification. Specific supersessions:

| §None[§5](original-rfc.md#5-proposed-target-architecture)–17 said | §26 says | Why |
|---|---|---|
| `dsd_spec.py` | `pb_ledger.py` (+ `pb_purpose.py`) | The change ledger is a Proofbound-native concept, not an inherited DSD identifier; the `dsd_` prefix is reserved for compatibility-sensitive inherited names |
| `specs/<id>/manifest.json` | `specs/<id>/ledger.json` | "Manifest" is now reserved for the immutable freeze manifest, whose canonical hash is an identity; the ledger is mutable and is not content-addressed |
| Ledger records `revision`, `status`, `accepted_at`, `authored_by`, `supersedes`, `pending_gates` | Four keys per artifact only | Each dropped field failed the "which invariant becomes harder?" test (§26.2) |
| Artifact `status` stored in the ledger | Validity is derived, never stored | I3 |
| "the review has PASS" | "the parent accepted, citing a qualifying gate" | There is no PASS field in DSD, by design (§26.1) |
| One M2 milestone | M2A / M2B / M2C | I9: the original M2 coupled three unproven theses |

### 26.1 Validated against current code

- `spec-author ∈ ALWAYS_PROJECT_WRITER_ROLES`; `spec-reflector` is read-only by the computed
  complement; `INDEPENDENT_REVIEW_ROLES = {reviewer, spec-reflector}` has exactly one production
  consumer, in `_assert_fresh_reviewer`.
- `accept_task` persists provenance as `{source_gate, semantic_report, semantic_gate}` — path plus
  SHA-256 — **into the run tree's `state.json` only**. Nothing reaches version control.
- The integrity gate already records `role`, `task` + `task_sha256`, `report_sha256`,
  `launch_reservation` + hash, and the frozen scope summary. Review **role** is therefore already a
  durable mechanical fact; review **purpose** is recorded nowhere.
- **There is no PASS field anywhere, by design.** DSD never records a verdict
  (`test_acceptance_binds_semantic_evidence_without_storing_verdict`). The mechanical fact is *the
  parent accepted this task citing this gate*. Any M2 clause phrased as "the review has PASS" must be
  restated as "the parent accepted, citing a qualifying gate", or it invents a field the
  architecture deliberately removed.
- `_contract.markdown_section` / `_bullet_values` already parse an arbitrary `## Heading` bullet
  section; a declared-purpose section needs **no new parser**. `accept_task` already resolves the
  contract path immediately before calling `_assert_fresh_reviewer`, which is exactly where a purpose
  check belongs.

### 26.2 Corrected assumptions

**A1 — "the review has PASS" is not available.** See above. Acceptance is an act, not a stored
verdict. The ledger records that the act occurred against a specific gate.

**A2 — Several fields the RFC previously sketched do not survive the "which invariant becomes
harder?" test and are dropped:**

| Dropped field | Why |
|---|---|
| `accepted_at` | No mechanical invariant depends on it. Ordering is established by DSD freshness at acceptance time; dates are in Git history. |
| `supersedes` / prior accepted hash | The ledger file's own Git history is the version chain. Duplicating it adds a field that can disagree with Git. |
| `author.attempt` | Derivable: the reviewer gate binds the contract, the contract locates the task directory, and every attempt lives under it. Recording it adds a second place to be wrong. |
| artifact `kind` | Nothing in M2A validates graph shape, so kind buys nothing yet (§26.6). |
| revision counters | I4: attempts are the unit of repair history, not contract revisions. |

**A3 — "proposal changed" and "artifact edited outside the harness" are the same mechanical event**
(recorded hash ≠ current hash). They differ only in whether the ledger was updated in the same act.
The design must not pretend Python can distinguish an authorized edit from an unauthorized one by
inspecting the file; it distinguishes them by whether an acceptance record accompanied the change.

### 26.3 Four concepts, kept separate

| Concept | Where it lives | Who decides |
|---|---|---|
| Artifact **content** | project tree, Git | agents / humans |
| Artifact **identity** | content SHA-256 + recorded dependency hashes | Python |
| Review **capability** | `INDEPENDENT_REVIEW_ROLES`, scope confinement, freshness | Python (inherited, unchanged) |
| Review **purpose** | *declared* in the task contract, recorded in the ledger | parent declares; Python checks the declaration against a static table |

### 26.4 Review-purpose model — the central M2 decision

M1 exposed that capability alone lets a `reviewer` gate accept a specification mutation and a
`spec-reflector` gate accept an implementation mutation. The fix must not have Python read prose.

**Mechanism.** The task contract declares one purpose in a `## Review purpose` section. A static
table maps each purpose to the roles permitted to serve it. `accept_task`, immediately beside the
existing freshness assertion, checks that the accepted gate's `role` is permitted for the declared
purpose. An absent section preserves today's behavior exactly, so every existing contract and test
is unaffected.

```text
purpose (declared, closed set)      permitted roles
---------------------------------  --------------------
proposal-reflection                {spec-reflector}
design-reflection                  {spec-reflector}
specification-reflection           {spec-reflector}
consistency-reflection             {spec-reflector}
implementation-review              {reviewer}
```

Python knows: the declared string, the role in the gate, and a constant table. Python does **not**
know whether `design.md` "looks architectural". I1 holds.

**Honest limitation, stated up front.** Today the first four entries are *enforcement-equivalent* —
they all resolve to `{spec-reflector}`. Only the specification/implementation split is actually
enforced. The finer names are recorded, not enforced. That is deliberate: the recorded value is what
M2B's graph validation will key on, and adding it now avoids retro-classifying ledger entries later.
But it is the weakest element of this model, and the two-value alternative
(`specification-reflection` | `implementation-review`) is a legitimate choice — see §26.9.

**What this does not do.** It does not prove the reflector applied design-reflection *reasoning*.
Nothing mechanical can. It proves the contract declared a purpose, and a role permitted for that
purpose served it.

### 26.5 The durable change ledger

**Why a committed ledger is necessary** (the strongest falsification attempt): everything else is
already recorded somewhere. Git versions the artifact; the run tree records acceptance. What no
existing store provides is **the binding between an artifact and the upstream content it was
reviewed against, surviving into a clone where the run tree is absent.** Staleness is inherently
cross-run and cross-machine — a proposal edited months later, in a different run, must invalidate a
design's reflection. Without a committed record of what the design was accepted against, that is
unprovable. That single invariant justifies the ledger; nothing else in it does.

One file per change, `specs/<change-id>/ledger.json`, so changes do not contend for one file:

```jsonc
{
  "format": "proofbound-change-ledger-v1",
  "change": "CH-001",
  "artifacts": {
    "specs/CH-001/design.md": {
      "content_sha256": "b1c2…",
      "depends_on": { "specs/CH-001/proposal.md": "a0f3…" },
      "review": {
        "purpose": "design-reflection",
        "role": "spec-reflector",
        "gate": "phases/spec/tasks/CH-001-design/attempts/spec-reflector-2/evidence-gate.json",
        "gate_sha256": "9d7e…"
      }
    }
  }
}
```

Four keys per artifact. Each survives the invariant test: `content_sha256` → drift detection;
`depends_on` → needs-revalidation; `review.purpose` + `review.role` → purpose provenance checkable
without the run tree; `review.gate` + hash → the pointer into run evidence for full provenance
validation. `gate` is **run-relative**, not absolute — an absolute machine path is noise in a
committed file.

**Who writes it.** A parent-only Proofbound helper, mirroring `dsd_state.py`'s posture. Two rules
make that safe, both inherited: every spec task's `## Allowed source changes` names only the artifact
being authored, so `ledger.json` is outside the boundary and a worker touching it is a
`WRITE-RESTRICTION` failure; and the parent writes it **between attempts**, because a parent write
during a live read-only attempt would appear in that attempt's frozen scope diff and trip
`READONLY-SCOPE-MOVED`. This is I12 applied, not a new rule.

**Not a second acceptance engine (I6).** The ledger records what DSD already established. It performs
no freshness check, no scope check, no role-capability check of its own. Its only independent
computation is derived validity (§26.7), which is arithmetic over recorded hashes.

### 26.6 Is artifact kind mechanical?

**Not yet.** Kind buys exactly one thing — validating graph *shape* ("tasks must depend on an
accepted specification") — and no such validation exists in the first slice. Dependencies are
declared explicitly per artifact by path and hash, which is strictly more general. The declared
purpose vocabulary already carries a coarse kind signal for free. Make kind first-class in M2B, when
something actually validates the graph. Knowing an artifact *is* a design may reasonably be
mechanical; knowing the design is *correct* never is.

### 26.7 Staleness, defined mechanically

Two **local** conditions plus a **transitive** rule. All are derived; nothing is stored (I3).

| State | Trigger | Re-author? | Re-reflect? | Old provenance |
|---|---|---|---|---|
| `accepted` | `sha256(file) == content_sha256`, every `depends_on` hash equals that dependency's current recorded `content_sha256`, and every dependency is recursively `accepted` | — | — | current |
| `invalid` | `sha256(file) != content_sha256` (or file missing) | yes, or revert | yes | retained in Git history; no longer current |
| `needs-revalidation` | own hash matches, but a `depends_on` hash no longer matches the dependency's recorded accepted hash | **not necessarily** | yes | retained |

**The transitive rule matters and closes a real hole.** If `proposal` is `invalid`, `design`'s
recorded dependency hash still matches proposal's *recorded accepted* hash — so `design` would look
fine. It is not. An artifact is `accepted` only if it is locally accepted **and** its full dependency
closure is accepted. Report the reason chain, not just the state.

Against the prompt's cases: **A** proposal content changes and is re-accepted → design
`needs-revalidation`, not `invalid` — its own bytes are untouched, only the ground it was reviewed
against moved. **B** design edited outside an author attempt → `invalid`, because no acceptance
record accompanied the change. **C** byte-identical re-author → hash unchanged → nothing invalidated;
M1 already proved DSD's content-based scope treats a byte-identical rewrite as no mutation. **D** spec
changes → tasks `needs-revalidation`; design unaffected (siblings). **E** task wording changes with
identical meaning → `invalid`, and a fresh reflection is required. Proofbound cannot and must not
guess semantic equivalence; the cost of a cheap re-reflection is the price of mechanical
enforceability. The wrong fix would be a "re-accept without re-review" escape hatch, which would
break I6.

### 26.8 Direction for freeze and binding (M2C, not designed here)

Confirmed direction, deliberately not detailed: an **immutable freeze manifest** aggregating the
accepted hashes of all authoritative artifacts, whose own canonical hash is the freeze identity.
Binding `specification.md` alone permits an inconsistent combination — spec revision *n* paired with
a drifted design — which is precisely the drift a freeze exists to prevent. Implementation contracts
bind the freeze identity, and because DSD already hashes the contract into every
`launch-reservation.json`, "which accepted contract did this attempt run against" stays a
cryptographic fact with no new protocol.

The **candidate-aggregate** idea for consistency reflection looks right and should be evaluated in
M2C: reflect against an aggregate identity, so that any artifact change changes the aggregate and
invalidates the consistency review automatically, rather than marking it stale by a separate rule.
It is the same content-addressing trick applied one level up.

Post-freeze changes create a **new freeze that supersedes the old**; freezes are never edited. First
implementation should **conservatively invalidate every task bound to the superseded freeze**;
selective preservation of tasks whose dependency closure is unchanged is an optimization, not a
correctness requirement, and belongs later.

### 26.9 Canonical serialization and schema evolution

The M0 protocol-snapshot defect was caused by a hash whose ordering input was implicit. Apply the
lesson from v1:

- **Hash the canonical serialization of the parsed object, never the file bytes**, so pretty-printing
  for diffability cannot change identity: UTF-8, `sort_keys=True`, `separators=(",", ":")`,
  `ensure_ascii=False`, no trailing newline. Sorting removes any hidden ordering input — the exact
  failure M0 had.
- **Artifact content hashes are over raw file bytes**, matching the inherited `sha256_file`. This
  makes them sensitive to line-ending translation; ship a `.gitattributes` entry marking spec
  artifacts `-text` so a Windows checkout cannot silently change every accepted hash. *This is a
  concrete, easily-missed footgun of the same family as the M0 bug.*
- Paths: repository-root-relative, POSIX separators, no `./`, no `..`.
- **Format identity from v1** (`proofbound-change-ledger-v1`). Verification dispatches on the
  *recorded* version and applies that version's canonicalization and field set. Never load an old
  record, fill today's defaults, and re-hash under today's rules (I7). Unknown fields are preserved,
  not stripped. M2A needs version *dispatch*, not a migration framework.

### 26.10 Trust boundary — what the hashes actually prove

Stated plainly, because it is easy to overclaim (I8):

- A SHA-256 in a committed JSON file proves **content integrity relative to a record**. It is **not a
  signature** and proves nothing about authorship or authority. Anyone with repository write access
  can edit both the artifact and the ledger and produce a fully consistent forgery.
- What the ledger does buy: **accidental drift becomes impossible to miss, and deliberate divergence
  becomes visible in a diff** that a human reviews. That is a real and sufficient property for a
  single-owner repository; it is not cryptographic authenticity.
- Two explicit validation levels:
  - **Structural validation** — from a clean clone, no run tree. Proves artifact hashes, dependency
    consistency, ledger internal consistency, and that the recorded role is permitted for the
    recorded purpose.
  - **Provenance validation** — requires the retained run tree. Proves the referenced gate exists,
    hashes as recorded, names that role, and binds that contract.
- After the run tree is deleted, provenance validation is permanently unavailable for those records.
  That is **accepted**, not solved: forcing worker logs into Git to make every proof portable would
  be worse. Evidence export/archival is a later milestone, not M2. Do not describe the ledger as
  proving a review happened when the run tree is gone — it proves a review was *recorded* as having
  happened.

### 26.11 Adversarial pass

| Attack / accident | Outcome |
|---|---|
| Artifact edited after acceptance | `invalid`; structural validation fails from a clone |
| Ledger hand-edited to claim acceptance | **Not prevented.** Structural validation passes; only Git review and (if retained) provenance validation catch it. Stated as a limitation, not a defense. |
| Reviewer role changed in the ledger | Detected by provenance validation against the gate; undetectable from a clone alone |
| Dependency hash edited | Consistency check fails against the dependency's recorded accepted hash |
| Old review reattached to a new artifact hash | Fails: the artifact's `content_sha256` and the gate's bound contract no longer correspond |
| `spec-reflector` used where implementation review was intended | **Now prevented** by the declared-purpose table (§26.4) — the gap M1 exposed |
| Run evidence missing | Structural validation only; say so explicitly rather than implying full proof |
| Merge resolves the ledger incorrectly | Derived validity recomputation catches hash/dependency inconsistency; a semantically wrong but internally consistent merge is not caught |
| Two branches, two freezes for one change | Legitimate divergent histories. Freeze identity is content-derived, so they are distinguishable; merge policy is an M2C question |
| Replay of evidence from another change | Bounded but not eliminated: the gate binds a contract, and the contract names its task. Cross-change replay within one run is conceivable and should be checked in M2C when the freeze binds a change id |

### 26.12 Unresolved questions

1. **Purpose vocabulary granularity** — five recorded names with two enforced classes, or two names
   only? Recording finer names costs nothing now and avoids retro-classification later, but it lets a
   reader mistake recorded precision for enforcement. **Human decision.**
2. **Where the ledger lives** — `specs/<change-id>/ledger.json` assumes the `specs/` root decided
   earlier. Still the only open naming question that blocks M2B, not M2A.
3. **Change profiles (None[§17](original-rfc.md#17-integration-points-with-current-dsd-code))** — the recommended direction is that the **parent declares the required
   artifact set explicitly** and Python enforces the declared graph, keeping subjective complexity
   judgments out of Python. No policy language. Not needed until M2B.
4. **Does discovery require reflection?** Deferred with the graph.
5. **Is `request.md` a versioned artifact or immutable input?** It has no upstream dependency and no
   author attempt; treating it as a *dependency-only* node — hashed, never reviewed — is the cheapest
   coherent answer, but it is unvalidated.

### 26.13 Worked examples (illustrative, not implementation)

**(1) Accepted artifact + (2) dependency + (3) review-purpose provenance.** One record carries all
three; they are separated here only for explanation.

```jsonc
// specs/CH-001/ledger.json  — committed
{
  "format": "proofbound-change-ledger-v1",
  "change": "CH-001",
  "artifacts": {
    "specs/CH-001/proposal.md": {
      "content_sha256": "a0f3…",
      "depends_on": {},                                   // (2) root: no upstream
      "review": {                                         // (3) purpose provenance
        "purpose": "proposal-reflection",
        "role": "spec-reflector",
        "gate": "phases/spec/tasks/CH-001-proposal/attempts/spec-reflector-2/evidence-gate.json",
        "gate_sha256": "4b81…"
      }
    },
    "specs/CH-001/design.md": {                           // (1) accepted artifact
      "content_sha256": "b1c2…",
      "depends_on": { "specs/CH-001/proposal.md": "a0f3…" },
      "review": {
        "purpose": "design-reflection",
        "role": "spec-reflector",
        "gate": "phases/spec/tasks/CH-001-design/attempts/spec-reflector-1/evidence-gate.json",
        "gate_sha256": "9d7e…"
      }
    }
  }
}
```

**(4) `needs-revalidation` after an upstream re-acceptance.** The proposal was re-authored and
re-reflected, so its record now reads `"content_sha256": "c7d4…"`. Nothing in the design record
changed — that is the point:

```text
$ pb validate CH-001
specs/CH-001/proposal.md   accepted
specs/CH-001/design.md     needs-revalidation
    depends_on specs/CH-001/proposal.md recorded a0f3… but proposal is now accepted at c7d4…
    design.md content is unchanged (b1c2…); re-authoring may be unnecessary,
    a fresh design-reflection against the new proposal is required
exit 1
```

Contrast `invalid`, where the artifact's own bytes moved:

```text
specs/CH-001/design.md     invalid
    recorded b1c2… but file hashes e5a9… — changed with no accompanying acceptance
```

**(5) Candidate freeze (deferred to M2C — shown only to test that the ledger shape supports it).**
The freeze is a separate immutable file whose canonical hash is the identity; it names accepted
hashes, never paths-plus-content:

```jsonc
// specs/CH-001/freeze-0001.json  — immutable once written
{
  "format": "proofbound-freeze-v1",
  "change": "CH-001",
  "artifacts": {
    "specs/CH-001/proposal.md":  "c7d4…",
    "specs/CH-001/design.md":    "f012…",
    "specs/CH-001/specification.md": "77ab…",
    "specs/CH-001/tasks.md":     "31de…"
  },
  "consistency_review": {
    "purpose": "consistency-reflection",
    "role": "spec-reflector",
    "gate": "phases/spec/tasks/CH-001-consistency/attempts/spec-reflector-1/evidence-gate.json",
    "gate_sha256": "aa10…"
  }
}
// freeze identity = sha256(canonical_json(this object without its own identity field))
// implementation contracts embed that identity; DSD already hashes the contract into every
// launch-reservation.json, so "which contract did this attempt run against" stays mechanical.
```

Absent optional artifacts are represented by **omission plus the change's declared required set**
(M2B), not by null entries — a null would be a second way to say the same thing.

### 26.14 Decision table

Derived states only; nothing is stored. "Freeze/execution" describes the M2C direction and is not
implemented.

| Mutation | Becomes `needs-revalidation` | Becomes `invalid` | Re-author required | Re-reflection required | Freeze / execution |
|---|---|---|---|---|---|
| **Proposal changes** (authored + re-accepted) | design, specification, and their closure | — | no | yes, downstream | freeze superseded |
| **Design changes** (re-accepted) | tasks | — | no | yes, tasks | freeze superseded |
| **Specification changes** (re-accepted) | tasks; every contract bound to a freeze containing it | — | no | yes, tasks | freeze superseded |
| **Tasks change** (re-accepted) | nothing upstream | — | no | no upstream | freeze superseded |
| **Artifact changes outside the harness** | its dependents, transitively (closure not accepted) | that artifact | yes, or revert | yes | binding void |
| **Review FAIL** | — | — | yes (new attempt, **same contract**, findings via `--input`) | yes, fresh reflector after the new mutation | never reached |
| **New acceptance, identical content** | nothing | nothing | no | no | unchanged — recorded hash did not move |
| **Byte-identical re-author** | nothing | nothing | no | no | unchanged — DSD records no mutation |
| **Dependency set edited** (edge added/removed in the ledger) | that artifact, if a recorded hash no longer matches | — | no | yes | freeze superseded |
| **Freeze already exists** | — | — | — | — | new freeze supersedes; **all** tasks bound to the old one conservatively invalidated |

Two rows deserve emphasis because they are where naive designs contradict themselves. *Review FAIL*
produces **no contract revision** — M1 proved attempts are the unit of repair history (I4). *New
acceptance, identical content* must be a no-op: if a fresh acceptance of unchanged bytes invalidated
downstream artifacts, every re-run would cascade, and the model would be unusable.


### 27.3 Corrections forced by implementation

1. **Provenance has three values, not two.** §26 anticipated `verified` and `unavailable`. A third
   state is required: **`contradicted`** — the recorded gate is still present, but its bytes moved, it
   is not clean, or it records a different role. Absence and contradiction are materially different
   signals and must never collapse into one word. `unavailable` is not a failure; `contradicted` is.
2. **Declared purpose is enforced unconditionally, not only for mutating tasks.** Gating the check on
   mutation detection would have made the guarantee conditional on an unrelated mechanism. Checking it
   wherever a purpose is declared is both simpler and strictly stronger.
3. **`- NONE` had to be rejected at the parser.** `NONE` means "explicitly nothing" elsewhere in the
   contract grammar; for this field it would have parsed as the literal purpose `"none"` and failed
   later as an unknown purpose. Failing at the declaration site is clearer, and keeps "absent" cleanly
   distinct from "malformed".
4. **Dependency closure needs a topological pre-pass, not just cycle detection.** A recursive closure
   is bounded by the interpreter's recursion limit; a legitimate 5000-node chain would crash it.
   Resolving in dependency order holds effective recursion depth at one. Verified at depth 5000 under
   the default limit of 1000.
5. **Recording fidelity is a distinct, legitimate check.** When a contract declares
   `## Allowed source changes`, the artifact being recorded must fall inside it. This is not a second
   acceptance decision — it cannot approve anything — it only stops the parent from filing an artifact
   under an acceptance that provably never covered it.

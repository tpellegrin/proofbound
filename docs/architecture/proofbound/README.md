# Proofbound architecture

> **Entry point and router.** This document routes; it does not summarize. Every rule below is stated in
> exactly one place, and this page links to it. If you find a principle restated here in full, that is a
> defect — fix it by replacing the copy with a link.

**Thesis.** Proofbound turns engineering intent into verified implementation by keeping two things apart:
what Python can *prove* (identity, boundaries, ordering, roles, schema) and what only an engineer or agent
can *judge* (whether the work is any good). It inherits DeepSeek-and-Destroy's execution and review
mechanics, adds durable specification artifacts with content-addressed provenance, and is designed so that
a long autonomous run cannot silently accumulate architecture nobody decided on.

## 0. Project identity boundary

**Proofbound** is this project's public identity — *from engineering intent to verified
implementation*; *specify, challenge, execute, prove*. Proofbound is derived from
DeepSeek-and-Destroy (MIT, © FrozenPepper) but is **not affiliated with or endorsed by** that
project. The inherited MIT license and copyright notice are preserved unchanged in `LICENSE`.

The identity boundary is deliberate and load-bearing:

- **Proofbound** names the project and new project-facing material: the repository, contributor
  documentation, architecture documents when they discuss *this* system rather than inherited
  implementation, and any genuinely new Proofbound-specific concept.
- **DeepSeek-and-Destroy-derived internal identifiers remain compatibility-sensitive
  implementation details until an explicit migration milestone.** That includes the
  `DeepSeekAndDestroy/` workspace root, `dsd_*.py` helpers and their CLI surface, persisted
  workspace paths, protocol and manifest format strings, snapshot formats, state keys,
  environment variables, adapters, and existing role names.

These are **wire and protocol identifiers**, not branding. Renaming them changes durable
artifacts that installed projects and historical runs depend on, so it requires its own
milestone with its own migration evidence — never a cosmetic pass bundled into feature work.

---


---

## Read this if…

Read the entry point plus the rows that match your task. Reading more is allowed; reading less is the
point. Byte figures are the authoritative-architecture cost of each route.

| Your task | Read | Skip | ≈ bytes |
|---|---|---|---|
| **A.** Changing reviewer freshness, attempts, gates, roles, or acceptance | README + [execution-and-review](execution-and-review.md) + [core-model](core-model.md) | everything else | ~28 KB |
| **B.** Implementing the M2B artifact graph | README + [core-model](core-model.md) + [artifacts-and-provenance](artifacts-and-provenance.md) + plan | autonomy, research, history | ~40 KB + plan |
| **C.** Implementing decision provenance | README + [core-model](core-model.md) + [artifacts-and-provenance](artifacts-and-provenance.md) + [long-running-autonomy](long-running-autonomy.md) | research, history | ~68 KB |
| **D.** Implementing context telemetry | README + [core-model](core-model.md) + [context-economy](context-economy.md) | artifacts, autonomy, history | ~34 KB |
| **E.** Fixing a bug in inherited DSD mechanics | README + [execution-and-review](execution-and-review.md) | everything else | ~12 KB |
| **F.** Asking "why is this rule like this?" | [evidence/implementation-findings](evidence/implementation-findings.md) | — | ~41 KB |
| **G.** Archaeology on the original design | [evidence/original-rfc](evidence/original-rfc.md) | — | ~83 KB |

If your task touches a principle, read its canonical definition in
[core-model.md](core-model.md#33-consolidated-principles) — not a paraphrase you found nearby (`P11`).

## Documents and their authority

Authority classes are deliberately visible in the filesystem. A research hypothesis and a proven invariant
must not look equally authoritative merely by living in the same file — that was the strongest reason to
split.

| Document | Class | Contains |
|---|---|---|
| [core-model.md](core-model.md) | **Normative** | Truth layers `L1`–`L4`; structural validity vs provenance vs semantics; **canonical `P1`–`P13`**; authority hierarchy `A1`–`A8`; knowledge lifecycle |
| [execution-and-review.md](execution-and-review.md) | **Normative** | **Canonical `I1`–`I15`**; attempts as repair history; review-purpose registry; parent's authority boundary |
| [artifacts-and-provenance.md](artifacts-and-provenance.md) | **Normative** | Canonical text identity; ledger v1; derived validity and closure; trust boundary; dependency ≠ applicability; M2B/M2C constraints |
| [long-running-autonomy.md](long-running-autonomy.md) | **Normative + rationale** | Promotion ladder; escalation; decision provenance direction; baseline supersession; erosion vs drift; coherence audit; **canonical `T1`–`T10`** |
| [context-economy.md](context-economy.md) | **Research** | External evidence and hypotheses. Not production behavior. Supports `P13`, which is defined in core-model. |
| [evidence/implementation-findings.md](evidence/implementation-findings.md) | **Historical evidence** | What M0–M2A proved and where it corrected the design. Why we trust the rules. |
| [evidence/original-rfc.md](evidence/original-rfc.md) | **Historical, superseded** | Pre-implementation design intent. Known wrong in several places. Never authoritative. |
| [../specification-reflection-harness-implementation-plan.md](../specification-reflection-harness-implementation-plan.md) | **Roadmap** | Milestone status, acceptance criteria, dependencies, deferrals, threat mitigation status |

**Precedence.** Normative beats rationale beats research beats history. Within normative documents, no
rule is defined twice, so there is nothing to arbitrate. If two documents appear to disagree, that is a
bug in the documentation, not a judgement call — report it.

## Identifier namespaces

Section numbers are **inherited stable identifiers**, not positions in a file; they did not change when
documents were split, and they carry no ordering meaning across documents. Prefer a durable identifier
over a section number whenever the concept has one — cite `P7`, not the section that happens to contain it.

| Namespace | Meaning | Canonical home |
|---|---|---|
| `I1`–`I15` | Inherited DSD mechanical invariants | [execution-and-review.md](execution-and-review.md) |
| `P1`–`P13` | Proofbound architecture principles | [core-model.md](core-model.md#33-consolidated-principles) |
| `T1`–`T10` | Long-running autonomy threats | [long-running-autonomy.md](long-running-autonomy.md#392-threats) |
| `L1`–`L4` | Truth layers | [core-model.md](core-model.md#31-the-truth-model--four-layers) |
| `A1`–`A8` | Evidence authority classes | [core-model.md](core-model.md#341-the-evidence-hierarchy) |
| `G1`–`G7` | Original problem-statement gaps | [evidence/original-rfc.md](evidence/original-rfc.md) *(historical)* |
| `M0`–`M5`, `CE1`–`CE2` | Milestones and research stages | [implementation plan](../specification-reflection-harness-implementation-plan.md) |
| `§N` | Inherited section identifier | the document that owns it |

Do not add another single-letter namespace without a reason that survives the field test.

## Principles index

One line each. **The canonical definitions, with their falsifiers, are in
[core-model.md None[§33](core-model.md#33-consolidated-principles)](core-model.md#33-consolidated-principles)** — cite that, not this index.

| | | | |
|---|---|---|---|
| `P1` semantic boundary | `P2` purpose ≠ capability ≠ role | `P3` derived state | `P4` separate trust layers |
| `P5` integrity, not authority | `P6` historical formats verified as recorded | `P7` local adaptation ≠ global policy | `P8` bounded decision provenance |
| `P9` supersession, not mutation | `P10` local correctness ≠ global coherence | `P11` patterns are evidence | `P12` fresh independent evaluation |
| `P13` context is an economic resource | | | |

## Status

| Milestone | State |
|---|---|
| M0 — trustworthy baseline | **Implemented** |
| M1 — reflection vertical slice | **Implemented** |
| M2A — durable artifact provenance | **Implemented** |
| M2B — artifact graph | **Next.** Not designed. Constraints in [artifacts-and-provenance.md](artifacts-and-provenance.md) |
| M2C — freeze and binding | Deferred; open questions recorded |
| Decision provenance, coherence audit, context telemetry | Direction only; see the plan's dependency graph |

Canonical test command: `python3 -m unittest discover -s tests -t .` (Python ≥3.10).

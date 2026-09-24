# Historical evidence — index

> **This index is not authority.** Nothing here states a rule. These documents record *what was
> observed*, dated, and why some rules exist. When evidence and a normative document disagree, the
> normative document is what the system obeys and the disagreement is a bug to report.

Evidence is read **on demand**, never as a precondition for doing work. That is why it is exempt
from the corpus ingestion budget, and why it lives behind this index rather than in the
[architecture entry point](../README.md): a corpus that must name every historical file in its
router cannot record a new run without first compressing its own prose.

**Adding a document here needs one row in this table and nothing else.** The reference checker
reaches it through this index, so the entry point does not change.

## Why a rule is the way it is

| Document | Records |
|---|---|
| [implementation-findings.md](implementation-findings.md) | What M0–M2A proved and where it corrected the design. The widest single answer to "why is this rule like this?" |
| [binding-implementation-outcomes.md](binding-implementation-outcomes.md) | What building M2C-A/B/C corrected in the freeze, consistency and execution-binding designs, and the boundary each shipped with. |
| [original-rfc.md](original-rfc.md) | Pre-implementation design intent, `G1`–`G7`. **Superseded and wrong in several places.** Never authoritative. |

## What a run observed

Each row is one dated observation. None is a rate, a reliability estimate or a comparison.

| Document | Observed |
|---|---|
| [supervised-workflow-2026-09-21.md](supervised-workflow-2026-09-21.md) | New operator path, offline observations, collection corrections and the unrun paired pilot; no new real-agent qualification. |
| [evaluation-runs.md](evaluation-runs.md) | What individual evaluation runs established: the V1 outcome, baseline zero, calibration outcomes. Never protocol. |
| [lifecycle-field-check.md](lifecycle-field-check.md) | `pb-lifecycle-field-check-1`: protocol and outcome of the attempt-deadline field check. Engineering validation, never a treatment sample. |
| [authority-workflow-demonstration.md](authority-workflow-demonstration.md) | `pb-authority-demo-1`: the first real-agent run of the full authority chain and the manual decisions it needs. Its specification challenge found a real defect and it stopped there under its own no-repair rule. |
| [authority-workflow-intent-defect.md](authority-workflow-intent-defect.md) | `pb-authority-demo-2` stopped because the parent intent it was built on was internally inconsistent: what it was, how it survived six paid attempts, what would have caught it. |
| [workflow-readiness-2026-09-22.md](workflow-readiness-2026-09-22.md) | Reproduced deadline, resume and completion defects before first paid use — including one that made the acceptance check invalidate its own review, which every fixture dodged. |
| [worker-profiles-qualification-2026-09-23.md](worker-profiles-qualification-2026-09-23.md) | Worker profiles and replay-only configuration qualification. The reported unfinished work was absent; the comparison overclaim reproduced and repaired; the pinned executor's zero-usage recording and 4,649-retry storm observed against a scripted endpoint. No model qualified. |
| [first-use-readiness-2026-09-23.md](first-use-readiness-2026-09-23.md) | Six qualification defects reproduced and repaired; the provider's V4.1 Flash routing; the retry storm recounted as a response loop and contained by the host; a four-trial live proposal and a first-use recipe, both unauthorized. Nothing live. |
| [live-qualification-2026-09-24.md](live-qualification-2026-09-24.md) | The authorized live qualification, blocked: the tool loop was shown; the contradictory challenge's reviewer failed in executor start-up before any request, traced to an undeclared runtime npm install, cause not established; two trials not run; first use not started. $0.016342 derived, 3 launches. |
| [executor-startup-2026-09-24.md](executor-startup-2026-09-24.md) | The reviewer's failure reproduced: the executor refuses a model its cached, fetched catalogue lists as deprecated. The npm install and lock activity were correlated, not causal. Start-up repaired for new runs; the findings-format example that showed the challenge's answer corrected. Nothing spent. |
| [qualification-and-first-use-2026-09-24.md](qualification-and-first-use-2026-09-24.md) | The continuation qualification completed: all three trials met, the contradictory case as verification rather than discovery. First use of the CSV task under Claude Code/Opus went from the goal to an accepted delivery, verified on a fresh checkout, with a fresh-session handoff whose first session exited mid-launch. 14 launches, $0.132969 derived. |
| [launch-supervision-2026-09-24.md](launch-supervision-2026-09-24.md) | A launch now outlives the session that started it, under a run-owned supervisor, and `recover` diagnoses and reconciles an interrupted launch from evidence. Reproduced first, including a stalled real worker that outlived its deadline with a live caller. Rehearsed with the real executor; nothing spent. Costs of the handoff sessions separated from worker spend. |
| [borrowdesk-preparation-2026-09-24.md](borrowdesk-preparation-2026-09-24.md) | First supervised-alpha application (BorrowDesk maintenance holds), preparation only. Baseline `63da90eb`: checks pass 39 of 39; a populated v0 database was built with public commands. **Blocked:** the worker boundary cannot run Node, npm or TypeScript 7's native compiler; the smallest change that makes `npm run check` pass inside was demonstrated and awaits an owner decision. Nothing spent. |
| [evidence-package-reader.md](evidence-package-reader.md) | What the offline evidence reader can and cannot recompute from `pb-handoff-1`'s retained files, and why the missing session databases bound it. |
| [readme-usability-check.md](readme-usability-check.md) | Can a stranger answer five questions from the documentation alone? What one fresh reader got right, what it exposed, what changed. |

## Corrections, by addition

A run's own records are never edited. A correction is a new dated document that says what the
earlier one got wrong, and the earlier one keeps its bytes (`P9`).

| Document | Corrects |
|---|---|
| [authority-workflow-successor.md](authority-workflow-successor.md) | `pb-authority-demo-1`'s preparation, and the questions its plan left open. |
| [authority-workflow-demo-2-audit.md](authority-workflow-demo-2-audit.md) | `pb-authority-demo-2`: the interrupted call was never bounded, search exhaustion is not nonexistence, `D1`/`D4` were departures. |
| [admission-bypass-reproduction.md](admission-bypass-reproduction.md) | The claim that the guarded launch path enforced authorization. The credential-free reproduction, the repair, and what it does and does not establish. |

## Run evidence outside this corpus

Retained run trees are not architecture documents and are not indexed here. They live with the
experiment that produced them — `evals/authority_slice/runs/<experiment>/` — and each carries its
own README and run report.

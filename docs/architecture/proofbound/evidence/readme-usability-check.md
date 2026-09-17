# Documentation usability check — can a stranger answer five questions?

**Dated 2026-09-17.** A bounded check of whether the documentation works, distinct from the
authority-recovery probes in
[`evals/authority_slice/probe-observations.md`](../../../../evals/authority_slice/probe-observations.md).
One reader, one pass. Not a measurement of anything.

## Method, and its accounting scope

A fresh Claude Code subagent, launched by the author's session with no inherited conversation, was
given the repository path and five questions and told to read prose only, running nothing except
commands the documentation itself tells a newcomer to run. It was **not** told the answers.

It is a fresh context, not an independent party: same model family, launched by the author, billed
to the same subscription. 147,660 subagent tokens, 55 tool calls, 12 minutes. No provider call was
made through the worker harness and nothing was charged to any demonstration budget.

The five questions: what the project does and who for; which guarantees are mechanical and which are
judgment; what has actually been demonstrated with real agents; how to run a credential-free check;
and what evidence would justify the next improvement.

## What it got right without help

All five, from the root README plus the documents it routes to. It reproduced the mechanical/judgment
split including the three things that make it more than a slogan; it correctly identified that every
real-agent authority observation to date is the chain **refusing**, and that the second half of the
chain has never run; it found both qualifiers — that neither demonstration conformed to its frozen
protocol, and that the MLR findings are scoped to one fixture; and it named the next improvement and
its gate. It reported that trusting the evidence table took roughly 25 minutes because the
qualifiers live in four other documents — a real cost of the routing design, and the trade the
routing is making.

It also ran `pb_slice.py validate` and reproduced every published figure exactly from a cold read.

## What it exposed, and what changed

| Finding | Response |
|---|---|
| The canonical suite failed for it — 3 errors in `test_authority_demo2_accounting.py` | **Not a documentation defect: it read a working tree mid-edit.** The failures were a `closing()` change that stopped the test fixture committing its rows, fixed before the check reported. The suite is green at 1,147 tests. It is, incidentally, a fair warning about running a usability check against a live checkout |
| The spend record's key was `unfinished_call_reserve` while the function is `interrupted_call_reserve` | **Fixed.** The record keys are now `interrupted_call_reserve` and `interrupted_call_bound`, matching the functions |
| `evals/authority_slice/README.md` said "no case in this slice has been run against a real model" while `probe-observations.md` in the same directory described two probes | **Fixed, and it was the most useful thing reported.** It read the root README first, believed the blanket sentence, and concluded the root README had *overstated* its evidence — the opposite of the truth. Both files now distinguish a case's *workflow* from a read-only *probe* against its fixture, in a table |
| `<skill>` appears in six operational documents and is defined nowhere; no documented path from clone to installed | **Fixed.** The README now defines `<skill>` and `<project>` and gives the adapter install command |
| The README's anti-ellipsis rule is contradicted by `SKILL.md`, `PROMPTS.md` and the adapters; the convention is explained 55 lines into the evaluation guide | **Fixed** where the reader meets it: the README now states the convention beside its own commands |
| No expected runtime for the command every route points at | **Fixed**: about 8 minutes, and the expected final line |
| "Verified green on 3.10, 3.12, 3.13 and 3.14" is unsourced; CI covers 3.10 and 3.14 | **Fixed** in the README and `CONTRIBUTING.md`: CI brackets the range, the rest is expectation |
| `run-report.md` still asserts figures the audit withdrew, with no in-file pointer | **Fixed**: both demonstrations' run reports now carry a dated notice pointing at their corrections. No claim, figure or record in either report was edited |

## What was not changed, and why

**`SKILL.md`'s frontmatter declares `name: deepseek-and-destroy` under a `# Proofbound` heading**,
and the operational documents speak in the inherited voice throughout. The reader is right that a
newcomer crossing from the README into `SKILL.md` reads what looks like a different project. The
skill name is a **wire identifier** a parent harness resolves, so changing it belongs to the
migration milestone that owns that rename, with its own evidence — not to a documentation pass. The
prose voice of the operational surface is a real gap and is recorded here rather than papered over.

## The limit of this check

One reader, one pass, no repeat. It establishes that these particular gaps exist, not that no others
do, and a second reader would find a different set. The check cost roughly as much in model work as
a small evaluation trial, which is the honest way to think about it: readable documentation is a
product feature with a measurable cost, not free by virtue of being prose.

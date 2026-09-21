# Finding: the coordinator's report is not collected on the live path

**Dated 2026-09-21, during execution of pb-handoff-2.**

`_package.COLLECT` includes `coordinator-report.md`, and `pb-handoff-1` retained one. On the live
path nothing writes it: the coordinator's report is returned to the evaluator as its final message,
and no supported command puts it into the workdir before `finalize()` collects.

Consequence: both conditions' packages report `decision.coordinator: unavailable`. That is a true
statement about what the instrument collected, and it is left standing.

The reports themselves are retained **outside** the sealed packages, in this run's committed
evidence directory, each labelled as relayed from the coordinator's final message. They are not
inserted into the packages after sealing: a package that claimed to have collected something it did
not would be worth less than one that admits the gap.

Same class as the `authorization-refusal.json` gap, and same cause — the writer lives on the
rehearsal path, not the live one. Repair belongs to a separate milestone.

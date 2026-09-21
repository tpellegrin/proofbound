# Finding, discovered during execution of pb-handoff-2 (control condition)

**Dated 2026-09-21, before the control condition reached its terminal outcome.**

## What

The frozen `control.refusal` predicate requires a retained `authorization-refusal.json`. On the
**live** path nothing writes one.

* `_live.py:658` writes it — inside `_rehearse`, the offline rehearsal driver.
* On the live path the coordinator runs `pb_execution.py admit` directly. That command prints its
  refusal to stdout and writes no file.
* `_live.preserve` looks for `workdir/authorization-refusal.json`; `_live.finalize` calls
  `preserve` without a `refusal=` argument.

So a live control condition that refuses correctly still produces `control.refusal: not-observed`,
and therefore fails both its outcome predicate and its evidence predicate.

## Why the offline qualification did not catch it

Every offline rehearsal of the control went through `_rehearse`, which writes the record itself.
The integration test drove the *valid* shape through the public commands and the *control* shape
only through the rehearsal driver. The gap is exactly in the seam between them: the thing that
writes the evidence lives on the path that was not the one being qualified.

This is the defect class the protocol names — "a collection defect found after execution cannot be
repaired into retroactively complete evidence" — and it was found by executing, not by rehearsing.

## What is NOT being done about it

The instrument is frozen and under execution. Per the authorization: no criteria altered, no
repairs added during the run. The control condition runs to its terminal outcome and is reported
as it actually is. Supplying the refusal record at finalize time from the coordinator's prose would
be manufacturing the evidence the predicate exists to require — the precise error corrected in
`evidence/evidence-package-reader.md` for `pb-handoff-1`.

Repair belongs to a separate milestone.

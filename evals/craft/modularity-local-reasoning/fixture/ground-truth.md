# Fixture ground truth — frozen before any semantic call

Hidden from any future agent. Records what the experiment believes, so a later failure can be
diagnosed instead of rationalised.

## The external task

**Responsibility.** Deciding what a request returns, and when a report is produced, belongs to the
service. `objectstore` is asked to keep bytes and hand them back; it has no opinion about reports,
accounts, entitlement or status codes. The change lives entirely in `app/`.

**Contract facts legitimately required:** that `get` raises `NotFound` when nothing is stored under a
key and reports absence no other way; that `put` replaces whatever was there and is safe to repeat;
that a successful `put` is immediately visible to a following `get`. All three are stated in
`docs/storage-contract.md`.

**Internal facts not legitimately required:** how a key becomes a path, that anything is checksummed,
how many attempts a failed backend operation gets, how a partial write is avoided, what
`_ChecksumMismatch` is, or that a filesystem is involved at all.

**Correctness oracle:** `hidden/external_test.py`, product-visible behaviour only — statuses, bodies,
what a later read observes, and that a refused export stores nothing. It never imports the package's
internals and never asserts anything about the service's structure.

**Expected boundary relation:** the reference solution changes `app/exports.py` and `app/api.py` and
touches neither the contract nor the package. Verified.

**Known confounds:** `full` carries four extra files under `third_party/`, which is the treatment and
also the only structural difference. Source recovery through `inspect.getsource` or `__file__` was
closed in MLR-C2 by compiling the runtime; what remains open, and was measured in MLR-C3, is the live
object — `vars(_store)` yields `_ATTEMPTS` and `_FANOUT`, `dir` names the private helpers, and `dis`
renders the logic. So the treatment hides implementation *source*, not implementation *knowledge*.
That is evidence to record and to classify, never a breach to prevent: a `contract` run that
reconstructs the interior is a result, and the accounting exists so it cannot be mistaken for one
that did not.

## The internal control — not built, and why

The approved control was *change the storage retry behaviour*. It cannot be realised under the
approved isolation mechanism, and this was demonstrated rather than argued: `full`'s copy of the
package sits at `third_party/objectstore-1.4.0/`, which is not on `sys.path`, so editing it leaves
the running system untouched. A hidden test asserting a new retry policy therefore fails in **both**
arms, and the control would measure only that neither arm can modify a dependency.

This is a contradiction between two approved decisions, not a defect in either alone. Recorded in
the implementation record; the fixture is frozen without the control.

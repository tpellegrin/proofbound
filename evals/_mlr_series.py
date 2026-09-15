#!/usr/bin/env python3
"""The ordered, bounded, checkpointed slot procedure a frozen MLR paired series is run by.

`run_series` in `pb_mlr` is the original unbounded series: it drives `_mlr_run.run_attempt`, retries
any attempt that did not come back valid, and moves on to the next slot when a slot is exhausted.
That is the procedure the early headroom pilots were run under and it is left exactly as it was.

It is **not** the procedure `MLR-eventbus-b1-preregistration.md` describes, in three ways that decide
whether a record means anything:

* §11 A/C separate *an infrastructure attempt that failed before semantic execution began* — which
  may be retried, bounded at three — from *a semantic trajectory that began and was interrupted* —
  which is accounted, preserved, and *never* re-rolled. A blanket retry cannot tell them apart, so
  it would buy a second trajectory for a slot the design has already spent.
* §11 B stops the series when a slot exhausts its three attempts, rather than carrying on into the
  next slot with a hole behind it.
* §11 D–I stop the series on a validity defect in a *completed* attempt — a failed extraction,
  unresolved attribution, a contradiction, uncontrolled source reaching `contract`, stack drift, an
  oracle that could not grade.

**This is a new implementation of the documented procedure, not a recovered driver.** The
orchestration that produced `mlr-deepseek-v4-flash-high-paired-q1` is not in this repository and
nothing here reconstructs it; what is reconstructed is the procedure its preregistration specifies,
from the preregistration. Where the two would differ, the preregistration wins.

**What it refuses to decide.** It names the §11 condition that stopped a series and records the
evidence for it. It does not assign a result family, because a family is a reading of an experiment
and this is mechanism (`P1`). A stopped series is handed back with its stop condition, its attempts
and its spend, for a person to read.
"""
from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

import _hermetic
import _mlr
import _mlr_boundary
import _mlr_run
import _repeat
import _semantic_view

# §11's condition letters, used as recorded identifiers rather than prose so that a stop can be
# matched against the document that defines it. The text beside each is the document's, abbreviated.
STOP_CONDITIONS = {
    "B": "all three infrastructure attempts for a slot failed",
    "C": "a semantic trajectory began and did not complete; it is preserved and never re-rolled",
    "D": "extraction failed",
    "E": "material unresolved attribution, at item or component granularity",
    "F": "a contradiction or an uncovered material model-visible event",
    "G": "a boundary leak, or uncontrolled source in `contract`",
    "H": "provider, model, variant, boundary, runtime or attribution drift beyond a host identity",
    "I": "the hidden oracle could not grade an extracted workspace",
    "J": "the ceiling would be exceeded before a slot; the series ends short",
}

#: Not a §11 condition. The environment was refused before anything was launched, so no slot was
#: consumed and no money was spent — the series simply did not start.
NOT_LAUNCHABLE = "not-launchable"


class SeriesRefused(RuntimeError):
    """The series may not start or may not continue, and nothing semantic was attempted."""


def executor_eligibility(executor: Path | None, *, required_sha256: str) -> dict[str, Any]:
    """Whether this host's executor is the one a frozen stack names.

    Separated from both the boundary and the launcher so it can be exercised with controlled
    inputs on any platform: the interesting cases are *absent*, *matching* and *mismatching*, and
    none of them should require a developer to have the historical binary installed.

    The comparison is on content, never on a reported version. A version string is what a build
    claims to be; the digest is what it is, and the semantic boundary binds its tools by digest, so
    a mismatching executor is a different boundary as well as a different program.
    """
    required = (required_sha256 or "").lower()
    if not required:
        raise ValueError("a frozen stack must name the executor identity it requires")
    if executor is None:
        return {"status": "absent", "eligible": False, "required": required, "observed": None,
                "reason": "no executor was found or selected"}
    executor = Path(executor)
    if not executor.is_file():
        return {"status": "absent", "eligible": False, "required": required, "observed": None,
                "reason": f"{executor} is not a file"}
    observed = hashlib.sha256(executor.read_bytes()).hexdigest()
    # The preregistration freezes a prefix, so a prefix is what is checked; a full digest supplied
    # by a later record is compared over its whole length. Either way this is content identity.
    if observed.startswith(required):
        return {"status": "eligible", "eligible": True, "required": required,
                "observed": observed, "path": str(executor), "reason": None}
    return {"status": "mismatch", "eligible": False, "required": required, "observed": observed,
            "path": str(executor),
            "reason": ("the executor at this path is not the one the frozen stack names; "
                       "select the matching installation explicitly rather than running this one")}


def _digest_matches(value: str | None, frozen: str | None) -> bool:
    """A frozen prefix against an observed digest. Absent frozen value means nothing was frozen."""
    if not frozen:
        return True
    return isinstance(value, str) and value.lower().startswith(frozen.lower())


def drift(attempt: dict[str, Any], stack: dict[str, Any]) -> list[str]:
    """Which frozen stack identities this completed attempt did not reproduce (§11 H).

    Host-derived identities are deliberately absent from this list. §5 records the interpreter, the
    semantic boundary digest and the hermeticity rule digest *per slot as execution facts*, because
    each depends on the machine the slot ran on; a different value for the same rule on a different
    host is a host difference and not drift. What is checked here is the part of the stack that is
    the same everywhere: the fixture's own content, the model configuration, and the executor.

    **An absent field is never drift.** Only a value the attempt actually recorded, which differs
    from the one the stack froze, is. Records written before a field existed do not mean it changed
    — the same reading `_mlr._package` already gives a build that predates the second fixture — and
    reporting one as drift would stop a series on the instrument's own history. Whether b1's
    attempts carry every field is a separate guarantee of `run_bounded_attempt`, asserted by test,
    not something this function should infer from a `None`.
    """
    found: list[str] = []

    def compare(field: str, observed: Any, frozen: Any, *, digest: bool = False) -> None:
        if frozen is None or observed is None:
            return
        if digest:
            if not _digest_matches(observed, frozen):
                found.append(f"{field}: {str(observed)[:16]} != {str(frozen)[:16]}")
        elif observed != frozen:
            found.append(f"{field}: {observed!r} != {frozen!r}")

    compare("model", attempt.get("model"), stack.get("model"))
    compare("oracle", attempt.get("oracle"), stack.get("oracle"))
    compare("package", attempt.get("package"), stack.get("package"))
    compare("variant", attempt.get("variant"), stack.get("variant"))
    compare("permission flag", attempt.get("auto_flag"), stack.get("permission_flag"))
    compare("role", attempt.get("role"), stack.get("role"))
    compare("source_digest", attempt.get("source_digest"), stack.get("source_digest"), digest=True)
    compare("task_sha256", attempt.get("task_sha256"), stack.get("task_sha256"), digest=True)
    compare("contract_sha256", attempt.get("contract_sha256"), stack.get("contract_sha256"),
            digest=True)
    compare("executor", (attempt.get("executor") or {}).get("sha256"),
            stack.get("executor_sha256"), digest=True)
    return found


def validity_defect(attempt: dict[str, Any], stack: dict[str, Any]) -> tuple[str, str] | None:
    """The §11 condition a *completed* attempt trips, if any, as `(letter, evidence)`.

    Every check is a count or an equality over what the attempt already recorded. None of them
    reads a report, weighs a trade-off or decides whether the work was good — those are the
    grader's and the reader's jobs. Conditions are evaluated in the document's order, and the first
    that applies is the one returned.
    """
    extraction = attempt.get("extraction") or {}
    if not extraction.get("workspace") or not extraction.get("session"):
        return "D", f"extraction returned {sorted(extraction) or 'nothing'}"

    context = attempt.get("context") or {}
    unresolved = context.get("unresolved") or {}
    if unresolved.get("items") or unresolved.get("components"):
        return "E", (f"unresolved items={unresolved.get('items')} "
                     f"components={unresolved.get('components')}")
    if context.get("contradictions"):
        return "F", f"{len(context['contradictions'])} contradiction(s)"
    if context.get("uncovered_events"):
        return "F", f"{len(context['uncovered_events'])} uncovered model-visible event(s)"

    findings = (attempt.get("hermeticity") or {}).get("findings") or []
    if findings:
        return "G", f"{len(findings)} hermeticity finding(s) inside the view"
    if attempt.get("view_destroyed") is False:
        return "G", ("the slot's semantic view survived its attempt; the next slot would inherit "
                     "it, which is cross-slot contamination")
    if attempt.get("arm") == _mlr.CONTRACT and context.get("implementation_source_unique_bytes"):
        return "G", (f"{context['implementation_source_unique_bytes']} bytes of direct "
                     "implementation source reached the `contract` arm")

    moved = drift(attempt, stack)
    if moved:
        return "H", "; ".join(moved)

    outcome = attempt.get("outcome") or {}
    if "correct" not in outcome:
        return "I", f"no correctness verdict: {attempt.get('reason') or 'outcome absent'}"
    return None


def launchable(*, fixture: Path, executor: Path | None, stack: dict[str, Any],
               evidence_roots: list[Path] | None = None) -> dict[str, Any]:
    """Everything that must hold before a single provider call is bought.

    Resolves the configuration the series would actually run, compares it against the frozen stack,
    and reports what this host contributes. **It contacts no provider, consumes no slot and writes
    no experimental result** — the point is that every way this series could be wrong which does not
    require a model to discover is discovered here, for nothing.

    Host-derived identities are reported beside the values the preregistration observed on its own
    host, and labelled, rather than compared: §5 makes them execution facts. A difference there is
    information for the person deciding to spend, not a refusal.
    """
    spec = _mlr.fixture_for(fixture)
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: Any = None, blocking: bool = True) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail, "blocking": blocking})

    check("fixture is the frozen one",
          _digest_matches(_mlr.digest_tree(spec.source), stack.get("source_digest")),
          {"observed": _mlr.digest_tree(spec.source)[:16],
           "frozen": stack.get("source_digest"), "package": spec.package})
    check("task is the frozen one",
          _digest_matches(_mlr.digest_file(spec.task), stack.get("task_sha256")),
          {"observed": _mlr.digest_file(spec.task)[:16], "frozen": stack.get("task_sha256")})
    check("public contract is the frozen one",
          _digest_matches(_mlr.digest_file(spec.root / "base" / spec.contract),
                          stack.get("contract_sha256")),
          {"observed": _mlr.digest_file(spec.root / "base" / spec.contract)[:16],
           "frozen": stack.get("contract_sha256"), "path": spec.contract})
    check("hidden oracle is the frozen one",
          _digest_matches(_mlr.digest_file(spec.gate), stack.get("gate_sha256")),
          {"observed": _mlr.digest_file(spec.gate)[:16], "frozen": stack.get("gate_sha256"),
           "path": f"hidden/{spec.oracle}"})

    eligibility = executor_eligibility(executor, required_sha256=stack["executor_sha256"])
    check("executor is the frozen one", eligibility["eligible"], eligibility)

    sandbox = Path(_semantic_view.SANDBOX).exists()
    check("the semantic boundary can be constructed on this platform", sandbox,
          {"required": _semantic_view.SANDBOX,
           "note": "the boundary is a macOS sandbox profile; b1 must run through it"})

    check("the staged harness carries no controlled evidence",
          _mlr_boundary.harness_is_clean(fixture=spec.root)["status"] == _hermetic.CLEAN)

    # The two things that actually leaked. Ephemeral materialisations are the class that put twelve
    # readable copies of the implementation on the host for a day; stale views are what a killed
    # process leaves behind. Both are host state the next slot would inherit, and both are
    # removable — which is why they block rather than merely inform.
    roots = [Path(tempfile.gettempdir()), Path("/tmp"), *(evidence_roots or [])]
    ephemeral = _mlr.ephemeral_materialisations(roots)
    check("no ephemeral arm materialisation survives on the host", not ephemeral,
          {"found": [str(p) for p in ephemeral],
           "remedy": "pb_mlr.py preflight --clean"})
    stale = _semantic_view.stale_views()
    check("no semantic view from an earlier run survives", not stale,
          {"stale": [str(p) for p in stale],
           "remedy": "pb_mlr.py b1-preflight --clear-stale-views"})

    # Reported, never a launch condition. `_mlr.hermeticity` scans the repository on purpose,
    # because for an *unbounded* attempt the agent can reach it by the same command that reaches a
    # stale workspace. A bounded slot runs in a constructed view that does not contain the
    # repository at all, so the canonical fixture being present here is the normal state of a clean
    # checkout and cannot be a reason to refuse. What decides a bounded slot is the view-scoped
    # preflight `run_bounded_attempt` runs inside the view, per slot, before it launches anything.
    scan = _mlr.preflight(fixture=spec.root, evidence_roots=evidence_roots or [])
    check("host scan (informational; the binding check is per-slot and view-scoped)",
          scan["status"] == _hermetic.CLEAN,
          {"status": scan["status"], "findings": len(scan["findings"]),
           "scanned_roots": scan["scanned_roots"],
           "note": "the repository is a scanned root and holds the canonical fixture, so a clean "
                   "checkout is expected to report findings here; this does not block a bounded "
                   "series"},
          blocking=False)

    host = {
        "interpreter": _mlr.interpreter_identity(),
        "hermeticity_identity": scan["hermeticity_identity"][:16],
        "boundary_identity": (_mlr_boundary.policy(executor=Path(eligibility["path"])).identity()[:16]
                              if eligibility["eligible"] else None),
        "recorded_on_the_frozen_host": stack.get("host_derived"),
        "note": ("§5 records these per slot as execution facts, not as universal constants. A "
                 "difference here is a host difference; a change in policy, exposure, enforcement "
                 "or scan-root meaning would be stack drift and would stop the series."),
    }
    blocking = [c for c in checks if c["blocking"] and not c["ok"]]
    return {"fixture": str(spec.root), "package": spec.package, "checks": checks,
            "host_derived_identities": host, "executor": eligibility,
            "launchable": not blocking,
            "blocked_by": [c["check"] for c in blocking]}


def _spent(measurements: list[dict[str, Any]]) -> float:
    """Money actually derived so far, over every attempt that recorded usage.

    Failed and interrupted attempts are included, deliberately. An attempt that reached the
    provider and then lost its extraction spent what it spent, and a ceiling that only counted
    successes would be a ceiling the series could exceed by failing.
    """
    total = 0.0
    for m in measurements:
        amount = (m.get("cost") or {}).get("amount")
        if isinstance(amount, (int, float)):
            total += float(amount)
    return round(total, 6)


#: How far an attempt got. The four stages the retry rule has to tell apart, recorded rather than
#: re-inferred, because "did this cost a semantic trajectory?" is the only question §11 A and §11 C
#: differ on and a later reader must not have to reconstruct it from prose.
NOT_OFFERED = "not-offered"          # the slot was never handed to the executor at all
BEFORE_LAUNCH = "before-launch"      # attempted; failed before the launcher was entered
LAUNCHER_REFUSED = "launcher-refused"  # the launcher was entered and refused to start the worker
WORKER_EXECUTED = "worker-executed"  # the launcher started the worker; a provider call may have run


def execution_stage(record: dict[str, Any]) -> str:
    """How far one recorded attempt got, from what it already carries.

    `launcher-refused` is kept separate from `worker-executed` even though both are treated the same
    way by the retry rule, because they are different facts and the operator resolving a stopped
    series needs to see which one happened. The launcher's own classification of its output — an
    absent executable, a missing credential, a rate limit — is a *hint* about which side of the
    semantic boundary the failure fell on, and it is recorded as a hint. It is not promoted into
    permission to buy a second trajectory: it is a substring match over log text, and the cost of it
    being wrong is the one thing §11 C exists to prevent.
    """
    if record.get("stage") == NOT_OFFERED:
        return NOT_OFFERED
    if not record.get("trajectory_began"):
        return BEFORE_LAUNCH
    if record.get("launch_returncode") not in (0, None):
        return LAUNCHER_REFUSED
    return WORKER_EXECUTED


def _offered(measurements: list[dict[str, Any]], key: tuple[str, int]) -> int:
    """How many of this slot's three infrastructure attempts have actually been spent (§11 B).

    A row the loop appended without calling the executor — the ceiling refusal, the residue
    refusal — is not an attempt on the slot. Counting it would let three environment refusals
    exhaust a slot that was never offered to the executor once.
    """
    return sum(1 for m in measurements
               if (m.get("item"), m.get("repeat")) == key
               and execution_stage(m) != NOT_OFFERED)


def _slot_isolation(evidence_roots: list[Path] | None) -> dict[str, Any] | None:
    """Host state an earlier slot would have had to leave behind, or nothing."""
    roots = [Path(tempfile.gettempdir()), Path("/tmp"), *(evidence_roots or [])]
    ephemeral = [str(p) for p in _mlr.ephemeral_materialisations(roots)]
    stale = [str(p) for p in _semantic_view.stale_views()]
    if not ephemeral and not stale:
        return None
    return {"ephemeral_materialisations": ephemeral, "stale_views": stale}


def _unfinished_trajectory(measurements: list[dict[str, Any]],
                           key: tuple[str, int]) -> dict[str, Any] | None:
    """A prior attempt on this slot that began a semantic trajectory and did not come back valid."""
    for m in measurements:
        if (m.get("item"), m.get("repeat")) != key:
            continue
        if m.get("validity") != _mlr_run.VALID and m.get("trajectory_began"):
            return m
    return None


def run_bounded_series(out: Path, *, config: dict[str, Any], stack: dict[str, Any],
                       arms: list[str], samples: int, executor: Path,
                       slots: Callable[[list[str], int], list[dict[str, Any]]],
                       credentials: dict[str, Path] | None = None,
                       keep: Path | None = None,
                       budget: float | None = None, reserve: float = 0.10,
                       max_attempts_per_slot: int = 3,
                       evidence_roots: list[Path] | None = None,
                       extra: dict[str, Any] | None = None,
                       attempt: Callable[..., dict[str, Any]] | None = None,
                       ) -> dict[str, Any]:
    """Fill the preallocated slots in their frozen order, through the semantic boundary.

    `attempt` exists so the orchestration can be exercised without a provider. It defaults to
    `_mlr_boundary.run_bounded_attempt` and **there is no unbounded fallback**: a caller that does
    not supply one gets the boundary, and a caller that supplies one is a test. The original
    unbounded path is not reachable from here at all, because a series that silently ran outside the
    view would produce a record whose boundary identity described something that never contained it.
    """
    fixture = Path(config_fixture(config, stack))
    run_attempt = attempt or _mlr_boundary.run_bounded_attempt
    measurements = _repeat.load_series(out, config)
    done: set[tuple[str, int]] = set()

    def stop(condition: str, detail: Any = None) -> dict[str, Any]:
        _repeat.write_series(out, config, measurements, extra=extra)
        return {"config": config, "measurements": measurements, "stopped": condition,
                "stop_condition": condition,
                "stop_reason": STOP_CONDITIONS.get(condition, condition),
                "stop_detail": detail, "spent": _spent(measurements),
                "completed_slots": sorted(done)}

    # A stop is a property of the evidence, not of the process that noticed it. `done` is therefore
    # rebuilt by re-applying §11 D–I to every attempt already on disk, not by trusting `validity`
    # alone: an attempt can be a valid *execution* and still carry a defect that stops the series,
    # and reading it back as a closed slot would let a restart turn a stopped series into a record
    # that looks clean and complete. The live rule and the resume rule are the same rule.
    for recorded in measurements:
        if recorded.get("validity") != _mlr_run.VALID:
            continue
        defect = validity_defect(recorded, stack)
        if defect is not None:
            letter, evidence = defect
            return stop(letter, {"slot": {k: recorded.get(k) for k in ("item", "repeat", "slot")},
                                 "evidence": evidence,
                                 "note": "found on an attempt already recorded; the series was "
                                         "stopped when it ran and stays stopped"})
        done.add((recorded["item"], recorded["repeat"]))

    # `item`/`repeat` are `_repeat`'s names and are what `paired_analysis` reads; `slot` is the
    # 1-based position in the frozen order, carried so a record can be read against §9's table
    # without recomputing it. Nothing derives one from the other later.
    ordered = [{**s, "slot": i + 1} for i, s in enumerate(slots(arms, samples))]
    for slot in ordered:
        key = (slot["item"], slot["repeat"])
        if key in done:
            # Immutable. A completed semantic trajectory is never re-rolled — not for being
            # incorrect, expensive, representation-heavy or representation-light (§10).
            continue

        # Resume must not do what a live loop refuses to do. A slot whose earlier attempt reached
        # the launcher is in §11 C whether the process that ran it is still alive or not, so a
        # restart may not quietly buy it a second trajectory.
        interrupted = _unfinished_trajectory(measurements, key)
        if interrupted is not None:
            return stop("C", {"slot": slot, "attempt": interrupted.get("attempt"),
                              "validity": interrupted.get("validity"),
                              "reason": interrupted.get("reason"),
                              "cost": interrupted.get("cost"),
                              "note": "preserved; resolve deliberately, never automatically"})

        tried = _offered(measurements, key)
        while key not in done and tried < max_attempts_per_slot:
            # Budget before launching, never by cutting one short: a trajectory truncated for money
            # would change the correctness distribution everything else is gated on (§19).
            if budget is not None and _spent(measurements) + reserve > budget:
                measurements.append({**slot, "attempt": tried + 1,
                                     "validity": _mlr_run.SETUP_FAILURE,
                                     "trajectory_began": False, "stage": NOT_OFFERED,
                                     "reason": f"ceiling {budget} would be exceeded "
                                               f"(spent {_spent(measurements)}, reserve {reserve})"})
                return stop("J", {"slot": slot, "spent": _spent(measurements),
                                  "ceiling": budget, "reserve": reserve})

            # The stack is re-checked before every slot, not once at the start. An executor that
            # was upgraded between slot 4 and slot 5 would otherwise change the boundary mid-series
            # with nothing in the record moving.
            eligibility = executor_eligibility(executor,
                                               required_sha256=stack["executor_sha256"])
            if not eligibility["eligible"]:
                return stop("H", {"slot": slot, "executor": eligibility})

            # Cross-slot isolation is a precondition of the slot, not a property of the series: the
            # previous slot is the thing most likely to have left something behind. This is host
            # state only — what the *view* exposes is checked inside the view, per slot, by
            # `run_bounded_attempt` before it launches anything.
            residue = _slot_isolation(evidence_roots)
            if residue:
                measurements.append({
                    **slot, "attempt": tried + 1, "validity": _mlr_run.SETUP_FAILURE,
                    "trajectory_began": False, "stage": NOT_OFFERED,
                    "reason": "an earlier slot left state on the host", "residue": residue})
                return stop("G", {"slot": slot, "residue": residue})

            record = run_attempt(slot["item"], model=config["model"],
                                 variant=config.get("variant"), executor=executor,
                                 credentials=credentials, keep=keep, fixture=fixture)
            recorded = {**slot, "attempt": tried + 1, **record}
            recorded["stage"] = execution_stage(recorded)
            measurements.append(recorded)
            _repeat.write_series(out, config, measurements, extra=extra)
            tried += 1

            if record.get("validity") == _mlr_run.VALID:
                defect = validity_defect(recorded, stack)
                if defect is not None:
                    letter, evidence = defect
                    return stop(letter, {"slot": slot, "evidence": evidence})
                done.add(key)
                continue

            # Invalid. Whether this slot may be offered again is decided by one fact and not by the
            # failure's wording: did anything enter the launcher? Below that call is the executor
            # and its provider, and no downstream failure can prove they were not reached.
            if record.get("trajectory_began"):
                return stop("C", {"slot": slot, "attempt": tried,
                                  "stage": recorded["stage"],
                                  "validity": record.get("validity"),
                                  "reason": record.get("reason"),
                                  "cost": record.get("cost"),
                                  "launcher_classified_as_pre_semantic":
                                      recorded["stage"] == LAUNCHER_REFUSED
                                      and record.get("validity") == _mlr_run.SETUP_FAILURE,
                                  "note": ("the launcher was entered, so no automatic retry "
                                           "follows. Where the launcher itself reports an absent "
                                           "executable, a missing credential or a rate limit, the "
                                           "failure probably preceded semantic execution and a "
                                           "person may resolve the slot deliberately — that is a "
                                           "judgement, and this refuses to make it")})

            # A view-scoped preflight refusal is not an outage to be retried. It is the leak
            # detector firing, and §11 G stops the series on a leak; offering the same contaminated
            # surface two more times would spend attempts to learn nothing.
            if (record.get("hermeticity") or {}).get("findings"):
                return stop("G", {"slot": slot,
                                  "findings": record["hermeticity"]["findings"][:20]})

        if key not in done:
            return stop("B", {"slot": slot, "attempts": tried})

    _repeat.write_series(out, config, measurements, extra=extra)
    return {"config": config, "measurements": measurements, "stopped": None,
            "spent": _spent(measurements), "completed_slots": sorted(done)}


def config_fixture(config: dict[str, Any], stack: dict[str, Any]) -> Path:
    """The fixture root a configuration and its frozen stack agree on.

    Both carry it, which is the point: the stack is the document's claim about which module is under
    test and the configuration is what the machinery resolved. If they disagree, an `eventbus-b1`
    identifier is about to describe objectstore data, and that is refused here rather than noticed
    afterwards in a record that cannot be unwritten.
    """
    spec = _mlr.fixture_for(stack["fixture"])
    if not _digest_matches(config.get("source_digest"), stack.get("source_digest")):
        raise SeriesRefused(
            f"the resolved configuration is not the frozen stack's fixture: source "
            f"{str(config.get('source_digest'))[:16]} != {stack.get('source_digest')}; "
            f"experiment {config.get('experiment')!r} would describe another fixture's data")
    if config.get("oracle") != spec.oracle:
        raise SeriesRefused(
            f"the resolved configuration names oracle {config.get('oracle')!r}, but the frozen "
            f"stack's fixture ships {spec.oracle!r}")
    return spec.root


def clear_stale_views() -> list[str]:
    """Remove semantic views a killed process left behind, and say which.

    A signal ends a process rather than a block, so the view context manager's cleanup does not run
    and the directory survives. It is not evidence and nothing reads it; leaving it would fail the
    next slot's preflight for a reason that has nothing to do with the next slot.
    """
    removed = []
    for view in _semantic_view.stale_views():
        shutil.rmtree(view, ignore_errors=True)
        removed.append(str(view))
    return removed

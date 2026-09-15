#!/usr/bin/env python3
"""Run the modularity calibration's pre-registered series, one attempt at a time.

`pilot` runs `full` alone to answer whether there is anything for the paired treatment to remove;
`paired` runs the two arms against each other; `analyse` reads a completed series and classifies it
against the categories that were declared before the first call. None of them invents a category,
and each record carries its own experiment identity so one can never be mistaken for — or spliced
into — another's evidence.

`b1` and `b1-preflight` run the one frozen experiment whose procedure differs from `paired`'s: the
cross-fixture replication executes inside the semantic boundary and separates a retryable
infrastructure failure from a semantic trajectory that began, which a blanket retry cannot do. The
procedure lives in `_mlr_series`; see `MLR-eventbus-b1-execution.md`. `b1-preflight` resolves and
validates exactly what `b1` would run and buys nothing.

Checkpointing is `_repeat`'s: every attempt is written the moment it finishes, into preallocated
slots generated before execution, under a frozen configuration hash that refuses to resume across a
different fixture, runtime, model or budget. A host timeout once took a whole paired matrix; here
that costs one attempt.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]

import _hermetic       # noqa: E402
import _mlr            # noqa: E402
import _mlr_context    # noqa: E402
import _mlr_run        # noqa: E402
import _mlr_series     # noqa: E402
import _pricing        # noqa: E402
import _repeat         # noqa: E402

PILOT = "mlr-c3-full-headroom-pilot"
PILOT_R = "mlr-c3r-full-headroom-pilot"

#: The frozen stack of `MLR-eventbus-b1-preregistration.md`, transcribed from the committed
#: document. It is held here so the runner can refuse a configuration the document did not freeze,
#: and `tests/test_mlr_b1_execution_path.py::FrozenStackFidelityTest` asserts that the document is
#: byte-for-byte the one this was read from and that every value below still appears in it — the
#: document is the authority and this is a machine-readable copy of it, which is only safe while a
#: test keeps the two from drifting apart.
#:
#: `host_derived` is the set §5 records *per slot as execution facts*. It is carried so preflight can
#: show a person what this host contributes beside what the frozen host contributed. Nothing compares
#: against it, and a difference there is not drift.
B1 = {
    "revision": "eventbus-b1",
    "experiment": "mlr-deepseek-v4-flash-high-paired-eventbus-b1",
    "preregistration": "evals/craft/modularity-local-reasoning/MLR-eventbus-b1-preregistration.md",
    "preregistration_sha256":
        "c2dd49a0864d02bb189aed01d84a2f80950605ece42659138bac0c7074c379a5",
    "fixture": str(_mlr.EVENTBUS.root),
    "package": "eventbus",
    "source_digest": "9999cc1365c98e23",
    "task_sha256": "d0eb34a91a7b0935",
    "contract_sha256": "0be8e117bbb3050c",
    "gate_sha256": "542d27df3fff8f52",
    "oracle": "external_test.py",
    # §5 freezes `opencode` 1.18.29 by content. The digest, not the version string, is what the
    # semantic boundary binds and therefore what eligibility is decided on.
    "executor_sha256": "2f24593f1b8e578d",
    "model": "deepseek/deepseek-v4-flash",
    "variant": "high",
    "thinking": "enabled",
    "role": "implementer",
    "permission_flag": "--auto",
    "price_id": "deepseek-2026-09-09",
    "telemetry_version": "mlr-context-6",
    "profile_version": "profile-1",
    "samples": 6,                       # §8, fixed; no adaptive extension, no sequential stopping
    "max_attempts_per_slot": 3,         # §10
    "ceiling": 0.50,                    # §19
    "reserve": 0.10,                    # §19
    "host_derived": {                   # §5, as observed on the frozen host — never compared
        "interpreter": "CPython 3.9.6",
        "boundary_identity": "b88bd43109184459",
        "hermeticity_identity": "23a6e8001a46b70f",
    },
}

# Declared in MLR-C3-pilot-preregistration.md §12, before the first call, and read from here so the
# analysis cannot quietly acquire a threshold that suits the numbers it received.
MIN_CORRECT = 3
INCIDENTAL_BYTES = 200
SUBSTANTIAL_BYTES = 1000

NO_HEADROOM = "no-headroom"
LIMITED_HEADROOM = "limited-headroom"
MATERIAL_HEADROOM = "material-headroom"
INVALID = "pilot-invalid"


def _model_slug(model: str, variant: str | None) -> str:
    """A short, stable name for one model configuration, effort included."""
    slug = model.split("/", 1)[-1].replace("_", "-")
    return f"{slug}-{variant}" if variant else slug


def _experiment_id(model: str, variant: str | None, arms: list[str],
                   revision: str | None = None) -> str:
    """The series name. A revision is part of it, so a repaired instrument cannot inherit a name.

    The first paired series under this model was invalidated by its attribution, and a re-run must be
    a different experiment rather than a continuation of that one. Sharing the name would invite a
    later reader to pool the two, which is the thing the naming exists to prevent.
    """
    shape = "full-headroom" if arms == [_mlr.FULL] else "paired"
    tail = f"-{revision}" if revision else ""
    return f"mlr-{_model_slug(model, variant)}-{shape}{tail}"


def configuration(*, model: str, samples: int, arms: list[str], variant: str | None = None,
                  thinking: str = "enabled", revision: str | None = None,
                  purpose: str | None = None,
                  fixture: Path = _mlr.FIXTURE) -> dict[str, Any]:
    """Everything that must not vary within one series.

    The fixture is a parameter and not a constant, but **no key was added for it**. Five of the
    digests below are already fixture facts, so selecting a different fixture already moves the
    frozen identity that decides whether two records may be pooled or resumed into one another —
    adding a sixth name for the same distinction would be persistent state for a fact the record
    already derives (`P3`). Omitting it keeps every objectstore configuration byte-identical to the
    one this function produced before there was a second fixture.
    """
    spec = _mlr.fixture_for(fixture)
    return {
        # The model is part of the experiment's name, not only of its configuration hash. Two
        # series that differ by model are different experiments, and a name that hid that would
        # let a later reader pool them by reading the file listing.
        "experiment": _experiment_id(model, variant, arms, revision),
        "purpose": purpose or (
            "headroom: whether unrestricted `full` executions consume implementation source often "
            "enough for a paired source-visibility experiment to measure"
            if arms == [_mlr.FULL] else
            "paired: what happens to correctness and to implementation representation when direct "
            "source visibility is removed"),
        "evidence_class": "development",
        "model": model,
        "harness": "opencode-cli",
        "role": _mlr_run.ROLE,
        "permission_flag": _mlr_run.AUTO_FLAG,
        "arms": arms,
        "samples_per_arm": samples,
        "fixture_digest": _mlr.digest_tree(spec.root),
        "source_digest": _mlr.digest_tree(spec.source),
        "contract_sha256": _mlr.digest_file(spec.root / "base" / spec.contract),
        "task_sha256": _mlr.digest_file(spec.task),
        # The oracle actually used, not the one that came first. This bound `external_test.py`
        # while `_mlr_run.ORACLE` had moved to the second oracle, so a change to the oracle in force
        # would not have moved the frozen identity. It is now read from the fixture for the same
        # reason: the gate in force is the one that fixture ships, not a module-wide setting.
        "gate_sha256": _mlr.digest_file(spec.gate),
        "oracle": spec.oracle,
        # Model controls are part of the frozen configuration, not incidental runtime detail: a
        # provider that changes its default effort would otherwise alter a frozen experiment with
        # nothing in the record moving.
        "variant": variant,
        "thinking": thinking,
        "price_id": _pricing.DEEPSEEK_2026_09_09["id"],
        # Bytecode is version-specific, so the interpreter is part of what makes two arms the same
        # compiled system. The structural identity itself is recorded per execution, because it is a
        # property of the materialisation rather than of the fixture on disk.
        "interpreter": _mlr.interpreter_identity(),
        # What "no unintended copy is reachable" meant for this series: which categories were
        # checked, by which identities, over which roots. Widening the roots or declaring an
        # exposure changes the rule, and therefore changes the experiment.
        "hermeticity_identity": _mlr.preflight_identity(fixture=spec.root),
        # Bumped whenever what an origin *means* changes. A record carries the version its numbers
        # were produced under, so a later classifier cannot silently reinterpret an earlier result.
        "telemetry_version": "mlr-context-6",
        "profile_version": "profile-1",
        "attribution": ("every inbound representation normalised before attribution, whichever tool "
                        "carried it; origin follows causal evidence — linked ancestry, then artifact "
                        "identity, then authorship, then the activity that delivered the bytes; "
                        "content establishes representation form and never establishes that source "
                        "was read; ancestry of an artifact covers what that artifact delivered while "
                        "ancestry of content covers only the spans that replay it; material "
                        "components attributed individually whatever their share; representation "
                        "form and delivery route recorded separately; source, runtime-derived, "
                        "reconstructed and structural units never summed"),
        "consumed_definition": ("text appearing in a part OpenCode places in the message history "
                                "before a later model call"),
        "measurand": ("unique bytes of direct implementation-source representation consumed on "
                      "correct runs, per arm"),
    }


def slots(arms: list[str], samples: int) -> list[dict[str, Any]]:
    """Every attempt, allocated before any of them runs.

    Arm order rotates per sample so that in a paired series neither arm systematically leads and
    provider drift over a long run cannot line up with the comparison. A one-arm pilot inherits the
    same generator rather than a second code path that might diverge from it.
    """
    out: list[dict[str, Any]] = []
    for sample in range(1, samples + 1):
        offset = (sample - 1) % len(arms)
        for arm in arms[offset:] + arms[:offset]:
            out.append({"item": arm, "repeat": sample})
    return out


# What one more slot could conservatively cost, in dollars. Derived from the largest observed MLR
# run rather than the median, because a ceiling checked against an average is a ceiling that is
# exceeded half the time.
_RESERVE = 0.20


def _spent(measurements: list[dict[str, Any]]) -> float:
    """Money actually derived so far. Attempts with no priced usage contribute nothing."""
    total = 0.0
    for m in measurements:
        amount = (m.get("cost") or {}).get("amount")
        if isinstance(amount, (int, float)):
            total += float(amount)
    return round(total, 6)


# A slot that fails for setup or harness reasons is re-run, because an outage is not a measurement.
# Bounded, because a re-run that keeps failing is an infrastructure problem and pretending otherwise
# would burn the budget on it. Both records are always kept: a discarded failure is a falsified run.
MAX_ATTEMPTS_PER_SLOT = 3


def run_series(out: Path, *, model: str, samples: int, arms: list[str],
               keep: Path | None, variant: str | None = None,
               thinking: str = "enabled", budget: float | None = None,
               revision: str | None = None, purpose: str | None = None,
               hermetic_roots: list[Path] | None = None,
               preflight: "Callable[..., dict[str, Any]] | None" = None) -> dict[str, Any]:
    """Fill every preallocated slot exactly once with a *valid* attempt, checkpointing each.

    Only valid attempts close a slot. An invalid one is retained beside the slot it failed and the
    slot is offered again, which is what the pre-registration means by re-running into a fresh
    attempt rather than editing a record — and it is the reason a provider outage cannot quietly
    become "the agent consumed no implementation".
    """
    config = configuration(model=model, samples=samples, arms=arms, variant=variant,
                           thinking=thinking, revision=revision, purpose=purpose)
    measurements = _repeat.load_series(out, config)
    done = {(m["item"], m["repeat"]) for m in measurements
            if m.get("validity") == _mlr_run.VALID}
    for slot in slots(arms, samples):
        key = (slot["item"], slot["repeat"])
        tried = sum(1 for m in measurements
                    if (m.get("item"), m.get("repeat")) == key)
        while key not in done and tried < MAX_ATTEMPTS_PER_SLOT:
            # Budget is enforced *before* launching a slot, never by cutting one short: a
            # trajectory truncated for money would change the correctness distribution, which is
            # the quantity everything else is gated on.
            if budget is not None and _spent(measurements) + _RESERVE > budget:
                measurements.append({**slot, "attempt": tried + 1,
                                     "validity": _mlr_run.SETUP_FAILURE,
                                     "reason": f"budget ceiling {budget} would be exceeded"})
                _repeat.write_series(out, config, measurements)
                return {"config": config, "measurements": measurements,
                        "stopped": "budget-ceiling"}
            # Hermeticity is a precondition of the slot, not a property of the series: the previous
            # slot is one of the things that could have left a copy of the controlled evidence
            # behind, so every slot establishes its own environment before a call is made. A failure
            # here is an infrastructure precondition failure and not a semantic one — the slot stays
            # open under the existing resume semantics and no sample is consumed.
            check = preflight or _mlr.preflight
            environment = check(evidence_roots=hermetic_roots or [])
            if environment["status"] != _hermetic.CLEAN:
                measurements.append({
                    **slot, "attempt": tried + 1, "validity": _mlr_run.SETUP_FAILURE,
                    "reason": "hermeticity preflight refused the environment",
                    "hermeticity": {k: environment[k] for k in
                                    ("status", "hermeticity_identity", "scanned_roots",
                                     "excluded_roots", "claim", "unreadable")},
                    "hermeticity_findings": environment["findings"][:200]})
                _repeat.write_series(out, config, measurements)
                return {"config": config, "measurements": measurements,
                        "stopped": "hermeticity"}
            attempt = _mlr_run.run_attempt(slot["item"], model=model, keep=keep,
                                           variant=variant)
            attempt["hermeticity"] = {"status": environment["status"],
                                      "hermeticity_identity": environment["hermeticity_identity"],
                                      "scanned_roots": environment["scanned_roots"]}
            measurements.append({**slot, "attempt": tried + 1, **attempt})
            _repeat.write_series(out, config, measurements)
            tried += 1
            if attempt.get("validity") == _mlr_run.VALID:
                done.add(key)
    return {"config": config, "measurements": measurements}


def b1_configuration(stack: dict[str, Any] | None = None) -> dict[str, Any]:
    """The configuration `MLR-eventbus-b1-preregistration.md` describes, resolved from this host.

    Nothing here is a choice. The model, effort, N, revision and fixture all come from the frozen
    stack, and the digests come from the fixture the stack names — which is why an edited fixture
    changes the frozen identity and a resumed record from a different fixture is refused rather than
    extended.
    """
    stack = stack or B1
    return configuration(model=stack["model"], samples=stack["samples"],
                         arms=list(_mlr.ARMS), variant=stack["variant"],
                         thinking=stack["thinking"], revision=stack["revision"],
                         purpose=("cross-fixture replication: whether withholding direct readable "
                                  "implementation source changes the amount and kind of "
                                  "implementation representation entering the agent's reasoning "
                                  "when the software boundary is structurally different"),
                         fixture=Path(stack["fixture"]))


def _b1_record_extras(stack: dict[str, Any]) -> dict[str, Any]:
    """What the record carries beyond the configuration: the freeze it was run under.

    `execution_commit` is read at run time and is a fact about *when* the code ran, not a proof of
    it. It says which tree produced these attempts; it does not establish that a matching tree in
    anyone else's clone would produce them, and it is not evidence of when a semantic call was made.
    """
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=False)
    return {
        "preregistration": stack["preregistration"],
        "preregistration_sha256": stack["preregistration_sha256"],
        "execution_commit": head.stdout.strip() or None,
        "ceiling": stack["ceiling"],
        "reserve": stack["reserve"],
        "max_attempts_per_slot": stack["max_attempts_per_slot"],
        "samples_per_arm": stack["samples"],
        "evidence_class": "experiment",
        "host_derived_identities": (
            "interpreter, semantic boundary and hermeticity rule are computed on the execution "
            "host; recorded per measurement"),
        "order": [{"slot": i + 1, "pair": s["repeat"], "arm": s["item"]}
                  for i, s in enumerate(slots(list(_mlr.ARMS), stack["samples"]))],
    }


def b1_preflight(*, executor: Path | None, evidence_roots: list[Path] | None = None,
                 stack: dict[str, Any] | None = None,
                 keep: Path | None = None) -> dict[str, Any]:
    """Resolve and validate exactly what `b1` would run, without buying anything.

    No provider is contacted, no slot is consumed and no experimental record is written. A green
    report is a statement about this host and this tree; it is not a qualification, and it is not
    evidence that any earlier experiment ran.
    """
    stack = stack or B1
    config = b1_configuration(stack)
    document = ROOT / stack["preregistration"]
    report = _mlr_series.launchable(fixture=Path(stack["fixture"]), executor=executor,
                                    stack=stack, evidence_roots=evidence_roots)
    frozen_document = (document.is_file()
                       and _mlr.digest_file(document) == stack["preregistration_sha256"])
    report["checks"].insert(0, {
        "check": "the preregistration is the committed frozen one", "ok": frozen_document,
        "detail": {"path": stack["preregistration"],
                   "frozen": stack["preregistration_sha256"][:16],
                   "observed": _mlr.digest_file(document)[:16] if document.is_file() else None},
        "blocking": True})
    try:
        _mlr_series.config_fixture(config, stack)
        agrees, disagreement = True, None
    except _mlr_series.SeriesRefused as exc:
        agrees, disagreement = False, str(exc)
    report["checks"].insert(1, {
        "check": "the resolved configuration is the frozen stack's fixture", "ok": agrees,
        "detail": disagreement, "blocking": True})
    # Checked here because it is the one launch argument whose mistakes cost money. Retaining a
    # slot's evidence happens after the trajectory is bought, so a `--keep` that cannot be written
    # is a paid sample discovered too late; a digest comparison of a path costs nothing.
    if keep is not None:
        usable, detail = _retention_usable(Path(keep))
        report["checks"].insert(2, {
            "check": "the evidence retention directory can be written", "ok": usable,
            "detail": detail, "blocking": True})
    blocking = [c for c in report["checks"] if c["blocking"] and not c["ok"]]
    report.update({
        "experiment": config["experiment"],
        "identity_matches_the_freeze": config["experiment"] == stack["experiment"],
        "frozen_identity": _repeat.frozen_identity(config),
        "n_pairs": stack["samples"],
        "slots": len(slots(list(_mlr.ARMS), stack["samples"])),
        "order": _b1_record_extras(stack)["order"],
        "max_attempts_per_slot": stack["max_attempts_per_slot"],
        "ceiling": stack["ceiling"], "reserve": stack["reserve"],
        "telemetry_version": config["telemetry_version"],
        "profile_version": config["profile_version"],
        "launchable": not blocking,
        "blocked_by": [c["check"] for c in blocking],
        "note": ("preflight only: no provider call, no semantic slot, no experimental result. "
                 "A launchable report does not re-qualify the instrument and does not re-establish "
                 "any historical run."),
    })
    return report


def _retention_usable(keep: Path) -> tuple[bool, dict[str, Any]]:
    """Whether `--keep` names somewhere a slot's evidence can actually be copied to."""
    try:
        keep.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, {"path": str(keep), "error": f"{type(exc).__name__}: {exc}"}
    if not keep.is_dir():
        return False, {"path": str(keep), "error": "not a directory"}
    if not os.access(keep, os.W_OK):
        return False, {"path": str(keep), "error": "not writable"}
    return True, {"path": str(keep)}


def run_b1(out: Path, *, executor: Path, credentials: dict[str, Path] | None = None,
           keep: Path | None = None, evidence_roots: list[Path] | None = None,
           stack: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute the frozen `eventbus-b1` replication through the semantic boundary.

    Refuses to start unless `b1_preflight` is launchable, so the money is never spent discovering
    something a digest comparison already knew. There is no unbounded fallback: if the boundary
    cannot be constructed the series does not run.
    """
    stack = stack or B1
    ready = b1_preflight(executor=executor, evidence_roots=evidence_roots, stack=stack, keep=keep)
    if not ready["launchable"]:
        raise _mlr_series.SeriesRefused(
            "b1 is not launchable on this host: " + "; ".join(ready["blocked_by"]))
    config = b1_configuration(stack)
    return _mlr_series.run_bounded_series(
        out, config=config, stack=stack, arms=list(_mlr.ARMS), samples=stack["samples"],
        executor=Path(ready["executor"]["path"]), slots=slots, credentials=credentials, keep=keep,
        budget=stack["ceiling"], reserve=stack["reserve"],
        max_attempts_per_slot=stack["max_attempts_per_slot"],
        evidence_roots=evidence_roots, extra=_b1_record_extras(stack))


def _source_bytes(measurement: dict[str, Any]) -> int:
    return int((measurement.get("context") or {}).get(
        "implementation_source_unique_bytes") or 0)


def _runtime_bytes(measurement: dict[str, Any]) -> int:
    return int((measurement.get("context") or {}).get(
        "implementation_runtime_unique_bytes") or 0)


def analyse(record: dict[str, Any]) -> dict[str, Any]:
    """Classify a completed series against the pre-registered categories, and nothing else.

    Correctness gates headroom: consumption on a run that did not do the task says nothing about
    what successful reasoning needed. Failed runs are summarised separately rather than dropped,
    because a pilot where `full` cannot do the work is a finding about the fixture.
    """
    measurements = record.get("measurements") or []
    arms = record.get("arms") or [_mlr.FULL]
    per_arm: dict[str, Any] = {}
    for arm in arms:
        rows = [m for m in measurements if m.get("item") == arm]
        valid = [m for m in rows if m.get("validity") == _mlr_run.VALID]
        correct = [m for m in valid if (m.get("outcome") or {}).get("correct")]
        failed = [m for m in valid if not (m.get("outcome") or {}).get("correct")]
        source = sorted(_source_bytes(m) for m in correct)
        per_arm[arm] = {
            "attempts": len(rows),
            "valid": len(valid),
            "invalid": [{"repeat": m["repeat"], "validity": m.get("validity"),
                         "reason": m.get("reason")} for m in rows
                        if m.get("validity") != _mlr_run.VALID],
            "correct": len(correct),
            "correct_source_bytes": source,
            "correct_runs_reading_source": sum(1 for b in source if b > 0),
            "median_source_bytes": statistics.median(source) if source else 0,
            "correct_runtime_bytes": sorted(_runtime_bytes(m) for m in correct),
            "failed_source_bytes": sorted(_source_bytes(m) for m in failed),
            "tokens_input": [(m.get("context") or {}).get("tokens", {}).get("input")
                             for m in valid],
            "model_calls": [(m.get("context") or {}).get("model_calls") for m in valid],
            "elapsed_seconds": [m.get("elapsed_seconds") for m in rows],
        }

    arm = per_arm.get(_mlr.FULL, {})
    correct = arm.get("correct", 0)
    reading = arm.get("correct_runs_reading_source", 0)
    median = arm.get("median_source_bytes", 0)
    # Fail closed. An execution whose telemetry is absent is not an execution that consumed
    # nothing: reading it as zero would turn an infrastructure failure into the cheapest run in the
    # series, and the primary measurand is a byte count where zero is a meaningful answer.
    missing_telemetry = [m["repeat"] for m in measurements
                         if m.get("validity") == _mlr_run.VALID
                         and (not m.get("context")
                              or not (m.get("profile") or {}).get("complete", False))]
    if correct < MIN_CORRECT or missing_telemetry:
        verdict = INVALID
    elif reading <= 1 or median < INCIDENTAL_BYTES:
        verdict = NO_HEADROOM
    elif reading * 2 >= correct and median >= SUBSTANTIAL_BYTES:
        verdict = MATERIAL_HEADROOM
    else:
        verdict = LIMITED_HEADROOM
    return {"experiment": record.get("experiment"), "arms": per_arm,
            "missing_telemetry": missing_telemetry, "headroom": verdict}


def _ctx(measurement: dict[str, Any], *path: str, default: Any = None) -> Any:
    node: Any = measurement.get("context") or {}
    for key in path:
        if not isinstance(node, dict):
            return default
        node = node.get(key)
    return default if node is None else node


def _stage(measurement: dict[str, Any]) -> dict[str, Any]:
    stages = ((measurement.get("profile") or {}).get("stages") or [{}])
    return stages[0] if stages else {}


def _row(measurement: dict[str, Any]) -> dict[str, Any]:
    """One execution, flattened into the fields the paired report compares.

    Missing telemetry stays missing. A run whose profile is incomplete keeps `None` in every derived
    field rather than a zero, because the primary measurand is a byte count where zero is a
    meaningful answer and an outage must never be able to impersonate one.
    """
    stage = _stage(measurement)
    complete = bool((measurement.get("profile") or {}).get("complete"))
    valid = measurement.get("validity") == _mlr_run.VALID and complete
    usage = stage.get("usage") or {}
    tools = stage.get("tools") or {}
    timing = stage.get("time") or {}
    provenance = _ctx(measurement, "by_provenance", default={})
    return {
        "arm": measurement.get("item"),
        "repeat": measurement.get("repeat"),
        "attempt": measurement.get("attempt", 1),
        "validity": measurement.get("validity"),
        "complete": complete,
        "valid": valid,
        "correct": (measurement.get("outcome") or {}).get("correct") if valid else None,
        "gate": (measurement.get("outcome") or {}).get("gate_passed") if valid else None,
        "regression": (measurement.get("outcome") or {}).get("regression_passed") if valid else None,
        "source": _ctx(measurement, "implementation_source_unique_bytes") if valid else None,
        "runtime_repr": _ctx(measurement, "implementation_runtime_unique_bytes") if valid else None,
        "disclosure": _ctx(measurement, "disclosure", "unique_bytes") if valid else None,
        "contract_doc": (provenance.get("public-contract") or {}).get("unique_bytes")
                        if valid else None,
        "application": (provenance.get("application") or {}).get("unique_bytes") if valid else None,
        "behaviour": (provenance.get("behaviour") or {}).get("unique_bytes") if valid else None,
        "routes": sorted((_ctx(measurement, "by_route", default={}) or {}).keys()) if valid else [],
        "calls": _ctx(measurement, "model_calls") if valid else None,
        "input_tokens": usage.get("input") if valid else None,
        "output_tokens": usage.get("output") if valid else None,
        "cache_read": usage.get("cache_read") if valid else None,
        "reasoning_tokens": usage.get("reasoning") if valid else None,
        "executor_cost": usage.get("executor_cost") if valid else None,
        "tool_calls": tools.get("calls") if valid else None,
        "failed_tool_calls": tools.get("failed_calls") if valid else None,
        "by_tool": tools.get("by_tool") if valid else None,
        "tool_seconds": tools.get("seconds") if valid else None,
        "session_seconds": timing.get("session_span_seconds") if valid else None,
        "model_seconds": timing.get("model_seconds_derived") if valid else None,
        "verification_seconds": timing.get("verification_seconds") if valid else None,
        "elapsed_seconds": measurement.get("elapsed_seconds"),
        "reason": measurement.get("reason"),
    }


def _spread(values: list[Any]) -> dict[str, Any]:
    """Counts, median and range. No confidence interval: these are paired, not independent draws."""
    numbers = sorted(v for v in values if isinstance(v, (int, float)))
    if not numbers:
        return {"n": 0, "median": None, "min": None, "max": None, "values": []}
    return {"n": len(numbers), "median": statistics.median(numbers),
            "min": numbers[0], "max": numbers[-1], "values": numbers}


BOTH, FULL_ONLY, CONTRACT_ONLY, NEITHER, PAIR_INVALID = (
    "both-correct", "full-only", "contract-only", "neither-correct", "pair-invalid")


def paired_analysis(record: dict[str, Any]) -> dict[str, Any]:
    """The paired comparison, reported as pairs and distributions rather than as a score.

    Correctness is resolved first and gates everything else: the context comparison is defined on
    runs that did the task, so a `contract` trajectory that failed quickly after reading nothing is
    never allowed to look efficient. Source and runtime-derived representation stay separate columns
    because they are not commensurable, and the shift they can express — source removed, interior
    rebuilt another way — is the outcome the whole design exists to be able to see.
    """
    rows = [_row(m) for m in record.get("measurements") or []]
    valid = [r for r in rows if r["valid"]]
    by_arm = {arm: [r for r in valid if r["arm"] == arm] for arm in _mlr.ARMS}

    pairs: list[dict[str, Any]] = []
    for repeat in sorted({r["repeat"] for r in rows}):
        full = next((r for r in by_arm[_mlr.FULL] if r["repeat"] == repeat), None)
        contract = next((r for r in by_arm[_mlr.CONTRACT] if r["repeat"] == repeat), None)
        if full is None or contract is None:
            pattern = PAIR_INVALID
        elif full["correct"] and contract["correct"]:
            pattern = BOTH
        elif full["correct"]:
            pattern = FULL_ONLY
        elif contract["correct"]:
            pattern = CONTRACT_ONLY
        else:
            pattern = NEITHER
        pairs.append({"repeat": repeat, "pattern": pattern,
                      "full": full, "contract": contract})

    def spread(arm: str, field: str, correct_only: bool = True) -> dict[str, Any]:
        rows_ = [r for r in by_arm[arm] if (r["correct"] if correct_only else True)]
        return _spread([r[field] for r in rows_])

    fields = ("source", "runtime_repr", "disclosure", "contract_doc", "application", "behaviour",
              "calls", "input_tokens", "output_tokens", "cache_read", "reasoning_tokens",
              "tool_calls", "failed_tool_calls", "tool_seconds", "session_seconds",
              "model_seconds", "verification_seconds", "elapsed_seconds", "executor_cost")
    arms = {}
    for arm in _mlr.ARMS:
        correct = [r for r in by_arm[arm] if r["correct"]]
        arms[arm] = {
            "executions": sum(1 for r in rows if r["arm"] == arm),
            "valid": len(by_arm[arm]),
            "invalid": [{"repeat": r["repeat"], "validity": r["validity"],
                         "complete": r["complete"], "reason": r["reason"]}
                        for r in rows if r["arm"] == arm and not r["valid"]],
            "correct": len(correct),
            "on_correct": {f: spread(arm, f) for f in fields},
            "on_all_valid": {f: spread(arm, f, correct_only=False) for f in fields},
        }

    contract_source = [r["source"] for r in by_arm[_mlr.CONTRACT] if r["source"] is not None]
    return {
        "experiment": record.get("experiment"),
        "pairs": pairs,
        "pattern_counts": {p: sum(1 for x in pairs if x["pattern"] == p)
                           for p in (BOTH, FULL_ONLY, CONTRACT_ONLY, NEITHER, PAIR_INVALID)},
        "arms": arms,
        # Direct source must be structurally zero in `contract`. Anything else is a treatment
        # failure, not ordinary variation, and is surfaced rather than averaged away.
        "treatment_integrity": {
            "contract_source_bytes": contract_source,
            "contract_source_is_zero": all(v == 0 for v in contract_source),
        },
        "incomplete_profiles": [{"arm": r["arm"], "repeat": r["repeat"]}
                                for r in rows if r["validity"] == _mlr_run.VALID
                                and not r["complete"]],
        # §19 is a promise about money, so the analysis states the figure together with what the
        # figure omits. Recomputed from the measurements rather than read off the record, so a
        # record written before the account was persisted is reported to the same standard.
        "spend": _mlr_series.spend(record.get("measurements") or []),
    }


def retrospect(record: dict[str, Any], *, evidence_root: Path | None = None) -> dict[str, Any]:
    """Re-attribute a completed series' retained sessions under the attribution in force today.

    **This is diagnosis, not a result.** The record it reads is not modified and the numbers it
    returns are not that experiment's numbers: they were produced by a later classifier under a
    later telemetry version, and both versions are stated so the two can never be conflated. A
    series' reported outcome is whatever it reported when it ran.

    It exists because a repaired instrument has to be shown to explain the trajectories that broke
    the last one before another is bought. Every retained session is walked, every item is
    classified, and anything the instrument cannot account for is returned rather than summarised
    away.
    """
    out: list[dict[str, Any]] = []
    for measurement in record.get("measurements") or []:
        kept = Path(measurement.get("evidence") or "")
        # Retained sessions outlive the directory they were written to. When they have been moved,
        # they are found by the name the record already carries rather than by a second index.
        root = Path(evidence_root) / kept.name if evidence_root else kept
        db = root / "worker.db"
        built = _rebuilt(measurement)
        if not db.is_file() or built is None:
            out.append({**_slot_identity(measurement), "available": False})
            continue
        led = _mlr_context.consumed(db, built)
        forms = {}
        for item in led["items"]:
            for form, size in item["form_bytes"].items():
                forms[form] = forms.get(form, 0) + size
        out.append({
            **_slot_identity(measurement),
            "available": True,
            "session": root.name,
            "direct_source_unique_bytes": led["implementation_source_unique_bytes"],
            "runtime_unique_bytes": led["implementation_runtime_unique_bytes"],
            "source_equivalent_reconstruction": led["source_equivalent_reconstruction"],
            "metadata_references": led["implementation_metadata"]["references"],
            "by_provenance": {k: v["unique_bytes"] for k, v in led["by_provenance"].items()},
            "by_form_bytes": dict(sorted(forms.items())),
            "by_basis": led["by_basis"],
            "unresolved": led["unresolved"],
            "contradictions": led["contradictions"],
            "items": len(led["items"]),
        })
    clean = all(r.get("available") and not r["contradictions"] and not r["unresolved"]["items"]
                for r in out)
    return {
        "kind": "retrospective diagnostic analysis — not the recorded experiment result",
        "source_record": {"experiment": record.get("experiment"),
                          "frozen_identity": record.get("frozen_identity"),
                          "telemetry_version": record.get("telemetry_version")},
        "recomputed_under": {"telemetry_version": configuration(
            model=record.get("model") or "", samples=1,
            arms=record.get("arms") or [_mlr.FULL])["telemetry_version"]},
        "evidence_root": str(evidence_root) if evidence_root else None,
        "trajectories": out,
        "explained": clean,
        "unavailable": [r for r in out if not r.get("available")],
    }


def _slot_identity(measurement: dict[str, Any]) -> dict[str, Any]:
    return {"arm": measurement.get("arm"), "repeat": measurement.get("repeat"),
            "attempt": measurement.get("attempt"), "validity": measurement.get("validity"),
            "correct": (measurement.get("outcome") or {}).get("correct")}


def _rebuilt(measurement: dict[str, Any]) -> dict[str, Any] | None:
    """The arm layout a retained session ran under, recovered from what the record already holds.

    Path classification needs to know where the workspace and the runtime were. Both are prefixes of
    the attempt directory the record kept, so nothing has to be stored twice to make an old session
    readable again.

    Which *fixture* the session belongs to is carried through as well. Attribution selects its
    module fingerprints from `package` and path classification finds the vendored copy from
    `vendored`; both fall back to objectstore when absent, which is right for a record written
    before there was a second fixture and wrong for one that names eventbus. Dropping them here
    would have re-read an eventbus session with objectstore fingerprints and reported its `full`
    arm's direct source as zero — the instrument confidently answering about the wrong module,
    which is the defect class this programme has already paid for twice.
    """
    layout = {"arm": measurement.get("arm")}
    for field in ("fixture", "package", "vendored"):
        if measurement.get(field) is not None:
            layout[field] = measurement[field]

    event_dir = measurement.get("event_dir") or ""
    marker = "/arm/workspace/"
    if marker in event_dir:
        root = event_dir.split(marker)[0]
        return {**layout, "workspace": f"{root}/arm/workspace", "runtime": f"{root}/arm/runtime"}
    # Attempts run inside a constructed semantic view record the attempt directory relative to the
    # view, so the layout comes from the absolute path the evidence gate already kept.
    log = (measurement.get("evidence_gate") or {}).get("log") or ""
    if "/workspace/" in log:
        view = log.split("/workspace/")[0]
        return {**layout, "workspace": f"{view}/workspace", "runtime": f"{view}/runtime"}
    return None


def _which_executor() -> Path | None:
    """The executor this host would use if none was named. Discovery only; eligibility is separate."""
    found = shutil.which("opencode")
    return Path(found) if found else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("pilot", help="run the pre-registered `full`-only headroom pilot")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model", default="opencode/nemotron-3-ultra-free")
    p.add_argument("--samples", type=int, default=6)
    p.add_argument("--keep", type=Path, default=None)
    p.add_argument("--variant", default=None, help="provider reasoning effort, frozen per series")
    p.add_argument("--budget", type=float, default=None,
                   help="hard spend ceiling in USD, checked before launching each slot")

    q = sub.add_parser("paired", help="run the pre-registered paired full/contract comparison")
    q.add_argument("--out", type=Path, required=True)
    q.add_argument("--model", default="opencode/nemotron-3-ultra-free")
    q.add_argument("--samples", type=int, default=8)
    q.add_argument("--keep", type=Path, default=None)
    q.add_argument("--variant", default=None, help="provider reasoning effort, frozen per series")
    q.add_argument("--budget", type=float, default=None, help="hard spend ceiling in USD")
    q.add_argument("--revision", default=None,
                   help="series revision, so a repaired instrument does not inherit a name")
    q.add_argument("--purpose", default=None, help="what this series is for, recorded verbatim")
    q.add_argument("--evidence-root", type=Path, action="append", default=[],
                   help="an evidence archive to include in the per-slot hermeticity scan")

    b = sub.add_parser("b1-preflight",
                       help="resolve and validate the frozen eventbus-b1 stack; buys nothing")
    b.add_argument("--executor", type=Path, default=None,
                   help="the opencode binary to use; defaults to the one on PATH. Point this at an "
                        "isolated installation matching the frozen identity rather than changing "
                        "the one this host normally uses")
    b.add_argument("--evidence-root", type=Path, action="append", default=[],
                   help="an evidence archive to include in the hermeticity scan")
    b.add_argument("--clear-stale-views", action="store_true",
                   help="remove semantic views a killed process left behind")
    b.add_argument("--keep", type=Path, default=None,
                   help="the directory b1 would retain each slot's evidence in; checked here so a "
                        "path that cannot be written is found before a trajectory is bought")
    b.add_argument("--out", type=Path, default=None)

    e = sub.add_parser("b1", help="execute the frozen eventbus-b1 replication (spends money)")
    e.add_argument("--out", type=Path, required=True)
    e.add_argument("--executor", type=Path, default=None)
    e.add_argument("--credential", action="append", default=[], metavar="NAME=PATH",
                   help="a provider auth file to stage into the constructed home, destroyed with "
                        "the view")
    e.add_argument("--keep", type=Path, default=None,
                   help="directory to retain each slot's extracted evidence in")
    e.add_argument("--evidence-root", type=Path, action="append", default=[])

    a = sub.add_parser("analyse", help="classify a completed series")
    a.add_argument("--record", type=Path, required=True)
    a.add_argument("--paired", action="store_true", help="report the paired comparison")

    h = sub.add_parser("preflight",
                       help="check that no unintended copy of the controlled evidence is reachable")
    h.add_argument("--evidence-root", type=Path, action="append", default=[],
                   help="an evidence archive to include in the scanned roots")
    h.add_argument("--clean", action="store_true",
                   help="remove ephemeral arm materialisations found under the scanned roots")
    h.add_argument("--out", type=Path, default=None)

    r = sub.add_parser("retrospect",
                       help="re-attribute a completed series' retained sessions for diagnosis")
    r.add_argument("--record", type=Path, required=True)
    r.add_argument("--out", type=Path, default=None)
    r.add_argument("--evidence-root", type=Path, default=None,
                   help="directory holding the retained sessions, if they have been moved")

    args = ap.parse_args(argv)
    if args.command == "pilot":
        record = run_series(args.out, model=args.model, samples=args.samples,
                            arms=[_mlr.FULL], keep=args.keep,
                            variant=getattr(args, "variant", None),
                            budget=getattr(args, "budget", None))
        print(json.dumps(analyse({**record["config"], **record}), indent=2, sort_keys=True))
        return 0
    if args.command == "paired":
        record = run_series(args.out, model=args.model, samples=args.samples,
                            arms=list(_mlr.ARMS), keep=args.keep,
                            revision=getattr(args, "revision", None),
                            purpose=getattr(args, "purpose", None),
                            hermetic_roots=list(getattr(args, "evidence_root", []) or []),
                            variant=getattr(args, "variant", None),
                            budget=getattr(args, "budget", None))
        print(json.dumps(paired_analysis({**record["config"], **record}),
                         indent=2, sort_keys=True))
        return 0
    if args.command in {"b1-preflight", "b1"}:
        executor = args.executor or _which_executor()
        roots = [Path(p) for p in (getattr(args, "evidence_root", []) or [])]
        if getattr(args, "clear_stale_views", False):
            for removed in _mlr_series.clear_stale_views():
                print(f"removed stale view {removed}", file=sys.stderr)
        if args.command == "b1-preflight":
            report = b1_preflight(executor=executor, evidence_roots=roots,
                                  keep=Path(args.keep) if getattr(args, "keep", None) else None)
            text = json.dumps(report, indent=2, sort_keys=True)
            if args.out:
                Path(args.out).write_text(text + "\n", encoding="utf-8")
            print(text)
            return 0 if report["launchable"] else 1
        credentials = {}
        for pair in args.credential or []:
            name, _, path = pair.partition("=")
            if not name or not path:
                raise SystemExit(f"--credential expects NAME=PATH, got {pair!r}")
            credentials[name] = Path(path)
        try:
            record = run_b1(args.out, executor=executor, credentials=credentials,
                            keep=args.keep, evidence_roots=roots)
        except _mlr_series.SeriesRefused as exc:
            print(json.dumps({"refused": str(exc)}, indent=2), file=sys.stderr)
            return 2
        print(json.dumps({k: record[k] for k in record
                          if k not in ("config", "measurements")}, indent=2, sort_keys=True))
        return 0 if record.get("stopped") is None else 1
    if args.command == "preflight":
        roots = [Path(p) for p in (args.evidence_root or [])]
        removed = []
        if args.clean:
            import tempfile as _tempfile
            for stale in _mlr.ephemeral_materialisations(
                    [Path(_tempfile.gettempdir()), Path("/tmp"), *roots]):
                shutil.rmtree(stale, ignore_errors=True)
                removed.append(str(stale))
        report = _mlr.preflight(evidence_roots=roots)
        report["removed_materialisations"] = removed
        text = json.dumps(report, indent=2, sort_keys=True)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0 if report["status"] == _hermetic.CLEAN else 1
    if args.command == "retrospect":
        record = json.loads(Path(args.record).read_text(encoding="utf-8"))
        report = retrospect(record, evidence_root=getattr(args, "evidence_root", None))
        text = json.dumps(report, indent=2, sort_keys=True)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(text)
        return 0 if report["explained"] else 1
    record = json.loads(Path(args.record).read_text(encoding="utf-8"))
    reporter = paired_analysis if args.paired else analyse
    print(json.dumps(reporter(record), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

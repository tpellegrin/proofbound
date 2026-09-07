#!/usr/bin/env python3
"""Evaluation scenarios: frozen engineering situations with a known semantic target.

A scenario is a synthetic project in which one specific engineering contradiction has been
planted, discoverable from the accepted context a reflector legitimately receives. It is the
unit of comparability: two evaluation runs mean the same thing only if they ran the same
scenario content.

**Ground truth is a property, never a phrasing.** The planted condition is recorded as a
statement of what is wrong, and a reflector may express the same finding many ways. Exact
answer matching would measure paraphrase rather than comprehension.

**The property is grader-only.** It must never reach the system under test. `visible_files`
is what the trial copies into the fixture; the property lives in the manifest, which is not
copied. A scenario that leaked its own answer would measure nothing.

Scenario identity covers the manifest and every fixture byte — the things that define the
engineering problem. It deliberately excludes the grader model and rubric wording, which
belong to the evaluation configuration: re-grading retained evidence with a better grader is
a new measurement of the *same* scenario, not a different scenario.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _artifact_identity import artifact_identity_file  # noqa: E402

SCENARIO_FORMAT = "proofbound-eval-scenario-v1"
SUPPORTED_SCENARIO_FORMATS = (SCENARIO_FORMAT,)

# Two manifest shapes. `single` is the original form and is frozen: every scenario the first
# baseline and the calibration screening measured uses it, and its identity must never move.
# `multi` carries several independent planted obligations (E19). A manifest declares exactly
# one shape, and the shape decides how identity is computed — see `identity` below.
SINGLE = "single"
MULTI = "multi"

REQUIRED = frozenset({"format", "kind", "summary", "artifact", "review_purpose"})
SINGLE_ONLY = frozenset({"property", "dimensions", "reachable_from"})
MULTI_ONLY = frozenset({"properties"})
OPTIONAL = frozenset({"notes", "distractors"})
KINDS = frozenset({"regression", "capability"})

# The treatment artifact for the P12 control: a synthetic spec-author attempt report standing
# for the execution narrative that produced the reviewed artifact. It lives *beside* the fixture,
# never inside it, so it changes no byte the fixture contributes and therefore cannot move a
# scenario's identity — the placement is load-bearing and is tested.
AUTHOR_REPORT = "author-report.md"

PROPERTY_FIELDS = frozenset({"id", "statement", "dimension", "reachable_from"})
PROPERTY_ID = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
MIN_PROPERTIES = 2
MAX_PROPERTIES = 4

# The difficulty dimensions a calibration scenario may declare. Closed, because the point of
# declaring one is to check it: a free-text label would assert difficulty without evidence.
# Chosen in evaluation.md E16.4 by one filter — could a change in Proofbound plausibly change
# the outcome? — which is what the first four scenarios could not satisfy.
DEPENDENCY_DISTANCE = "dependency-distance"
COMPETING_CONCERNS = "competing-concerns"
INDIRECT_IMPLICATION = "indirect-implication"
DIFFICULTY_DIMENSIONS = frozenset({DEPENDENCY_DISTANCE, COMPETING_CONCERNS, INDIRECT_IMPLICATION})

# What makes one *obligation* hard, as opposed to what makes a scenario hard. `competing-concerns`
# is absent on purpose: it describes an artifact crowded with rival concerns, which is a property
# of the scenario and not of any single obligation in it.
DIRECT = "direct"
PATTERN_VERSUS_AUTHORITY = "pattern-versus-authority"
PROPERTY_DIMENSIONS = frozenset({DIRECT, INDIRECT_IMPLICATION, DEPENDENCY_DISTANCE,
                                 PATTERN_VERSUS_AUTHORITY})

# V1 evaluates one role. Widening this is a new evaluation thesis, not a config change.
REFLECTOR_ROLE = "spec-reflector"


class ScenarioError(ValueError):
    """A scenario cannot be interpreted, so no trial derived from it would be meaningful."""


def _relative(raw: Any, label: str) -> str:
    if not isinstance(raw, str) or not raw.strip() or raw != raw.strip():
        raise ScenarioError(f"{label} must be a non-empty unpadded string")
    if raw.startswith("/") or ".." in raw.split("/") or "\\" in raw:
        raise ScenarioError(f"unsafe {label}: {raw!r}")
    return raw


def load(directory: Path) -> dict[str, Any]:
    """Read and validate one scenario, failing closed on anything unrecognized."""
    directory = Path(directory).resolve()
    manifest_path = directory / "scenario.json"
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ScenarioError(f"scenario manifest missing: {manifest_path}") from exc
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ScenarioError(f"scenario manifest unreadable: {manifest_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ScenarioError("scenario manifest must be a JSON object")

    if raw.get("format") not in SUPPORTED_SCENARIO_FORMATS:
        raise ScenarioError(f"unsupported scenario format: {raw.get('format')!r}")
    missing = sorted(REQUIRED - set(raw))
    if missing:
        raise ScenarioError(f"scenario is missing {', '.join(missing)}")
    shape = _shape(raw)
    allowed = REQUIRED | OPTIONAL | (MULTI_ONLY if shape == MULTI else SINGLE_ONLY)
    extra = sorted(set(raw) - allowed)
    if extra:
        raise ScenarioError(f"unknown scenario field(s) for a {shape} scenario: "
                            f"{', '.join(extra)}")
    if raw["kind"] not in KINDS:
        raise ScenarioError(f"scenario kind must be one of {sorted(KINDS)}: {raw['kind']!r}")
    if not isinstance(raw["summary"], str) or len(raw["summary"].strip()) < 20:
        raise ScenarioError("scenario summary must be a substantive sentence")

    artifact = _relative(raw["artifact"], "artifact")
    fixture = directory / "fixture"
    if not fixture.is_dir():
        raise ScenarioError(f"scenario fixture directory missing: {fixture}")
    if not (fixture / artifact).is_file():
        raise ScenarioError(f"scenario artifact is not in the fixture: {artifact}")
    contract = directory / "contract.md"
    if not contract.is_file():
        raise ScenarioError(f"scenario contract missing: {contract}")

    # The reflector is challenging an artifact it did not author, so the contract must
    # declare a purpose a spec-reflector can satisfy. Checked against the live registry
    # here on purpose: a scenario is authored now, for the system as it is now.
    from _review_purpose import qualifying_roles
    if REFLECTOR_ROLE not in qualifying_roles(raw["review_purpose"]):
        raise ScenarioError(
            f"review purpose {raw['review_purpose']!r} cannot be satisfied by {REFLECTOR_ROLE}")

    files = sorted(p for p in fixture.rglob("*") if p.is_file())
    if not files:
        raise ScenarioError(f"scenario fixture is empty: {fixture}")

    properties = _properties(raw, shape)
    for prop in properties:
        for rel in prop["reachable_from"]:
            if not (fixture / rel).is_file():
                raise ScenarioError(f"reachable_from names a file not in the fixture: {rel}")
    # A single-shape scenario keeps its scenario-level dimensions verbatim; a multi-shape one
    # derives them from its properties, because a duplicate declaration could disagree with the
    # properties it summarises.
    dimensions = (_dimensions(raw) if shape == SINGLE
                  else sorted({p["dimension"] for p in properties if p["dimension"]}))
    reachable = sorted({r for p in properties for r in p["reachable_from"]})
    distractors = _distractors(raw)

    scenario = {
        "id": directory.name,
        "path": str(directory),
        "format": raw["format"],
        "kind": raw["kind"],
        "summary": raw["summary"].strip(),
        "artifact": artifact,
        "review_purpose": raw["review_purpose"],
        "contract": str(contract),
        "fixture": str(fixture),
        "files": [p.relative_to(fixture).as_posix() for p in files],
        "shape": shape,
        # Evaluation configuration, not scenario definition. Absent unless the scenario carries
        # a treatment artifact; never part of `identity` below.
        "author_report": str(directory / AUTHOR_REPORT)
                         if (directory / AUTHOR_REPORT).is_file() else None,
        # Normalised for every consumer: a single-property scenario is a one-element vector, so
        # nothing downstream needs to know which shape it came from.
        "properties": properties,
        # Declared calibration metadata. Deliberately absent from `identity` below: none of it
        # changes a single byte the system under test receives, and E3 already puts the rubric
        # on the configuration side of that line for the same reason.
        "dimensions": dimensions,
        "reachable_from": reachable,
        "distractors": distractors,
    }
    if shape == SINGLE:
        # Kept so existing readers and the leak check keep working unchanged.
        scenario["property"] = properties[0]["statement"]
    scenario["identity"] = identity(scenario)
    _assert_property_not_leaked(scenario)
    _assert_declared_difficulty_is_real(scenario, contract.read_text(encoding="utf-8"))
    return scenario


def _shape(raw: dict[str, Any]) -> str:
    """Which manifest form this is. Exactly one, never both."""
    has_single, has_multi = "property" in raw, "properties" in raw
    if has_single and has_multi:
        raise ScenarioError("a scenario declares either `property` or `properties`, never both")
    if not has_single and not has_multi:
        raise ScenarioError("scenario is missing property")
    return MULTI if has_multi else SINGLE


def _properties(raw: dict[str, Any], shape: str) -> list[dict[str, Any]]:
    """The planted obligations, normalised to a vector whichever shape was declared."""
    if shape == SINGLE:
        statement = raw["property"]
        if not isinstance(statement, str) or len(statement.strip()) < 20:
            raise ScenarioError("scenario property must be a substantive sentence")
        declared = _dimensions(raw)
        return [{"id": "primary", "statement": statement.strip(),
                 # A legacy scenario declares dimensions for the scenario, not per obligation;
                 # with exactly one obligation the two coincide only when there is one label.
                 "dimension": declared[0] if len(declared) == 1 else None,
                 "reachable_from": [_relative(x, "reachable_from entry")
                                    for x in raw.get("reachable_from", [])]}]

    values = raw["properties"]
    if not isinstance(values, list):
        raise ScenarioError("properties must be a list")
    if not MIN_PROPERTIES <= len(values) <= MAX_PROPERTIES:
        raise ScenarioError(f"a multi-property scenario carries {MIN_PROPERTIES}-{MAX_PROPERTIES} "
                            f"planted obligations; found {len(values)}")
    out: list[dict[str, Any]] = []
    for entry in values:
        if not isinstance(entry, dict):
            raise ScenarioError("each property must be an object")
        unknown = sorted(set(entry) - PROPERTY_FIELDS)
        if unknown:
            raise ScenarioError(f"unknown property field(s): {', '.join(unknown)}")
        missing = sorted({"id", "statement", "dimension"} - set(entry))
        if missing:
            raise ScenarioError(f"property is missing {', '.join(missing)}")
        pid = entry["id"]
        if not isinstance(pid, str) or not PROPERTY_ID.match(pid):
            raise ScenarioError(f"property id must be lowercase kebab-case: {pid!r}")
        statement = entry["statement"]
        if not isinstance(statement, str) or len(statement.strip()) < 20:
            raise ScenarioError(f"property {pid!r} statement must be a substantive sentence")
        if entry["dimension"] not in PROPERTY_DIMENSIONS:
            raise ScenarioError(f"property {pid!r} declares unknown dimension "
                                f"{entry['dimension']!r}")
        out.append({"id": pid, "statement": statement.strip(), "dimension": entry["dimension"],
                    "reachable_from": [_relative(x, "reachable_from entry")
                                       for x in entry.get("reachable_from", [])]})
    ids = [p["id"] for p in out]
    if len(set(ids)) != len(ids):
        raise ScenarioError("property ids must be unique within a scenario")
    return out


def _dimensions(raw: dict[str, Any]) -> list[str]:
    values = raw.get("dimensions", [])
    if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
        raise ScenarioError("dimensions must be a list of strings")
    unknown = sorted(set(values) - DIFFICULTY_DIMENSIONS)
    if unknown:
        raise ScenarioError(f"unknown difficulty dimension(s): {', '.join(unknown)}")
    if len(set(values)) != len(values):
        raise ScenarioError("dimensions must not repeat")
    return list(values)


def _distractors(raw: dict[str, Any]) -> list[str]:
    """Defensible concerns the artifact genuinely contains that are *not* the planted property.

    Evaluator-side, like the rubric: they never reach the system under test. They exist so a
    crowded scenario can state, in advance, what a report may legitimately raise while still
    having missed the breach — which is exactly the negative control such a scenario needs.
    """
    values = raw.get("distractors", [])
    if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
        raise ScenarioError("distractors must be a list of strings")
    for value in values:
        if len(value.strip()) < 20:
            raise ScenarioError(f"distractor must be a substantive description: {value!r}")
    return [v.strip() for v in values]


def _assert_declared_difficulty_is_real(scenario: dict[str, Any], contract_text: str) -> None:
    """Check the claims a scenario makes about its own difficulty, where checking is possible.

    A declared dimension that nothing verifies is a label, and a suite of labels would let
    difficulty be asserted rather than built. Two of the three dimensions have a mechanical
    consequence; the third is recorded as a human judgement and says so.
    """
    dimensions = scenario["dimensions"] if scenario["shape"] == SINGLE else []
    if DEPENDENCY_DISTANCE in dimensions:
        if not scenario["reachable_from"]:
            raise ScenarioError(f"scenario {scenario['id']} declares {DEPENDENCY_DISTANCE} "
                                "but lists no reachable_from material")
        # The point of the dimension: at least one artifact carrying the conflict must not be
        # handed to the worker by the contract. If every source is named there, the reflector
        # is comparing documents it was given and the pipeline is not on the causal path.
        unnamed = [rel for rel in scenario["reachable_from"] if rel not in contract_text]
        if not unnamed:
            raise ScenarioError(
                f"scenario {scenario['id']} declares {DEPENDENCY_DISTANCE} but the contract "
                "names every artifact the property depends on; nothing has to be discovered")
    if COMPETING_CONCERNS in dimensions and len(scenario["distractors"]) < 2:
        raise ScenarioError(f"scenario {scenario['id']} declares {COMPETING_CONCERNS} but "
                            "lists fewer than two competing defensible concerns")
    # INDIRECT_IMPLICATION has no mechanical test: "the conflict is not stated by any adjacent
    # sentence pair" is a reading, and inventing a proxy metric for it would measure the proxy.
    # It is a human judgement, recorded in the manifest and checked in review.
    if scenario["shape"] == MULTI:
        _assert_multi_property_shape(scenario, contract_text)
    for prop in scenario["properties"]:
        needles = _ngrams(prop["statement"])
        for distractor in scenario["distractors"]:
            flat = " ".join(re.findall(r"[a-z]{4,}", distractor.lower()))
            if any(needle in flat for needle in needles):
                raise ScenarioError(
                    f"scenario {scenario['id']} lists a distractor that restates planted "
                    f"property {prop['id']!r}; a negative control built from it would grade "
                    "as a detection")


def _assert_multi_property_shape(scenario: dict[str, Any], contract_text: str) -> None:
    """The mechanical half of E19.2-E19.3. The semantic half stays with human review.

    Python can check that a scenario is *shaped* like a crowded, multi-obligation review and
    that its obligations are not textual restatements of one another. It cannot decide whether
    two engineering obligations are genuinely independent, whether repairing one would repair
    the other, or whether a violation is objective — those are readings, and a proxy metric
    for them would measure the proxy. Scenario review owns them.
    """
    props = scenario["properties"]
    sid = scenario["id"]

    # Defensible rival concerns must at least match the number of breaches, or the artifact is
    # a list of planted mistakes rather than a review with something to prioritise.
    if len(scenario["distractors"]) < len(props):
        raise ScenarioError(
            f"scenario {sid} plants {len(props)} obligations but lists only "
            f"{len(scenario['distractors'])} competing concerns; a multi-property scenario "
            "needs at least as many defensible rival concerns as breaches")

    if len({p["dimension"] for p in props}) < 2:
        raise ScenarioError(
            f"scenario {sid} plants every obligation under one difficulty dimension; a "
            "multi-property scenario must exercise at least two reasoning structures")

    # At least one obligation must depend on material the contract does not hand over, or the
    # scenario collapses back to comparing documents the worker was given.
    discoverable = [p["id"] for p in props
                    if any(rel not in contract_text for rel in p["reachable_from"])]
    if not discoverable:
        raise ScenarioError(
            f"scenario {sid} names every artifact its obligations depend on in the contract; "
            "at least one obligation must require material the worker has to discover")

    # A textual restatement is the one form of dependence Python can catch. Genuine semantic
    # entailment is not decidable here and is a review question.
    for i, first in enumerate(props):
        needles = _ngrams(first["statement"])
        for second in props[i + 1:]:
            flat = " ".join(re.findall(r"[a-z]{4,}", second["statement"].lower()))
            if any(needle in flat for needle in needles):
                raise ScenarioError(
                    f"scenario {sid} properties {first['id']!r} and {second['id']!r} restate "
                    "each other; planted obligations must be separate, not one chain split up")


def identity(scenario: dict[str, Any]) -> str:
    """Content identity of the engineering problem.

    Covers the manifest fields that define the problem plus every fixture byte and the task
    contract. Ordered explicitly rather than relying on directory iteration, because
    ordering that affects an identity is protocol — the lesson M0 paid for.

    **Computed from the shape the manifest actually declared.** A single-property scenario
    hashes exactly the fields it always hashed, so every identity recorded by the first
    baseline and the calibration screening stays byte-for-byte what it was; changing the
    serialization for all scenarios would silently orphan that evidence. A multi-property
    scenario hashes its obligation set instead, because that set is what the scenario asks
    for and a scenario whose properties changed is a different measurement.

    Grader model and rubric stay outside identity in both shapes (E3): re-grading retained
    evidence is a new measurement of the same scenario.
    """
    fixture = Path(scenario["fixture"])
    shape = scenario.get("shape", SINGLE)
    h = hashlib.sha256()
    h.update(SCENARIO_FORMAT.encode("utf-8")); h.update(b"\0")
    if shape == SINGLE:
        fields = ("kind", "summary", "property", "artifact", "review_purpose")
    else:
        fields = ("kind", "summary", "artifact", "review_purpose")
    for field in fields:
        h.update(field.encode("utf-8")); h.update(b"\0")
        h.update(str(scenario[field]).encode("utf-8")); h.update(b"\0")
    if shape == MULTI:
        # Order is the manifest's order, not sorted: reordering the obligations is an authoring
        # change and should be visible as one rather than silently identical.
        h.update(b"properties\0")
        h.update(str(len(scenario["properties"])).encode("utf-8")); h.update(b"\0")
        for prop in scenario["properties"]:
            for key in ("id", "statement", "dimension"):
                h.update(key.encode("utf-8")); h.update(b"\0")
                h.update(str(prop[key]).encode("utf-8")); h.update(b"\0")
            h.update(b"reachable_from\0")
            for rel in prop["reachable_from"]:
                h.update(rel.encode("utf-8")); h.update(b"\0")
    h.update(b"contract\0")
    h.update(artifact_identity_file(Path(scenario["contract"])).encode("utf-8")); h.update(b"\0")
    for rel in sorted(scenario["files"]):
        h.update(rel.encode("utf-8")); h.update(b"\0")
        h.update(artifact_identity_file(fixture / rel).encode("utf-8")); h.update(b"\0")
    return h.hexdigest()


def _ngrams(text: str, n: int = 6) -> set[str]:
    words = re.findall(r"[a-z]{4,}", text.lower())
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)} if len(words) >= n else set()


def _assert_property_not_leaked(scenario: dict[str, Any]) -> None:
    """No planted obligation's answer may sit in the material the reflector receives.

    A crude but effective check: no long distinctive run of any property may appear verbatim
    in the fixture or contract. It cannot prove a scenario is subtle, but it does catch the
    obvious failure of pasting an answer into the inputs — and with several obligations there
    are several answers to leak, so every one is checked.
    """
    fixture = Path(scenario["fixture"])
    haystacks = [(rel, (fixture / rel).read_text(encoding="utf-8", errors="ignore").lower())
                 for rel in scenario["files"]]
    haystacks.append(("contract.md",
                      Path(scenario["contract"]).read_text(encoding="utf-8").lower()))
    if scenario.get("author_report"):
        # Worker-visible in the treated arm, so it is held to the same standard as the fixture:
        # it may restate engineering facts the reflector could already read, never the planted
        # conclusion, which would hand the treated arm the answer the control is measuring.
        haystacks.append((AUTHOR_REPORT,
                          Path(scenario["author_report"]).read_text(encoding="utf-8").lower()))
    flattened = [(name, " ".join(re.findall(r"[a-z]{4,}", text))) for name, text in haystacks]
    for prop in scenario["properties"]:
        for needle in _ngrams(prop["statement"]):
            for name, flat in flattened:
                if needle in flat:
                    raise ScenarioError(
                        f"scenario {scenario['id']} leaks planted property {prop['id']!r} into "
                        f"{name}: ...{needle}... — the system under test must not be handed "
                        "the answer")


def discover(root: Path) -> list[dict[str, Any]]:
    """Every scenario under `root`, ordered deterministically."""
    root = Path(root)
    return [load(d) for d in sorted(root.iterdir())
            if d.is_dir() and (d / "scenario.json").is_file()]

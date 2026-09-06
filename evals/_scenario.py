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

REQUIRED = frozenset({"format", "kind", "summary", "property", "artifact", "review_purpose"})
OPTIONAL = frozenset({"notes"})
KINDS = frozenset({"regression", "capability"})

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
    extra = sorted(set(raw) - REQUIRED - OPTIONAL)
    if extra:
        raise ScenarioError(f"unknown scenario field(s): {', '.join(extra)}")
    if raw["kind"] not in KINDS:
        raise ScenarioError(f"scenario kind must be one of {sorted(KINDS)}: {raw['kind']!r}")
    for field in ("summary", "property"):
        if not isinstance(raw[field], str) or len(raw[field].strip()) < 20:
            raise ScenarioError(f"scenario {field} must be a substantive sentence")

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

    scenario = {
        "id": directory.name,
        "path": str(directory),
        "format": raw["format"],
        "kind": raw["kind"],
        "summary": raw["summary"].strip(),
        "property": raw["property"].strip(),
        "artifact": artifact,
        "review_purpose": raw["review_purpose"],
        "contract": str(contract),
        "fixture": str(fixture),
        "files": [p.relative_to(fixture).as_posix() for p in files],
    }
    scenario["identity"] = identity(scenario)
    _assert_property_not_leaked(scenario)
    return scenario


def identity(scenario: dict[str, Any]) -> str:
    """Content identity of the engineering problem.

    Covers the manifest fields that define the problem plus every fixture byte and the task
    contract. Ordered explicitly rather than relying on directory iteration, because
    ordering that affects an identity is protocol — the lesson M0 paid for.
    """
    fixture = Path(scenario["fixture"])
    h = hashlib.sha256()
    h.update(SCENARIO_FORMAT.encode("utf-8")); h.update(b"\0")
    for field in ("kind", "summary", "property", "artifact", "review_purpose"):
        h.update(field.encode("utf-8")); h.update(b"\0")
        h.update(str(scenario[field]).encode("utf-8")); h.update(b"\0")
    h.update(b"contract\0")
    h.update(artifact_identity_file(Path(scenario["contract"])).encode("utf-8")); h.update(b"\0")
    for rel in sorted(scenario["files"]):
        h.update(rel.encode("utf-8")); h.update(b"\0")
        h.update(artifact_identity_file(fixture / rel).encode("utf-8")); h.update(b"\0")
    return h.hexdigest()


def _assert_property_not_leaked(scenario: dict[str, Any]) -> None:
    """The grader's answer must not be sitting in the material the reflector receives.

    A crude but effective check: no long distinctive run of the property may appear verbatim
    in the fixture or contract. It cannot prove a scenario is subtle, but it does catch the
    obvious failure of pasting the answer into the inputs.
    """
    words = re.findall(r"[a-z]{4,}", scenario["property"].lower())
    if len(words) < 6:
        return
    needles = {" ".join(words[i:i + 6]) for i in range(len(words) - 5)}
    fixture = Path(scenario["fixture"])
    haystacks = [(rel, (fixture / rel).read_text(encoding="utf-8", errors="ignore").lower())
                 for rel in scenario["files"]]
    haystacks.append(("contract.md",
                      Path(scenario["contract"]).read_text(encoding="utf-8").lower()))
    for name, text in haystacks:
        flat = " ".join(re.findall(r"[a-z]{4,}", text))
        for needle in needles:
            if needle in flat:
                raise ScenarioError(
                    f"scenario {scenario['id']} leaks its planted property into {name}: "
                    f"...{needle}... — the system under test must not be handed the answer")


def discover(root: Path) -> list[dict[str, Any]]:
    """Every scenario under `root`, ordered deterministically."""
    root = Path(root)
    return [load(d) for d in sorted(root.iterdir())
            if d.is_dir() and (d / "scenario.json").is_file()]

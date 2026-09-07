#!/usr/bin/env python3
"""Compare two evaluation runs without inventing a ranking.

A comparison is **derived, never stored**. Two ordinary run summaries already hold every
fact; a persisted comparison record would duplicate them and then disagree with them. There
is no comparison id, no leaderboard and no winner: applying the state test, nothing here
cannot be recomputed from the two summaries it names.

**What changed comes before what scored.** A reader can only interpret a difference in
detection as a difference in models if nothing else moved, so the configuration diff is
computed first and a comparison in which several material fields differ says so rather than
presenting itself as a controlled result.

**Scenario population is matched by identity, not by name.** Two runs whose scenario sets
differ are not a ranking of two systems; they are two measurements of different things. The
shared population is reported explicitly and anything outside it is named.

**Ranking is a human call.** Comparison reports counts, per scenario and stratified by kind,
and stops. At the trial counts calibration uses, a one-trial gap is not an ordering, and code
that turned it into one would manufacture confidence that the evidence does not contain.
"""
from __future__ import annotations

import hashlib
from typing import Any

# The system-under-test fields whose equality decides whether a comparison isolates anything.
# Each answers: could a difference here change the outcome and thereby confound the reading?
COMPARISON_FIELDS = ("proofbound_sha", "harness", "harness_version",
                     "model", "grader_model", "role", "python")

# Provider is not a stored field: an OpenCode model identifier is `provider/model`, so it is
# derivable from something already recorded, and the state test says derive it. It matters
# because a comparison that also crosses providers is not a model-only comparison (E16.7).

# Counts carried per scenario, in the vocabulary the summary already uses.
COUNTS = ("attempted", "valid", "setup_failures", "harness_failures", "mechanical_ok",
          "semantic_detected", "semantic_not_detected", "grading_unavailable")


class ComparisonError(ValueError):
    """Two runs cannot be compared in a way that would mean anything."""


def configuration_diff(a: dict[str, Any], b: dict[str, Any]) -> list[dict[str, Any]]:
    """Every comparison-relevant field, marked same or different.

    Absent is a value, and it is *unknown* rather than a match: two runs that both omit
    `harness_version` are not thereby known to have used the same harness release.
    """
    sys_a, sys_b = a.get("system") or {}, b.get("system") or {}
    rows = []
    for field in COMPARISON_FIELDS:
        left, right = sys_a.get(field), sys_b.get(field)
        known = left is not None and right is not None
        # Recorded by neither run is not a difference — there is nothing to disagree about —
        # but it is not agreement either, and `unverified` is how a reader is told which.
        rows.append({"field": field, "a": left, "b": right,
                     "same": known and left == right, "known": known,
                     "unverified": left is None and right is None})
    return rows


def _provider(model: Any) -> str | None:
    """The provider half of a `provider/model` identifier, when there is one."""
    return model.split("/", 1)[0] if isinstance(model, str) and "/" in model else None


def _treatment(summary: dict[str, Any]) -> str | None:
    """One descriptor for what a whole run supplied to its reflectors.

    Derived rather than stored, like `provider`: the durable fact is each scenario's own
    author-report hash, and a run-level copy would be a second place for it to live. `None`
    means the record predates the experiment — not that it ran untreated.
    """
    values = [s.get("author_report_sha256") for s in summary.get("scenarios", [])]
    if not values or any(v is None for v in values):
        return None
    if all(v == "none" for v in values):
        return "none"
    h = hashlib.sha256()
    for scenario, value in sorted(zip((s["id"] for s in summary["scenarios"]), values)):
        h.update(scenario.encode("utf-8")); h.update(b"\0")
        h.update(str(value).encode("utf-8")); h.update(b"\0")
    return "author-report:" + h.hexdigest()[:16]


def _by_identity(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["identity"]: s for s in summary.get("scenarios", [])}


def compare(a: dict[str, Any], b: dict[str, Any], *,
            label_a: str = "A", label_b: str = "B") -> dict[str, Any]:
    """Build the derived comparison of two run summaries."""
    left, right = _by_identity(a), _by_identity(b)
    shared = sorted(set(left) & set(right), key=lambda i: left[i]["id"])
    if not shared:
        raise ComparisonError("the two runs share no scenario identity; there is nothing "
                              "to compare")

    diff = configuration_diff(a, b)
    # A field neither run recorded cannot count as a difference; it is reported as unverified.
    differing = [row["field"] for row in diff if not row["same"] and not row["unverified"]]
    unverified = [row["field"] for row in diff if row["unverified"]]
    sys_a, sys_b = a.get("system") or {}, b.get("system") or {}
    provider_a, provider_b = _provider(sys_a.get("model")), _provider(sys_b.get("model"))
    treatment_a, treatment_b = _treatment(a), _treatment(b)
    if treatment_a is not None or treatment_b is not None:
        known = treatment_a is not None and treatment_b is not None
        diff.append({"field": "treatment", "a": treatment_a, "b": treatment_b,
                     "same": known and treatment_a == treatment_b, "known": known,
                     # A run that recorded no treatment and one that recorded `"none"` are not
                     # the same fact, so this is a difference rather than an unverified match.
                     "unverified": False})
        if not (known and treatment_a == treatment_b):
            differing.append("treatment")
    populations_match = set(left) == set(right)
    # "Controlled" is a narrow claim: exactly one field moved and both runs saw the same
    # scenarios. Anything else is still evidence, but it is not a single-variable comparison.
    # Controlled means exactly one comparison-relevant field moved — whichever field that is.
    # Hardcoding the model would have made a treatment-only comparison look uncontrolled, which
    # is precisely the experiment this substrate now has to support.
    controlled = populations_match and len(differing) == 1

    scenarios = []
    for ident in shared:
        sa, sb = left[ident], right[ident]
        # Per obligation, in the manifest's order, keyed by the scenario-local id both runs
        # recorded. A property present in only one run is a population mismatch, not a score.
        pa, pb = sa.get("properties") or {}, sb.get("properties") or {}
        properties = [{"id": pid, "dimension": (pa[pid] or {}).get("dimension"),
                       "a": pa[pid], "b": pb.get(pid)}
                      for pid in pa if pid in pb]
        scenarios.append({
            "id": sa["id"], "identity": ident, "kind": sa.get("kind"),
            "a": {k: sa["counts"].get(k, 0) for k in COUNTS},
            "b": {k: sb["counts"].get(k, 0) for k in COUNTS},
            "properties": properties,
            "resources": {"a": sa.get("resources", {}), "b": sb.get("resources", {})},
        })

    # Stratified rather than pooled: easy regression anchors would otherwise dominate a
    # headline number and hide the capability scenarios that carry the actual signal.
    strata: dict[str, dict[str, dict[str, int]]] = {}
    for entry in scenarios:
        bucket = strata.setdefault(entry["kind"] or "unlabelled",
                                   {"a": dict.fromkeys(COUNTS, 0), "b": dict.fromkeys(COUNTS, 0)})
        for side in ("a", "b"):
            for key in COUNTS:
                bucket[side][key] += entry[side][key]

    return {"labels": {"a": label_a, "b": label_b},
            "configuration": diff, "differing_fields": differing,
            "unverified_fields": unverified,
            "provider": {"a": provider_a, "b": provider_b,
                         "same": provider_a is not None and provider_a == provider_b},
            "populations_match": populations_match, "controlled": controlled,
            "only_in_a": sorted(left[i]["id"] for i in set(left) - set(right)),
            "only_in_b": sorted(right[i]["id"] for i in set(right) - set(left)),
            "scenarios": scenarios, "strata": strata}


def render(comparison: dict[str, Any]) -> str:
    la, lb = comparison["labels"]["a"], comparison["labels"]["b"]
    out = ["Evaluation comparison — derived, not a stored record", "",
           "  what changed"]
    for row in comparison["configuration"]:
        if row["unverified"]:
            out.append(f"    {row['field']:<16} {'unrecorded':<10} neither run recorded it")
        elif row["same"]:
            out.append(f"    {row['field']:<16} {'same':<10} {row['a']}")
        else:
            out.append(f"    {row['field']:<16} {'differs':<10} {row['a']} -> {row['b']}")
    provider = comparison["provider"]
    if not provider["same"]:
        out.append(f"    {'provider':<16} {'differs':<10} {provider['a']} -> {provider['b']}"
                   "   (derived from the model identifier)")
    out.append("")
    if comparison["controlled"]:
        varied = comparison["differing_fields"][0]
        out.append(f"  only `{varied}` differs and both runs saw the same scenarios:")
        out.append(f"  readable as a controlled {varied} comparison under this configuration.")
        if not comparison["provider"]["same"]:
            out.append("  the provider changed with it, so model capability and provider "
                       "behaviour are not separable here.")
    else:
        reasons = []
        if not comparison["populations_match"]:
            reasons.append("the runs did not evaluate the same scenario set")
        if len(comparison["differing_fields"]) > 1:
            reasons.append("more than one field differs: "
                           + ", ".join(comparison["differing_fields"]))
        if not comparison["differing_fields"]:
            reasons.append("nothing material differs, so this compares a run with itself")
        out.append("  NOT a controlled comparison — " + "; ".join(reasons) + ".")
        if comparison["only_in_a"] or comparison["only_in_b"]:
            out.append(f"    only in {la}: {', '.join(comparison['only_in_a']) or '-'}")
            out.append(f"    only in {lb}: {', '.join(comparison['only_in_b']) or '-'}")
    if comparison["unverified_fields"]:
        out.append("  unverified (recorded by neither run, so equality is assumed and not "
                   "shown): " + ", ".join(comparison["unverified_fields"]))
    out += ["", f"  complete trials / valid (attempted)   {la:>14}  {lb:>14}"]
    for entry in comparison["scenarios"]:
        a, b = entry["a"], entry["b"]
        out.append(f"    {entry['id']:<34} "
                   f"{a['semantic_detected']:>3}/{a['valid']:<3}({a['attempted']:>2})  "
                   f"{b['semantic_detected']:>3}/{b['valid']:<3}({b['attempted']:>2})   "
                   f"[{entry['kind']}]")
        # The breakdown is the finding; a scenario total can hide which obligation is weak.
        for prop in entry["properties"]:
            pa, pb2 = prop["a"], prop["b"]
            out.append(f"      {prop['id']:<32} "
                       f"{pa['detected']:>3}/{pa['gradeable']:<3}     "
                       f"{pb2['detected']:>3}/{pb2['gradeable']:<3}      "
                       f"[{prop['dimension']}]")
    out.append("")
    for kind in sorted(comparison["strata"]):
        a, b = comparison["strata"][kind]["a"], comparison["strata"][kind]["b"]
        out.append(f"    {kind:<34} "
                   f"{a['semantic_detected']:>3}/{a['valid']:<3}({a['attempted']:>2})  "
                   f"{b['semantic_detected']:>3}/{b['valid']:<3}({b['attempted']:>2})   stratum")
    invalid, views = [], []
    for side, label in (("a", la), ("b", lb)):
        totals = {k: sum(s[side][k] for s in comparison["scenarios"]) for k in COUNTS}
        invalid.append(f"    {label}: setup-fail {totals['setup_failures']}"
                       f"  harness-fail {totals['harness_failures']}"
                       f"  ungraded {totals['grading_unavailable']}"
                       f"  mechanical {totals['mechanical_ok']}/{totals['valid']}")
        det = sum(p[side]["detected"] for s in comparison["scenarios"] for p in s["properties"])
        grd = sum(p[side]["gradeable"] for s in comparison["scenarios"] for p in s["properties"])
        # Two questions, two denominators. End-to-end asks whether the configuration operated
        # the role at all; conditional asks how complete it was when it did. Reporting only the
        # second would let a configuration that barely ran look excellent.
        # A run recorded before per-property counts existed has no obligations to show; that
        # is absent, not zero detections.
        obligations = f"{det}/{grd}" if grd else "not recorded"
        views.append(f"    {label}: end-to-end complete {totals['semantic_detected']}"
                     f"/{totals['attempted']} attempted"
                     f"   |   conditional complete {totals['semantic_detected']}"
                     f"/{totals['valid']} valid"
                     f"   obligations {obligations}")
    out += ["", "  validity and mechanics", *invalid,
            "", "  end-to-end role effectiveness vs conditional semantic completeness", *views]
    out += ["", "  resources (separate from semantic outcome, never combined with it)"]
    for entry in comparison["scenarios"]:
        ra, rb = entry["resources"]["a"], entry["resources"]["b"]
        out.append(f"    {entry['id']:<34} "
                   f"{str(ra.get('median_elapsed_seconds')):>14}s "
                   f"{str(rb.get('median_elapsed_seconds')):>14}s   median")
    out += ["", "  No ordering is computed. These are observed counts on this scenario "
                "population",
            "  under this configuration; whether they establish an ordering is a human "
            "judgement."]
    return "\n".join(out)

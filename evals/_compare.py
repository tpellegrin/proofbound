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


def _row(field: str, left: Any, right: Any) -> dict[str, Any]:
    """One field on both sides. Unknown on either side is `unverified`: neither agreement nor
    difference. Treating a one-sided absence as a difference turned *unavailable* into *mismatch*;
    treating a two-sided absence as agreement let an unrecorded control certify a comparison."""
    known = left is not None and right is not None
    return {"field": field, "a": left, "b": right, "same": known and left == right,
            "known": known, "unverified": not known,
            "recorded_by": ("both" if known else "a" if left is not None else
                            "b" if right is not None else "neither")}


def configuration_diff(a: dict[str, Any], b: dict[str, Any]) -> list[dict[str, Any]]:
    """Every comparison-relevant field, marked same, different or unverified.

    Absent is a value, and it is *unknown* rather than a match: two runs that both omit
    `harness_version` are not thereby known to have used the same harness release.
    """
    sys_a, sys_b = a.get("system") or {}, b.get("system") or {}
    return [_row(field, sys_a.get(field), sys_b.get(field)) for field in COMPARISON_FIELDS]


def eligibility(rows: list[dict[str, Any]], *, populations_match: bool) -> dict[str, Any]:
    """Whether a comparison may be read as controlled, and every reason it may not.

    **An unknown material control never establishes a controlled effect** (E17.3). Every field in
    `rows` is a required control; a comparison is controlled only when the populations match,
    exactly one field is *known* to differ, and no field is unverified. Anything else remains
    descriptive evidence and says why.
    """
    differing = [r["field"] for r in rows if r["known"] and not r["same"]]
    unverified = [r["field"] for r in rows if r["unverified"]]
    reasons = []
    if not populations_match:
        reasons.append("the runs did not evaluate the same scenario set")
    if len(differing) > 1:
        reasons.append("more than one field differs: " + ", ".join(differing))
    if not differing:
        reasons.append("no field is known to differ, so this compares a run with itself or "
                       "with an unknown")
    if unverified:
        named = []
        for r in rows:
            if r["unverified"]:
                who = ("recorded by neither" if r["recorded_by"] == "neither"
                       else f"recorded by {r['recorded_by']} only")
                named.append(f"{r['field']} ({who})")
        reasons.append("required control(s) not recorded by both runs, so their equality is "
                       "unknown: " + ", ".join(named))
    return {"differing": differing, "unverified": unverified, "reasons": reasons,
            "controlled": populations_match and len(differing) == 1 and not unverified}


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
    sys_a, sys_b = a.get("system") or {}, b.get("system") or {}
    provider_a, provider_b = _provider(sys_a.get("model")), _provider(sys_b.get("model"))
    # The treatment is a required control like any other. A record that predates the P12 field
    # and one that recorded `"none"` are not the same fact — and not a known difference either.
    diff.append(_row("treatment", _treatment(a), _treatment(b)))
    populations_match = set(left) == set(right)
    # "Controlled" is a narrow claim: exactly one field is known to have moved, nothing required
    # is unrecorded, and both runs saw the same scenarios. Whichever field moved — hardcoding the
    # model would have made a treatment-only comparison look uncontrolled.
    verdict = eligibility(diff, populations_match=populations_match)
    differing, unverified, controlled = (verdict["differing"], verdict["unverified"],
                                         verdict["controlled"])

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
            "not_controlled_because": verdict["reasons"] if not controlled else [],
            "only_in_a": sorted(left[i]["id"] for i in set(left) - set(right)),
            "only_in_b": sorted(right[i]["id"] for i in set(right) - set(left)),
            "scenarios": scenarios, "strata": strata}


def render(comparison: dict[str, Any]) -> str:
    la, lb = comparison["labels"]["a"], comparison["labels"]["b"]
    out = ["Evaluation comparison — derived, not a stored record", "",
           "  what changed"]
    for row in comparison["configuration"]:
        if row["unverified"]:
            who = ("neither run recorded it" if row.get("recorded_by", "neither") == "neither"
                   else f"only {row['recorded_by']} recorded it ({row['a']} -> {row['b']})")
            out.append(f"    {row['field']:<16} {'unverified':<10} {who}; equality unknown")
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
        out.append(f"  only `{varied}` differs, every required control is recorded by both runs, "
                   "and both saw the same scenarios:")
        out.append(f"  readable as a controlled {varied} comparison under this configuration.")
        if not comparison["provider"]["same"]:
            out.append("  the provider changed with it, so model capability and provider "
                       "behaviour are not separable here.")
    else:
        out.append("  NOT a controlled comparison — "
                   + "; ".join(comparison["not_controlled_because"]) + ".")
        out.append("  The counts below remain descriptive evidence of what each run observed; "
                   "no difference in them is attributable to one field.")
        if comparison["only_in_a"] or comparison["only_in_b"]:
            out.append(f"    only in {la}: {', '.join(comparison['only_in_a']) or '-'}")
            out.append(f"    only in {lb}: {', '.join(comparison['only_in_b']) or '-'}")
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


# -- configuration qualification results ---------------------------------------------------------
#
# The same rule, applied to what `evals/_qualify.py` records. The difference is what may vary: a
# qualification comparison answers a *question*, and a declared question may vary a bundle of
# fields — which is reported as a bundle and never attributed to one of its members.

#: Configuration fields grouped by the question that varies them. Every field is a required
#: control for every question that does not vary its group.
QUALIFICATION_GROUPS = {
    "worker": ("worker.profile_kind", "worker.provider", "worker.endpoint", "worker.model",
               "worker.variant", "worker.limits", "worker.network"),
    "executor": ("executor",),
    "coordinator": ("coordinator",),
    "harness": ("control_plane", "interpreter"),
    "tasks": ("suite",),
    "resources": ("resources",),
    "measurement": ("mode",),
}

QUESTIONS = {
    frozenset({"worker"}): "worker-profile comparison: coordinator, tasks, verifier and every "
                           "other recorded control held fixed",
    frozenset({"coordinator"}): "coordinator comparison: worker path and tasks held fixed",
    frozenset({"harness"}): "harness-treatment comparison: baseline and candidate control planes "
                            "under one declared configuration",
    frozenset({"executor"}): "executor comparison: reported as the executor bundle",
    frozenset({"executor", "worker"}): "agent-system comparison: executor and worker changed "
                                       "together, reported as one bundle",
}


def _trial_key(trial: dict[str, Any]) -> tuple[Any, ...]:
    """Tasks are matched by immutable case identity, never by name."""
    return (trial.get("case_identity"), trial.get("subject"), trial.get("variant"))


def _headline(trial: dict[str, Any]) -> str:
    """The one outcome word a trial's grade carries, without folding dimensions together."""
    if trial.get("status") != "completed":
        return str(trial.get("status"))
    o = trial.get("outcome") or {}
    for key in ("outcome", "review", "delivered_verdict"):
        if isinstance(o.get(key), str):
            return o[key]
    return "ungraded"


def compare_qualification(a: dict[str, Any], b: dict[str, Any], *,
                          label_a: str = "A", label_b: str = "B") -> dict[str, Any]:
    """What two qualification results can support, derived and never stored.

    Order of the report is the order of the argument: what question this is, which controls are
    unverified, which population differs, which trials are missing or duplicated — and only then
    what each side observed.
    """
    conf_a, conf_b = a.get("configuration") or {}, b.get("configuration") or {}
    rows = [_row(f, conf_a.get(f), conf_b.get(f))
            for group in QUALIFICATION_GROUPS.values() for f in group]
    by_field = {r["field"]: r for r in rows}
    varied = sorted(g for g, fields in QUALIFICATION_GROUPS.items()
                    if any(by_field[f]["known"] and not by_field[f]["same"] for f in fields))
    unverified = [r["field"] for r in rows if r["unverified"]]
    bundle = [r["field"] for r in rows if r["known"] and not r["same"]]

    def index(result: dict[str, Any]) -> tuple[dict[Any, dict[str, Any]], list[str]]:
        seen: dict[Any, dict[str, Any]] = {}
        duplicates = []
        for trial in result.get("trials") or []:
            key = _trial_key(trial)
            if key in seen:
                duplicates.append(trial.get("trial_id"))
            else:
                seen[key] = trial
        return seen, duplicates

    left, dup_a = index(a)
    right, dup_b = index(b)
    if not set(left) & set(right):
        raise ComparisonError("the two results share no trial of the same case identity; "
                              "there is nothing to compare")
    same_run = a.get("plan_digest") == b.get("plan_digest") and \
        a.get("started_at") == b.get("started_at")
    reasons = []
    question = QUESTIONS.get(frozenset(set(varied) - {"tasks"}))
    if "measurement" in varied:
        question = None
        reasons.append("the two results were measured differently (replay stand-in and live, "
                       "or different stand-ins); they are not measurements of one question")
    elif not set(varied) - {"tasks"}:
        question = ("the same record twice: nothing is gained by comparing it with itself"
                    if same_run else "replication: distinct trials of one configuration — "
                                     "repetitions, not an effect")
    elif question is None:
        question = ("configuration-bundle comparison across " + ", ".join(varied)
                    + "; the difference belongs to the bundle, not to any one field")
    if "tasks" in varied:
        reasons.append("the suites differ; only trials of the same case identity are paired")
    if set(left) != set(right):
        reasons.append("the trial populations differ; unpaired trials are listed, never scored")
    if unverified:
        reasons.append("required control(s) unrecorded on at least one side: "
                       + ", ".join(unverified))
    if dup_a or dup_b:
        reasons.append("duplicate trials were excluded from pairing: "
                       + ", ".join(dup_a + dup_b))
    controlled = not reasons and bool(set(varied) - {"tasks"})

    paired, unpairable = [], []
    for key in sorted(set(left) & set(right), key=lambda k: str(k)):
        ta, tb = left[key], right[key]
        if ta.get("transport") != tb.get("transport"):
            # A stand-in and a real executor, or two different stand-ins, measured different
            # things for this cell: shown, never set side by side as one question.
            unpairable.append({"trial_id": ta.get("trial_id"), "a": ta.get("transport"),
                               "b": tb.get("transport")})
            continue
        paired.append({"case": ta.get("case"), "subject": ta.get("subject"),
                       "variant": ta.get("variant"),
                       "a": _dimensions(ta), "b": _dimensions(tb)})
    if unpairable:
        reasons.append("some cells were measured by different transports and are not paired: "
                       + ", ".join(str(u["trial_id"]) for u in unpairable))
        controlled = False
    return {
        "labels": {"a": label_a, "b": label_b},
        "question": question, "controlled": controlled, "not_controlled_because": reasons,
        "varied_groups": varied, "varied_bundle": bundle,
        "attributable_to_one_field": controlled and len(bundle) == 1,
        "configuration": rows, "unverified_fields": unverified,
        "denominators": {"a": a.get("denominators"), "b": b.get("denominators")},
        "only_in_a": sorted(str(left[k].get("trial_id")) for k in set(left) - set(right)),
        "only_in_b": sorted(str(right[k].get("trial_id")) for k in set(right) - set(left)),
        "duplicates": {"a": dup_a, "b": dup_b},
        "paired": paired, "unpairable": unpairable,
        "modes": {"a": conf_a.get("mode"), "b": conf_b.get("mode")},
        "claims": {"a": a.get("claim"), "b": b.get("claim")},
        "tokens_comparable": not ({"worker.provider", "worker.model", "executor"} & set(bundle)),
    }


def _dimensions(trial: dict[str, Any]) -> dict[str, Any]:
    """Each dimension a trial reports, side by side and never combined."""
    o = trial.get("outcome") or {}
    usage = o.get("usage") or {}
    return {
        "status": trial.get("status"), "headline": _headline(trial),
        "first_attempt": o.get("first_attempt"), "after_repair": o.get("after_bounded_repair"),
        "false_acceptance": o.get("false_acceptance",
                                  o.get("decision_outcome") == "false-acceptance" or None),
        "false_refusal": (o.get("decision_outcome") == "false-refusal"
                          or o.get("outcome") == "false-refusal") or None,
        "findings": {k: (o.get("findings") or o.get("review") or {}).get(k)
                     for k in ("reported", "correct", "substantiated",
                               "correct_but_unsubstantiated", "false")}
        if isinstance(o.get("findings") or o.get("review"), dict) else None,
        "repairs": o.get("repairs"),
        "elapsed_seconds": trial.get("elapsed_seconds"),
        "tokens": (usage.get("tokens") or {}) and {k: usage["tokens"].get(k) for k in
                                                     ("input", "output", "reasoning",
                                                      "cache_read")},
        "usage_complete": usage.get("complete"),
        "derived_cost": usage.get("derived_cost"), "billing": usage.get("billing"),
    }


def render_qualification(comparison: dict[str, Any]) -> str:
    la, lb = comparison["labels"]["a"], comparison["labels"]["b"]
    out = ["Qualification comparison — derived, not a stored record", "",
           f"  question     {comparison['question'] or 'none this comparison can answer'}",
           f"  controlled   {'yes' if comparison['controlled'] else 'NO'}"]
    for reason in comparison["not_controlled_because"]:
        out.append(f"    - {reason}")
    if comparison["varied_bundle"]:
        out.append("  varied       " + ", ".join(comparison["varied_bundle"])
                   + ("" if comparison["attributable_to_one_field"] else
                      "   (a bundle: not attributable to any one field)"))
    out += ["", "  configuration"]
    for row in comparison["configuration"]:
        state = ("same" if row["same"] else "unverified" if row["unverified"] else "differs")
        value = row["a"] if row["same"] else f"{row['a']} -> {row['b']}"
        out.append(f"    {row['field']:<22} {state:<10} {value}")
    out += ["", "  denominators (planned / attempted / completed / gradeable)"]
    for side, label in (("a", la), ("b", lb)):
        d = comparison["denominators"][side] or {}
        out.append(f"    {label}: {d.get('planned')} / {d.get('attempted')} / "
                   f"{d.get('completed')} / {d.get('gradeable')}; excluded "
                   f"{[e.get('trial_id') for e in d.get('excluded') or []]}")
    if comparison["only_in_a"] or comparison["only_in_b"]:
        out.append(f"    unpaired — only in {la}: {comparison['only_in_a'] or '-'}; "
                   f"only in {lb}: {comparison['only_in_b'] or '-'}")
    out += ["", "  per trial, each dimension apart (a | b)"]
    for row in comparison["paired"]:
        name = "/".join(x for x in (row["case"], row["subject"], row["variant"]) if x)
        a, b = row["a"], row["b"]
        out.append(f"    {name}")
        for key in ("headline", "first_attempt", "after_repair", "false_acceptance",
                    "false_refusal", "findings", "repairs", "elapsed_seconds", "tokens",
                    "usage_complete", "derived_cost"):
            if a.get(key) is None and b.get(key) is None:
                continue
            out.append(f"      {key:<17} {a.get(key)} | {b.get(key)}")
    if comparison["modes"]["a"] == comparison["modes"]["b"] == "replay":
        out.append("")
        out.append("  both results are replays: stand-ins did the work, so matching outcomes are "
                   "expected by construction and say nothing about either model.")
    if not comparison["tokens_comparable"]:
        out.append("")
        out.append("  token counts cross providers, models or executors: tokenizers and cache "
                   "conventions differ, so the counts are not directly comparable.")
    out += ["", "  claims recorded with each result:",
            f"    {la}: {comparison['claims']['a']}", f"    {lb}: {comparison['claims']['b']}",
            "", "  No ordering is computed, and nothing here selects a configuration. One trial per",
            "  cell is an observation; a repeated comparison needs a declared margin, pairing and",
            "  its own uncertainty."]
    return "\n".join(out)

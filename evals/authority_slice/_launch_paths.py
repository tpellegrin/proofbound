#!/usr/bin/env python3
"""Enumerate the paid launches an experiment can reach, so its ceiling is derived rather than set.

`pb-authority-demo-2` froze a launch ceiling of 8 written as `5 clean + 3 repair`, then discovered
mid-run that the same document granted a survivable deadline expiry nobody had added to the sum.
The ceiling was raised to 9 by the party it benefited — a defensible reading and still a departure
([audit](../../docs/architecture/proofbound/evidence/authority-workflow-demo-2-audit.md)).

The repair is arithmetic, not policy: declare the transitions, enumerate every path, and take the
maximum. A path the experiment intends to allow but forgot to count then shows up before the run
rather than during it. This is a dozen lines of graph walking on purpose — a workflow language
would be a second thing to validate.
"""
from __future__ import annotations

from typing import Any

#: `state -> [(next state, paid launches, why)]`. A terminal state has no successors.
#: `budget_relaunch` is the once-per-run allowance for a launch that never reached the executor.
TRANSITIONS: "dict[str, list[tuple[str, int, str]]]" = {
    "recovered": [("authorized", 0, "the guard admits; no provider call"),
                  ("stopped-refused", 0, "the guard refuses, which is an answer")],
    "authorized": [("implemented", 1, "implementer attempt")],
    "implemented": [("reviewed", 1, "fresh independent review")],
    "reviewed": [("accepted", 0, "no task-relevant defect; the coordinator accepts"),
                 ("repaired", 1, "a genuine finding; the producer repairs under the same "
                                 "immutable contract")],
    "repaired": [("re-reviewed", 1, "the repair must be re-earned by a fresh review")],
    "re-reviewed": [("accepted", 0, "accepted against the fresh review"),
                    ("stopped-allowance-spent", 0, "a further finding, with the one repair "
                                                   "already spent")],
    "accepted": [],
    "stopped-refused": [],
    "stopped-allowance-spent": [],
    #: Not a transition: a deadline expiry that leaves a model call in flight makes the spend
    #: figure incomplete, and an incomplete figure refuses every further launch. It ends the run
    #: unless an enforced per-call limit makes the unfinished call boundable. Counted as terminal
    #: so the ceiling never silently assumes it is survivable.
}

TERMINAL_BY_INCOMPLETE_SPEND = (
    "a deadline expiry with a model call still in flight ends the run: with no enforced per-call "
    "limit the cost of that call is unknown, the figure is incomplete, and stop condition 1 "
    "refuses further launches")

MECHANICAL_RELAUNCH_ALLOWANCE = 1


def paths(start: str = "recovered") -> "list[dict[str, Any]]":
    """Every path from `start` to a terminal state, with the launches it spends."""
    out: "list[dict[str, Any]]" = []

    def walk(state: str, spent: int, trail: "list[str]") -> None:
        successors = TRANSITIONS.get(state, [])
        if not successors:
            out.append({"path": [*trail, state], "launches": spent})
            return
        for nxt, cost, _why in successors:
            if nxt in trail:                       # the table is acyclic; this guards a typo
                raise ValueError(f"cycle through {nxt}")
            walk(nxt, spent + cost, [*trail, state])

    walk(start, 0, [])
    return out


def ceiling() -> "dict[str, Any]":
    """The maximum paid launches any allowed path can reach, plus the relaunch allowance."""
    enumerated = paths()
    worst = max(enumerated, key=lambda p: p["launches"])
    return {
        "paths": len(enumerated),
        "max_launches_on_a_path": worst["launches"],
        "worst_path": worst["path"],
        "mechanical_relaunch_allowance": MECHANICAL_RELAUNCH_ALLOWANCE,
        "ceiling": worst["launches"] + MECHANICAL_RELAUNCH_ALLOWANCE,
        "terminal_not_survivable": TERMINAL_BY_INCOMPLETE_SPEND,
        "enumerated": sorted(enumerated, key=lambda p: (-p["launches"], p["path"])),
    }

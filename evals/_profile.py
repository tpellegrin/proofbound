#!/usr/bin/env python3
"""What one agent execution cost, described without knowing what the experiment is about.

MLR-C3 measured a pipeline and found the measurement was the fragile part. This module is the half
of that measurement which is not about object storage, module boundaries or contract substitution:
model calls, tokens, tool activity, time and stages. It could describe a reviewer run or a spec
reflection without changing a line, and it deliberately knows nothing that would let it.

**Layering.** `_profile` answers *what did this execution do*. `_mlr_context` answers *where did the
representation come from*, which is experiment-specific and stays there. Keeping them apart is what
makes the first reusable and stops the second from quietly becoming an ontology.

**Source.** OpenCode records a session in the SQLite database `run_worker.py` points `OPENCODE_DB`
at: `step-start` marks a model call beginning, `step-finish` carries that call's provider-counted
usage, and `tool` parts carry the invoked tool, its arguments, its output, its status and a
start/end timestamp. Everything here is read from those rows; nothing is estimated.

**Stages.** A Proofbound pipeline is a sequence of roles — spec author, reflector, implementer,
reviewer. This module carries a stage per execution and aggregates across stages, so a pipeline of
several roles needs more rows rather than a new design. The MLR experiment currently runs one
implementer, and one stage is a degenerate case of the shape, not a different shape.

**No score.** There is no combination of tokens, time and correctness into a single number here, and
there should not be one anywhere: nothing in Proofbound has the authority to exchange quality for
cost. Resource figures are reported beside an outcome, never traded against it.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

# What a metric means when the executor did not record it. An absent measurement is not zero, and a
# run whose interpretation depends on a missing metric is invalid rather than cheap.
MISSING = None


def read_parts(db: Path) -> list[dict[str, Any]]:
    """Every recorded part of one session, ordered as OpenCode replays it.

    Opened read-only by URI so measuring a session never modifies it.
    """
    path = Path(db)
    if not path.is_file():
        return []
    uri = f"file:{path.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        rows = conn.execute(
            "SELECT p.id, p.message_id, p.data, m.data, m.time_created "
            "FROM part p JOIN message m ON m.id = p.message_id "
            "ORDER BY m.time_created, p.message_id, p.id").fetchall()
    events: list[dict[str, Any]] = []
    for ordinal, (part_id, message_id, part_raw, message_raw, created) in enumerate(rows):
        try:
            part = json.loads(part_raw)
            message = json.loads(message_raw)
        except (json.JSONDecodeError, TypeError):
            continue
        events.append({"ordinal": ordinal, "part_id": part_id, "message_id": message_id,
                       "time_created": created, "role": message.get("role"),
                       "summary": bool(message.get("summary")),
                       "model": message.get("modelID") or message.get("model"),
                       "provider": message.get("providerID"),
                       "part": part, "message": message})
    return events


def model_call_starts(events: list[dict[str, Any]]) -> list[int]:
    """Ordinals at which a model call began.

    `step-start` rather than `step-finish`: a call that failed still received its input, and what
    later context accounting needs is which calls existed after a representation appeared.
    """
    return [e["ordinal"] for e in events if e["part"].get("type") == "step-start"]


def usage(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Provider-counted usage, summed over completed calls.

    Raw usage is retained rather than money. Prices change, and a later price change must not be
    able to reinterpret what a historical run actually consumed; cost is derived from these numbers
    plus a price identity, never stored in their place.
    """
    totals = {"calls_started": len(model_call_starts(events)), "calls_finished": 0,
              "input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0,
              "cost": 0.0}
    for event in events:
        part = event["part"]
        if part.get("type") != "step-finish":
            continue
        totals["calls_finished"] += 1
        tokens = part.get("tokens") or {}
        cache = tokens.get("cache") or {}
        for key, value in (("input", tokens.get("input")), ("output", tokens.get("output")),
                           ("reasoning", tokens.get("reasoning")),
                           ("cache_read", cache.get("read")), ("cache_write", cache.get("write"))):
            if isinstance(value, (int, float)):
                totals[key] += int(value)
        if isinstance(part.get("cost"), (int, float)):
            totals["cost"] += float(part["cost"])
    totals["cost"] = round(totals["cost"], 6)
    return totals


def tool_activity(events: list[dict[str, Any]]) -> dict[str, Any]:
    """What the agent did with its hands, and how long it spent doing it.

    Durations come from each tool part's own start/end stamps, so tool time is measured rather than
    inferred. Failed calls are counted separately: an agent that ran ten commands and had six of
    them fail did not do the same work as one whose commands all succeeded.
    """
    by_tool: dict[str, int] = {}
    failed: dict[str, int] = {}
    total_ms = 0
    measured = 0
    for event in events:
        part = event["part"]
        if part.get("type") != "tool":
            continue
        name = part.get("tool") or "?"
        by_tool[name] = by_tool.get(name, 0) + 1
        state = part.get("state") or {}
        if state.get("status") not in (None, "completed"):
            failed[name] = failed.get(name, 0) + 1
        stamps = state.get("time") or {}
        start, end = stamps.get("start"), stamps.get("end")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end >= start:
            total_ms += int(end - start)
            measured += 1
    return {
        "calls": sum(by_tool.values()),
        "by_tool": dict(sorted(by_tool.items())),
        "failed": dict(sorted(failed.items())),
        "failed_calls": sum(failed.values()),
        "seconds": round(total_ms / 1000.0, 3) if measured else MISSING,
        "timed_calls": measured,
    }


def timing(events: list[dict[str, Any]], *, elapsed_seconds: float | None = None,
           verification_seconds: float | None = None) -> dict[str, Any]:
    """Where the time went, with each figure labelled by how it was obtained.

    Only two of these are measured directly: the session span, from the first and last recorded
    part, and tool time, from the tool parts' own stamps. Model time is their difference and is
    named `derived` so nobody later reports it as if the provider had said so. Harness time is what
    the executor itself timed, and includes materialisation and grading, which no session row sees.
    """
    stamps = [e["time_created"] for e in events if isinstance(e["time_created"], (int, float))]
    tools = tool_activity(events)
    span = MISSING
    if len(stamps) >= 2:
        span = round((max(stamps) - min(stamps)) / 1000.0, 3) if max(stamps) > 1e11 else \
            round(float(max(stamps) - min(stamps)), 3)
    model = MISSING
    if span is not MISSING and tools["seconds"] is not MISSING:
        model = round(max(span - tools["seconds"], 0.0), 3)
    return {
        "harness_seconds": elapsed_seconds,
        "session_span_seconds": span,
        "tool_seconds": tools["seconds"],
        "model_seconds_derived": model,
        "verification_seconds": verification_seconds,
    }


def profile(db: Path, *, stage: str, model: str, provider: str = "opencode-cli",
            elapsed_seconds: float | None = None,
            verification_seconds: float | None = None) -> dict[str, Any]:
    """One stage's execution profile: what it spent, and whether the record is complete.

    `complete` is the fail-closed switch. An execution whose session was never recorded has no
    tokens and no calls, and reporting that as zeros would make an infrastructure failure look like
    a remarkably cheap run. Callers that interpret any of these numbers must refuse an incomplete
    profile rather than read it.
    """
    events = read_parts(db)
    tools = tool_activity(events)
    counts = usage(events)
    missing = []
    if not events:
        missing.append("session-transcript")
    if counts["calls_started"] == 0:
        missing.append("model-calls")
    if counts["calls_finished"] == 0:
        missing.append("provider-usage")
    return {
        "stage": stage,
        "model": model,
        "provider": provider,
        "usage": counts,
        "tools": tools,
        "time": timing(events, elapsed_seconds=elapsed_seconds,
                       verification_seconds=verification_seconds),
        "summarised": any(e.get("summary") for e in events),
        "parts": len(events),
        "missing": missing,
        "complete": not missing,
    }


def pipeline(stages: list[dict[str, Any]], *, outcome: dict[str, Any]) -> dict[str, Any]:
    """The whole run, and the stages that explain it.

    Both, never one: the pipeline is the unit of engineering value and the stages are the only way
    to say why it behaved as it did. The outcome travels with them and is not folded into them —
    resource figures are interpretable only once the property they were supposed to preserve has
    been checked.
    """
    totals = {"calls_started": 0, "calls_finished": 0, "input": 0, "output": 0, "reasoning": 0,
              "cache_read": 0, "cache_write": 0, "cost": 0.0}
    tool_calls = failed_calls = 0
    for stage in stages:
        for key in totals:
            totals[key] += stage["usage"].get(key, 0)
        tool_calls += stage["tools"]["calls"]
        failed_calls += stage["tools"]["failed_calls"]
    totals["cost"] = round(totals["cost"], 6)
    return {
        "outcome": outcome,
        "stages": stages,
        "usage": totals,
        "tool_calls": tool_calls,
        "failed_tool_calls": failed_calls,
        "complete": all(s["complete"] for s in stages) and bool(stages),
        "missing": sorted({m for s in stages for m in s["missing"]}),
    }

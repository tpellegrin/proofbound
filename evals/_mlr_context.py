#!/usr/bin/env python3
"""What actually entered a model call, and where it came from.

MLR-C2 left one accounting category unproven: `consumed`. Availability is fixed by the arm and
`read` is attributable from a path, but neither says what the model was given — a tool may open a
file whose contents are truncated before they reach the provider, and a file read once may be
replayed into every later call in the session. This module answers that question against the
executor Proofbound actually runs, rather than against an assumption about it.

**The executor.** `run_worker.py` launches `opencode run --model … --title … --dir …` with
`OPENCODE_DB` pointed at a per-attempt SQLite database. OpenCode records the session there: one
`message` row per turn and one `part` row per element of it. The parts that matter are `step-start`,
which marks the beginning of one model call; `step-finish`, which carries that call's token usage and
cost as the provider reported them; and `tool`, whose `state.output` is the text OpenCode places in
the message history and therefore hands back to the model on every subsequent call.

**So the operational definition is:**

> A representation is *consumed* when its text appears in a part that OpenCode places in the message
> history before a later model call.

**And its honest limit,** stated here so no later milestone forgets it: this reads what the executor
recorded, not a capture of the provider request body. It is the text OpenCode assembles calls from,
after the executor's own truncation, and it does not see the system prompt the CLI adds. Retained
next to it is `tokens.input` from `step-finish`, which the provider counted — an independent
aggregate that cannot be attributed by provenance but can contradict an attribution that has gone
badly wrong.

**Provenance, not knowledge.** Nothing here tries to say what a model learned. Each representation is
attributed to where it came from — the public contract, the application, the module's readable
source, the module's runtime interior, behaviour observed by running it, the harness, or nothing
identifiable. A `contract` run that disassembles the module is therefore *not* recorded as having
consumed no implementation information; it is recorded as having obtained implementation-derived
representation by a different route, which is exactly the outcome the experiment must be able to see.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

import _mlr

# Where a representation came from. Evaluation-local: these classify this fixture's transcripts and
# are not an engineering ontology.
PUBLIC_CONTRACT = "public-contract"
APPLICATION = "application"
IMPLEMENTATION_SOURCE = "implementation-source"
IMPLEMENTATION_RUNTIME = "implementation-runtime"
BEHAVIOUR = "behaviour"
HARNESS = "harness"
OTHER = "other"

PROVENANCE = (PUBLIC_CONTRACT, APPLICATION, IMPLEMENTATION_SOURCE, IMPLEMENTATION_RUNTIME,
              BEHAVIOUR, HARNESS, OTHER)

# The two classes that carry the module's interior. Kept together because the primary comparison is
# about one of them and the interpretation of that comparison depends on the other.
IMPLEMENTATION_DERIVED = (IMPLEMENTATION_SOURCE, IMPLEMENTATION_RUNTIME)

CONTRACT_DOC = "docs/storage-contract.md"

# Identifiers that exist only inside the module. Their appearance in text handed to the model is
# evidence that implementation-derived detail was delivered, whatever route requested it — which is
# how a traceback through `_with_retries` is caught without asking why the command was run.
INTERNAL_MARKERS = ("_ChecksumMismatch", "_with_retries", "_path_for", "_checksum", "_FANOUT",
                    "_ATTEMPTS", "_BACKOFF_SECONDS", "_store", "_backend")

# Facilities that render the interior of a live object. Counted only together with the module's own
# name, because `dir(` and `vars(` are ordinary Python and mean nothing on their own.
INTROSPECTION_MARKERS = ("dis.dis", "dis(", "__code__", "co_consts", "co_names", "co_varnames",
                         "co_filename", "getsource", "getmembers", "getsourcelines", "marshal",
                         "__dict__", "vars(", "dir(", "importlib", "__loader__", ".pyc",
                         "disassemble", "unmarshal")

# Running the system, as an external caller would.
BEHAVIOUR_MARKERS = ("unittest", "pytest", "python -m", "python3 -m", "test_service", "app.api",
                     "download_export", "create_export")

_PATHLIKE = re.compile(r"[A-Za-z0-9_./\-]*[/.][A-Za-z0-9_./\-]*")


def read_transcript(db: Path) -> list[dict[str, Any]]:
    """Every recorded part of the session, in the order OpenCode appended it.

    Read-only and by URI, so a live database is never modified by being measured. Ordering is by the
    message's creation time and then the part id, which is how OpenCode itself replays a session;
    the ordinal it produces is what makes "how many later calls saw this" answerable.
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
                       "summary": bool(message.get("summary")), "part": part,
                       "message": message})
    return events


def model_calls(events: list[dict[str, Any]]) -> list[int]:
    """Ordinals at which a model call began.

    `step-start` rather than `step-finish`: a representation is consumed by a call that *started*
    after it existed, and a call that failed still received its input.
    """
    return [e["ordinal"] for e in events if e["part"].get("type") == "step-start"]


def token_usage(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Provider-reported usage, summed over completed calls.

    This is the reliable token evidence. It is not attributable by provenance — the provider counts
    a whole request — so it is reported beside the byte accounting rather than divided into it. No
    bytes-per-token constant appears anywhere in this module.
    """
    totals = {"calls_finished": 0, "input": 0, "output": 0, "reasoning": 0,
              "cache_read": 0, "cache_write": 0, "cost": 0.0}
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


def _mentions_module(text: str) -> bool:
    return "objectstore" in text or any(m in text for m in INTERNAL_MARKERS)


def classify_command(command: str, built: dict[str, Any]) -> str:
    """Where the output of one shell command came from.

    Ordered most-implementation-first, so a command that both reads the module and runs the suite is
    never recorded as mere behaviour. The command text is retained alongside the class in every case,
    because §7 of the brief is right that this distinction is not always mechanically decidable and
    a later reader must be able to check the call rather than trust the label.
    """
    text = command or ""
    for token in set(_PATHLIKE.findall(text)):
        if not token or token in (".", "..") or token.startswith("-"):
            continue
        if _mlr.classify_path(token, built) == _mlr.VENDORED_IMPLEMENTATION:
            return IMPLEMENTATION_SOURCE
    if _mentions_module(text) and any(m in text for m in INTROSPECTION_MARKERS):
        return IMPLEMENTATION_RUNTIME
    if any(m in text for m in BEHAVIOUR_MARKERS):
        return BEHAVIOUR
    return OTHER


def classify_file(path: str, built: dict[str, Any]) -> str:
    """Where the contents of one opened file came from."""
    location = _mlr.classify_path(path, built)
    if location == _mlr.VENDORED_IMPLEMENTATION:
        return IMPLEMENTATION_SOURCE
    if location == _mlr.RUNTIME:
        return IMPLEMENTATION_RUNTIME
    resolved = Path(path)
    name = resolved.as_posix()
    if name.endswith(CONTRACT_DOC):
        return PUBLIC_CONTRACT
    if location == _mlr.WORKSPACE:
        return HARNESS if "DeepSeekAndDestroy" in name else APPLICATION
    return OTHER


def _internal_markers(text: str) -> list[str]:
    return sorted({m for m in INTERNAL_MARKERS if m in text})


def attribute(event: dict[str, Any], built: dict[str, Any]) -> dict[str, Any] | None:
    """One transcript part, as a representation that did or did not enter later calls.

    Assistant text and reasoning are the model's own output and are recorded — they re-enter the
    context and cost something — but they are never attributed to the module: text a model wrote
    about the implementation is not implementation representation it was given.
    """
    part = event["part"]
    kind = part.get("type")
    if kind == "tool":
        state = part.get("state") or {}
        payload = state.get("output")
        if not isinstance(payload, str):
            payload = ""
        arguments = state.get("input") or {}
        tool = part.get("tool") or "?"
        detail = ""
        if tool in ("read", "edit", "write") and isinstance(arguments.get("filePath"), str):
            detail = arguments["filePath"]
            provenance = classify_file(detail, built)
        elif tool == "bash" and isinstance(arguments.get("command"), str):
            detail = arguments["command"]
            provenance = classify_command(detail, built)
        elif tool in ("grep", "glob"):
            detail = json.dumps(arguments, sort_keys=True)[:400]
            provenance = _search_provenance(payload, built)
        else:
            detail = json.dumps(arguments, sort_keys=True)[:400] if arguments else ""
            provenance = OTHER
        metadata = state.get("metadata") or {}
        return _item(event, kind=f"tool:{tool}", provenance=provenance, detail=detail,
                     text=payload, truncated=bool(metadata.get("truncated")))
    if kind in ("text", "reasoning"):
        text = part.get("text") or ""
        if not text:
            return None
        provenance = HARNESS if event.get("role") == "user" else OTHER
        return _item(event, kind=f"{event.get('role')}:{kind}", provenance=provenance,
                     detail="", text=text, truncated=False)
    if kind == "patch":
        return _item(event, kind="patch", provenance=APPLICATION, detail="",
                     text=json.dumps(part.get("files") or [], sort_keys=True), truncated=False)
    return None


def _search_provenance(output: str, built: dict[str, Any]) -> str:
    """A search returns paths; the interesting question is whether any of them was the module."""
    for token in set(_PATHLIKE.findall(output or "")):
        if _mlr.classify_path(token, built) == _mlr.VENDORED_IMPLEMENTATION:
            return IMPLEMENTATION_SOURCE
    return OTHER


def _item(event: dict[str, Any], *, kind: str, provenance: str, detail: str, text: str,
          truncated: bool) -> dict[str, Any]:
    payload = text or ""
    return {
        "ordinal": event["ordinal"],
        "kind": kind,
        "provenance": provenance,
        "detail": detail[:600],
        "bytes": len(payload.encode("utf-8")),
        "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "truncated": truncated,
        "internal_markers": _internal_markers(payload),
    }


def ledger(events: list[dict[str, Any]], built: dict[str, Any]) -> dict[str, Any]:
    """The four quantities, kept apart.

    `unique` counts each distinct piece of text once, however often it was delivered: it answers
    *what entered reasoning at all*. `delivered` multiplies it by the number of model calls that
    began afterwards and therefore received it: it answers *what the context cost*. MLR-C3 keeps
    both because the brief is right that they answer different questions and picking one discards
    the other; the primary measurand is defined on `unique`.

    A session that OpenCode summarised is flagged. Summarisation replaces history with a shorter
    rendering, so `delivered` becomes an upper bound and says so rather than quietly overcounting.
    """
    calls = model_calls(events)
    items: list[dict[str, Any]] = []
    for event in events:
        item = attribute(event, built)
        if item is not None:
            item["delivered_to_calls"] = sum(1 for c in calls if c > item["ordinal"])
            item["delivered_bytes"] = item["bytes"] * item["delivered_to_calls"]
            items.append(item)

    by_class = {name: {"unique_bytes": 0, "delivered_bytes": 0, "items": 0}
                for name in PROVENANCE}
    seen: set[tuple[str, str]] = set()
    for item in items:
        bucket = by_class[item["provenance"]]
        bucket["items"] += 1
        bucket["delivered_bytes"] += item["delivered_bytes"]
        key = (item["provenance"], item["sha256"])
        if key not in seen:
            seen.add(key)
            bucket["unique_bytes"] += item["bytes"]

    implementation = {name: by_class[name] for name in IMPLEMENTATION_DERIVED}
    return {
        "model_calls": len(calls),
        "tokens": token_usage(events),
        "summarised": any(e.get("summary") for e in events),
        "by_provenance": by_class,
        "implementation_derived": {
            "unique_bytes": sum(v["unique_bytes"] for v in implementation.values()),
            "delivered_bytes": sum(v["delivered_bytes"] for v in implementation.values()),
        },
        "implementation_source_unique_bytes": by_class[IMPLEMENTATION_SOURCE]["unique_bytes"],
        "implementation_runtime_unique_bytes": by_class[IMPLEMENTATION_RUNTIME]["unique_bytes"],
        "items_carrying_internal_names": sum(1 for i in items if i["internal_markers"]),
        "truncated_items": sum(1 for i in items if i["truncated"]),
        "items": items,
    }


def consumed(db: Path, built: dict[str, Any]) -> dict[str, Any]:
    """The ledger for one attempt's recorded session."""
    return ledger(read_transcript(db), built)

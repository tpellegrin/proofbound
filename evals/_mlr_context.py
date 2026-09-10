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

# How a representation was asked for. The MLR-C3 defect was classifying a whole tool call from the
# command name alone: `help(objectstore)` returned 5,397 bytes of the package's interior and was
# scored `other`, and `python3 -m pydoc objectstore` matched a behaviour marker and was scored as
# running the system. Route and delivered content are now two separate channels, and the routes that
# render a live object are their own family rather than a fallthrough.
SOURCE_FILE = "source-file"
SEARCH = "search"
DOCUMENTATION = "documentation"
INTROSPECTION = "introspection"
RUN = "run"
EDIT = "edit"
UNKNOWN = "unknown"

# Python's documentation surface. Separated from introspection because what it returns is sometimes
# purely public — `__all__`, a signature, a docstring — and sometimes the package's interior. Which
# one it was is decided by the bytes that came back, not by the verb that asked.
DOCUMENTATION_MARKERS = ("help(", "pydoc", "render_doc", "__doc__", "getdoc", "plaintext.document")

# Facilities that render the interior of a live object.
INTROSPECTION_MARKERS = ("dis.dis", "dis(", "__code__", "co_consts", "co_names", "co_varnames",
                         "co_filename", "getsource", "getmembers", "getsourcelines", "marshal",
                         "__dict__", "vars(", "dir(", "importlib", "__loader__", ".pyc",
                         "disassemble", "unmarshal", "signature", "iter_modules", "__path__",
                         "__all__", "mro(", "__mro__", "__module__")

# Running the system, as an external caller would.
RUN_MARKERS = ("unittest", "pytest", "python -m", "python3 -m", "test_service", "app.api",
               "download_export", "create_export")


def internal_names(source: Path | None = None) -> tuple[str, ...]:
    """Names that exist only inside the module, derived from its source rather than listed by hand.

    A hand-written list is exactly the wrong instrument here: it silently stops covering the module
    the moment the module changes, and the failure looks like an absence of evidence. This walks the
    runtime source with `ast` and takes the private submodule stems plus every private module-level
    binding in them, so a new internal constant is covered the day it is written.

    These names are the fingerprint of implementation-derived text. Their appearance in something
    handed to the model is evidence the interior was disclosed, whichever route asked for it.
    """
    import ast
    root = Path(source) if source is not None else _mlr.FIXTURE / "runtime" / "objectstore"
    found: set[str] = set()
    for module in sorted(Path(root).glob("*.py")):
        if module.stem.startswith("_") and not module.stem.startswith("__"):
            found.add(module.stem)
        try:
            tree = ast.parse(module.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            names = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names = [node.name]
            elif isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names = [node.target.id]
            found.update(n for n in names if n.startswith("_") and not n.startswith("__"))
    return tuple(sorted(found))


def _name_pattern(names: tuple[str, ...]) -> "re.Pattern[str]":
    """Word-bounded, so `_store` does not match inside `export_stored` or `objectstore`."""
    if not names:
        return re.compile(r"(?!x)x")
    return re.compile(r"\b(?:%s)\b" % "|".join(re.escape(n) for n in names))


_PATHLIKE = re.compile(r"[A-Za-z0-9_./\-]*[/.][A-Za-z0-9_./\-]*")


def _mentions_module(text: str) -> bool:
    return "objectstore" in text


def command_route(command: str, built: dict[str, Any]) -> str:
    """Which family of thing one shell command asked for.

    Documentation and introspection are tested before running the system, which is the ordering the
    C3 defect got wrong: `python3 -m pydoc objectstore` matches a run marker and is not a run.
    """
    text = command or ""
    for token in set(_PATHLIKE.findall(text)):
        if not token or token in (".", "..") or token.startswith("-"):
            continue
        if _mlr.classify_path(token, built) == _mlr.VENDORED_IMPLEMENTATION:
            return SOURCE_FILE
    if _mentions_module(text):
        if any(m in text for m in DOCUMENTATION_MARKERS):
            return DOCUMENTATION
        if any(m in text for m in INTROSPECTION_MARKERS):
            return INTROSPECTION
    if any(m in text for m in RUN_MARKERS):
        return RUN
    return UNKNOWN


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
    # Closed explicitly: sqlite3's context manager commits the transaction but leaves the
    # connection open, which leaks a handle per session read and surfaces as a ResourceWarning
    # once a suite reads many of them.
    conn = sqlite3.connect(uri, uri=True)
    try:
        rows = conn.execute(
            "SELECT p.id, p.message_id, p.data, m.data, m.time_created "
            "FROM part p JOIN message m ON m.id = p.message_id "
            "ORDER BY m.time_created, p.message_id, p.id").fetchall()
    finally:
        conn.close()
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


_INTERNAL_NAMES = None
_INTERNAL_RE = None


def _internal_hits(text: str) -> list[str]:
    """Which module-internal names the delivered text disclosed."""
    global _INTERNAL_NAMES, _INTERNAL_RE
    if _INTERNAL_RE is None:
        _INTERNAL_NAMES = internal_names()
        _INTERNAL_RE = _name_pattern(_INTERNAL_NAMES)
    return sorted(set(_INTERNAL_RE.findall(text or "")))


def attribute(event: dict[str, Any], built: dict[str, Any]) -> dict[str, Any] | None:
    """One transcript part, as a representation with a route and a provenance.

    Two channels, because MLR-C3 proved one is not enough. The **route** says what was asked for and
    is read from the path or the command. The **content** says what came back, and decides the case
    the route cannot: `help(objectstore)` and `inspect.signature(objectstore.put)` are the same kind
    of request, and one returns the package's private submodules while the other returns a public
    signature. Asking the bytes is the only mechanically defensible way to tell them apart.

    Assistant text and reasoning are recorded — they re-enter context and cost something — but are
    never attributed to the module: text a model wrote about the implementation is not
    implementation representation it was given.
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
            route = EDIT if tool in ("edit", "write") else SOURCE_FILE
            provenance = classify_file(detail, built)
        elif tool == "bash" and isinstance(arguments.get("command"), str):
            detail = arguments["command"]
            route = command_route(detail, built)
            provenance = _command_provenance(route, payload, built)
        elif tool in ("grep", "glob"):
            detail = json.dumps(arguments, sort_keys=True)[:400]
            route = SEARCH
            provenance = _search_provenance(payload, built)
        else:
            detail = json.dumps(arguments, sort_keys=True)[:400] if arguments else ""
            route = UNKNOWN
            provenance = OTHER
        metadata = state.get("metadata") or {}
        return _item(event, kind=f"tool:{tool}", route=route, provenance=provenance, detail=detail,
                     text=payload, truncated=bool(metadata.get("truncated")),
                     status=state.get("status"))
    if kind in ("text", "reasoning"):
        text = part.get("text") or ""
        if not text:
            return None
        provenance = HARNESS if event.get("role") == "user" else OTHER
        return _item(event, kind=f"{event.get('role')}:{kind}", route=UNKNOWN,
                     provenance=provenance, detail="", text=text, truncated=False, status=None)
    if kind == "patch":
        return _item(event, kind="patch", route=EDIT, provenance=APPLICATION, detail="",
                     text=json.dumps(part.get("files") or [], sort_keys=True), truncated=False,
                     status=None)
    return None


def _command_provenance(route: str, output: str, built: dict[str, Any]) -> str:
    """Where a shell command's output came from, once both channels have spoken.

    The documentation and introspection routes split on content: interior names present means the
    module's inside was rendered, and their absence means what came back was the public surface. A
    run of the system that happens to print a traceback through the module's interior stays a run —
    its bytes are mostly test output — but the disclosure is recorded on the item either way.
    """
    if route == SOURCE_FILE:
        return IMPLEMENTATION_SOURCE
    if route in (DOCUMENTATION, INTROSPECTION):
        return IMPLEMENTATION_RUNTIME if _internal_hits(output) else PUBLIC_CONTRACT
    if route == RUN:
        return BEHAVIOUR
    return IMPLEMENTATION_RUNTIME if _internal_hits(output) else OTHER


def _search_provenance(output: str, built: dict[str, Any]) -> str:
    """A search returns paths; the interesting question is whether any of them was the module."""
    for token in set(_PATHLIKE.findall(output or "")):
        if _mlr.classify_path(token, built) == _mlr.VENDORED_IMPLEMENTATION:
            return IMPLEMENTATION_SOURCE
    return OTHER


def _item(event: dict[str, Any], *, kind: str, route: str, provenance: str, detail: str, text: str,
          truncated: bool, status: str | None) -> dict[str, Any]:
    payload = text or ""
    hits = _internal_hits(payload)
    return {
        "ordinal": event["ordinal"],
        "kind": kind,
        "route": route,
        "provenance": provenance,
        "detail": detail[:600],
        "bytes": len(payload.encode("utf-8")),
        "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "truncated": truncated,
        "status": status,
        "internal_names": hits,
    }


def ledger(events: list[dict[str, Any]], built: dict[str, Any]) -> dict[str, Any]:
    """The four quantities, kept apart, plus the disclosure channel that stands beside them.

    `unique` counts each distinct piece of text once however often it was delivered: it answers
    *what entered reasoning at all*, and the primary measurand is defined on it. `delivered`
    multiplies by the number of model calls that began afterwards: it answers *what the context
    cost*. Both are kept because they answer different questions and choosing one discards the other.

    `disclosure` is the second channel MLR-C3 needed and did not have in usable form: bytes of text
    that carried module-internal names, whatever route requested them. It is reported separately and
    never added to the provenance totals — a 500-byte test output with a 60-byte traceback through
    the module's interior is test output that disclosed something, not 500 bytes of implementation.

    A session OpenCode summarised is flagged, which makes `delivered` an upper bound and says so.
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
    by_route: dict[str, dict[str, int]] = {}
    seen: set[tuple[str, str]] = set()
    disclosure_bytes = 0
    disclosed: set[str] = set()
    disclosure_seen: set[str] = set()
    for item in items:
        bucket = by_class[item["provenance"]]
        bucket["items"] += 1
        bucket["delivered_bytes"] += item["delivered_bytes"]
        key = (item["provenance"], item["sha256"])
        if key not in seen:
            seen.add(key)
            bucket["unique_bytes"] += item["bytes"]
        route = by_route.setdefault(item["route"], {"items": 0, "unique_bytes": 0})
        route["items"] += 1
        if item["internal_names"]:
            disclosed.update(item["internal_names"])
            if item["sha256"] not in disclosure_seen:
                disclosure_seen.add(item["sha256"])
                disclosure_bytes += item["bytes"]
    route_unique: dict[str, set[str]] = {}
    for item in items:
        route_unique.setdefault(item["route"], set())
        if item["sha256"] not in route_unique[item["route"]]:
            route_unique[item["route"]].add(item["sha256"])
            by_route[item["route"]]["unique_bytes"] += item["bytes"]

    implementation = {name: by_class[name] for name in IMPLEMENTATION_DERIVED}
    return {
        "model_calls": len(calls),
        "tokens": token_usage(events),
        "summarised": any(e.get("summary") for e in events),
        "by_provenance": by_class,
        "by_route": dict(sorted(by_route.items())),
        "implementation_derived": {
            "unique_bytes": sum(v["unique_bytes"] for v in implementation.values()),
            "delivered_bytes": sum(v["delivered_bytes"] for v in implementation.values()),
        },
        "implementation_source_unique_bytes": by_class[IMPLEMENTATION_SOURCE]["unique_bytes"],
        "implementation_runtime_unique_bytes": by_class[IMPLEMENTATION_RUNTIME]["unique_bytes"],
        "disclosure": {
            "unique_bytes": disclosure_bytes,
            "items": sum(1 for i in items if i["internal_names"]),
            "names": sorted(disclosed),
        },
        "items_carrying_internal_names": sum(1 for i in items if i["internal_names"]),
        "truncated_items": sum(1 for i in items if i["truncated"]),
        "items": items,
    }


def consumed(db: Path, built: dict[str, Any]) -> dict[str, Any]:
    """The ledger for one attempt's recorded session."""
    return ledger(read_transcript(db), built)

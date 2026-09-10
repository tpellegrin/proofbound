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

import _lineage
import _mlr

# Where a representation came from. Evaluation-local: these classify this fixture's transcripts and
# are not an engineering ontology.
PUBLIC_CONTRACT = "public-contract"
APPLICATION = "application"
IMPLEMENTATION_SOURCE = "implementation-source"
IMPLEMENTATION_RUNTIME = "implementation-runtime"
IMPLEMENTATION_METADATA = _lineage.IMPLEMENTATION_METADATA
BEHAVIOUR = "behaviour"
HARNESS = "harness"
MODEL_DERIVED = _lineage.MODEL_DERIVED
OTHER = "other"

PROVENANCE = (PUBLIC_CONTRACT, APPLICATION, IMPLEMENTATION_SOURCE, IMPLEMENTATION_RUNTIME,
              BEHAVIOUR, HARNESS, MODEL_DERIVED, OTHER)

# The two classes that carry the module's interior. Kept together because the primary comparison is
# about one of them and the interpretation of that comparison depends on the other.
IMPLEMENTATION_DERIVED = (IMPLEMENTATION_SOURCE, IMPLEMENTATION_RUNTIME)

# How strongly the origin on an item is evidenced, strongest first. This is the axis the previous
# instrument did not have, and every defect it suffered was a weaker basis silently overruling a
# stronger one — a temporary path erasing a known disassembly, a command argument turning a directory
# listing into source, matching bytes turning a model's own sentence into a file it never opened.
BASIS_ANCESTRY = "ancestry"          # linked to the event that produced the information
BASIS_ARTIFACT = "artifact-path"     # the file opened is a classified artifact of the fixture
BASIS_AUTHOR = "author"              # the model wrote it, so its origin is the model
BASIS_CONTENT = "content"            # nothing stronger spoke; the delivered bytes decided
BASIS_ROUTE = "command-route"        # the family of request decided, with no content to check
BASIS_DEFAULT = "default"            # no evidence beyond the kind of part

BASES = (BASIS_ANCESTRY, BASIS_ARTIFACT, BASIS_AUTHOR, BASIS_CONTENT, BASIS_ROUTE, BASIS_DEFAULT)

# Bases that content may describe but never overrule. `resolve_origin` is free to say what a text
# looks like; when one of these decided the origin, what the text looks like does not change where it
# came from.
SETTLED_BASES = (BASIS_ANCESTRY, BASIS_ARTIFACT, BASIS_AUTHOR)

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


# Where a shell command puts what it produced. Not a shell parser: a redirection or a `tee` is the
# whole of what is claimed, and a command whose output lands somewhere by any other means is left
# unlinked rather than guessed at. Partial ancestry that is right beats complete ancestry that is
# invented — and where the link is missed, the representation itself still has to be classified,
# which is why content remains a second line of defence rather than the first.
_REDIRECTION = re.compile(r"(?:^|[\s;&|])(?:\d?>>?|\|\s*tee(?:\s+-a)?)\s+(?P<path>[^\s;|&<>()]+)")
_NOT_A_FILE = ("/dev/null", "/dev/stdout", "/dev/stderr", "&1", "&2")

_COPY = re.compile(r"(?:^|[\s;&|])(?:cp|mv|install)\s+(?P<args>[^;&|<>\n]+)")

# A command whose output is text the command itself carries.
_AUTHORED_WRITE = re.compile(r"<<-?\s*['\"]?\w+|(?:^|[\s;&|])(?:echo|printf)\s")


def produced_artifacts(command: str) -> tuple[str, ...]:
    """Paths this command writes its output to.

    Redirections and `tee`, plus the destination of a copy or a move — the three ways an agent
    actually materialises something it has just produced. A command that puts bytes somewhere by any
    other means is left unlinked rather than guessed at.
    """
    found = []
    for match in _REDIRECTION.finditer(command or ""):
        path = match.group("path").strip("'\"")
        if not path or path in _NOT_A_FILE or path.startswith("&"):
            continue
        if path not in found:
            found.append(path)
    for match in _COPY.finditer(command or ""):
        tokens = [tok for tok in match.group("args").split() if not tok.startswith("-")]
        if len(tokens) >= 2 and tokens[-1] not in found:
            found.append(tokens[-1].strip("'\""))
    return tuple(found)


def referenced_paths(command: str) -> tuple[str, ...]:
    """Every path-shaped token in a command, for asking whether it names a known artifact."""
    return tuple(sorted({tok.strip("'\"") for tok in _PATHLIKE.findall(command or "")
                         if tok and tok not in (".", "..") and not tok.startswith("-")}))


def is_module_source_file(token: str, built: dict[str, Any]) -> bool:
    """Whether one path token names one of the module's own source files.

    The distinction the previous instrument lacked. `third_party/objectstore-1.4.0/objectstore/
    _store.py` is a module source file; `third_party/objectstore-1.4.0` is a directory that contains
    one. Mentioning the directory in a command does not make that command's output source, and two
    runs were charged 301 and 224 bytes of source for a `ls` that returned three paths and a version
    string.
    """
    if _mlr.classify_path(token, built) != _mlr.VENDORED_IMPLEMENTATION:
        return False
    return Path(token).name in _module_files()


def artifact_origin(route: str, command: str, built: dict[str, Any]) -> str | None:
    """What a command that produces a file was producing, judged from the command itself.

    A redirecting command hands back nothing but a shell's acknowledgement — a byte count, a prompt,
    silence — so its own output cannot say what it made. The request can. A disassembly redirected
    into a file is a disassembly wherever it is later read from, and that is the fact the old
    instrument had no way to carry across the redirection.
    """
    if route == SOURCE_FILE and any(is_module_source_file(tok, built)
                                    for tok in referenced_paths(command)):
        return IMPLEMENTATION_SOURCE
    if route in (INTROSPECTION, DOCUMENTATION):
        return IMPLEMENTATION_RUNTIME
    if route == RUN:
        return BEHAVIOUR
    if _AUTHORED_WRITE.search(command or ""):
        # The bytes came out of the command itself, and the model wrote the command. A file filled
        # from a heredoc or an `echo` carries the model's text, so reading it back is a replay of
        # what the model already said rather than a fresh observation — even when what it said
        # reproduces the module exactly.
        return MODEL_DERIVED
    return None


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


class _Session:
    """What one transcript has established so far, as it is walked in order.

    Two indexes, both of them links between events rather than conclusions about them. The first
    remembers which files a command wrote, so a later read of one of those files inherits what the
    command was doing. The second remembers the content each origin has already been seen carrying,
    so the same information arriving a second way — echoed into a log, copied to a scratch file,
    quoted back — is recognised as the same information and keeps its history.

    Neither index stores a verdict that could be recomputed from the item list; both store the link
    that would otherwise be lost, which is the only thing a later pass cannot reconstruct.
    """

    def __init__(self, built: dict[str, Any]):
        self.built = built
        self._artifacts: dict[str, str] = {}
        self._content: dict[tuple[str, str], str] = {}

    def _key(self, path: str) -> str:
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = Path(self.built["workspace"]) / resolved
        try:
            return resolved.resolve().as_posix()
        except OSError:                                     # pragma: no cover - unresolvable path
            return resolved.as_posix()

    def note_artifact(self, path: str, origin: str) -> None:
        self._artifacts[self._key(path)] = origin

    def artifact(self, path: str) -> str | None:
        return self._artifacts.get(self._key(path))

    def note_content(self, identities: dict[str, str | None], origin: str) -> None:
        if origin in (OTHER, _lineage.UNRESOLVED):
            return
        for form, identity in identities.items():
            if identity:
                self._content.setdefault((form, identity), origin)

    def echo(self, identities: dict[str, str | None]) -> str | None:
        """The origin this exact content was first seen carrying, if it has been seen before."""
        for form in _lineage.SUBSTANTIVE_FORMS:
            identity = identities.get(form)
            if identity and (form, identity) in self._content:
                return self._content[(form, identity)]
        return None


# Classifications that identify the artifact itself rather than the container it sits in. A read of
# the module's source is settled by its path; a read of the worker log is not, because the log's path
# says where the bytes were sitting and nothing about what they are. The workspace is a container in
# the same sense — an agent may write anything into it — so `application` does not settle either.
_SETTLING_LOCATIONS = (IMPLEMENTATION_SOURCE, IMPLEMENTATION_RUNTIME, PUBLIC_CONTRACT)


def attribute(event: dict[str, Any], built: dict[str, Any],
              session: "_Session | None" = None) -> dict[str, Any] | None:
    """One transcript part, as a representation with a route, a form and an origin.

    Three channels, because two were not enough. The **route** says what was asked for. The **form**
    says what the delivered bytes encode. The **origin** says where the information came from, and is
    settled by the strongest evidence available: a link to the event that produced it, failing that
    the identity of the artifact opened, failing that the family of the request, failing that the
    bytes, and failing all of those, nothing — recorded as unresolved rather than as zero.

    Assistant text and reasoning are attributed to the model. That is an origin and not a shrug: text
    a model wrote is text the model wrote, however exactly it reproduces something it read.
    """
    session = session if session is not None else _Session(built)
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
        basis = BASIS_DEFAULT
        if tool in ("read", "edit", "write") and isinstance(arguments.get("filePath"), str):
            detail = arguments["filePath"]
            route = EDIT if tool in ("edit", "write") else SOURCE_FILE
            provenance = classify_file(detail, built)
            ancestry = session.artifact(detail)
            if ancestry:
                basis = BASIS_ANCESTRY
            else:
                basis = BASIS_ARTIFACT if provenance in _SETTLING_LOCATIONS else BASIS_DEFAULT
            if tool == "write":
                # The model produced this file. A later read of it is a replay of the model's own
                # text, not a fresh observation of anything.
                session.note_artifact(detail, MODEL_DERIVED)
        elif tool == "bash" and isinstance(arguments.get("command"), str):
            detail = arguments["command"]
            route = command_route(detail, built)
            written = produced_artifacts(detail)
            provenance = _command_provenance(route, payload, built)
            ancestry = next((session.artifact(tok) for tok in referenced_paths(detail)
                             if tok not in written and session.artifact(tok)), None)
            basis = BASIS_ANCESTRY if ancestry else BASIS_ROUTE
            produced = artifact_origin(route, detail, built)
            if produced:
                for path in written:
                    session.note_artifact(path, produced)
        elif tool in ("grep", "glob"):
            detail = json.dumps(arguments, sort_keys=True)[:400]
            route = SEARCH
            provenance, basis = _search_provenance(payload, built), BASIS_ROUTE
            ancestry = None
        else:
            detail = json.dumps(arguments, sort_keys=True)[:400] if arguments else ""
            route = UNKNOWN
            provenance, basis, ancestry = OTHER, BASIS_DEFAULT, None
        metadata = state.get("metadata") or {}
        return _item(event, session, kind=f"tool:{tool}", route=route, provenance=provenance,
                     basis=basis, ancestry=ancestry, detail=detail, text=payload,
                     truncated=bool(metadata.get("truncated")), status=state.get("status"))
    if kind in ("text", "reasoning"):
        text = part.get("text") or ""
        if not text:
            return None
        if event.get("role") == "user":
            provenance, basis = HARNESS, BASIS_DEFAULT
        else:
            provenance, basis = MODEL_DERIVED, BASIS_AUTHOR
        return _item(event, session, kind=f"{event.get('role')}:{kind}", route=UNKNOWN,
                     provenance=provenance, basis=basis, ancestry=None, detail="", text=text,
                     truncated=False, status=None)
    if kind == "patch":
        return _item(event, session, kind="patch", route=EDIT, provenance=APPLICATION,
                     basis=BASIS_ARTIFACT, ancestry=None, detail="",
                     text=json.dumps(part.get("files") or [], sort_keys=True), truncated=False,
                     status=None)
    return None


def _command_provenance(route: str, output: str, built: dict[str, Any]) -> str:
    """Where a shell command's output came from, once both channels have spoken.

    The route says what was asked for; the output says what came back. Neither alone is enough, and
    the previous version let the route win outright for `source-file` — so a command that merely
    *named* the module's directory turned its own listing into implementation source.

    Now the route only says which origins are available, and the delivered bytes choose among them.
    A command that names a module source file and returns source lines is source. A command that
    renders the interior returns runtime representation. A command that returns nothing but the
    module's file names returns metadata. A command that asked to introspect and got back only a
    public surface got back a public surface.
    """
    comp = _components(output)
    forms = comp["bytes"]
    if route == SOURCE_FILE:
        if forms[_lineage.SOURCE_FORM] >= _lineage.MATERIAL_BYTES:
            return IMPLEMENTATION_SOURCE
        if forms[_lineage.DISASSEMBLY] + forms[_lineage.RUNTIME_STRUCTURE] >= _lineage.MATERIAL_BYTES:
            return IMPLEMENTATION_RUNTIME
        if forms[_lineage.PATH_METADATA] >= _lineage.MATERIAL_BYTES:
            return _lineage.IMPLEMENTATION_METADATA
        return OTHER
    if route in (DOCUMENTATION, INTROSPECTION):
        return IMPLEMENTATION_RUNTIME if _internal_hits(output) else PUBLIC_CONTRACT
    if route == RUN:
        return BEHAVIOUR
    # Nothing about the request narrows the answer, so the delivered representation decides. It is
    # asked as a decomposition rather than as a name match, because a name match cannot tell a
    # rendering of the interior from a listing that only names its files — `git ls-files` and a
    # `find` over the compiled package are the cases that prove it, and both used to be charged to
    # the runtime channel for containing the word `_store`.
    if forms[_lineage.SOURCE_FORM] >= _lineage.MATERIAL_BYTES:
        return IMPLEMENTATION_SOURCE
    if forms[_lineage.DISASSEMBLY] + forms[_lineage.RUNTIME_STRUCTURE] >= _lineage.MATERIAL_BYTES:
        return IMPLEMENTATION_RUNTIME
    if forms[_lineage.PATH_METADATA] >= _lineage.MATERIAL_BYTES:
        return _lineage.IMPLEMENTATION_METADATA
    return OTHER


def _search_provenance(output: str, built: dict[str, Any]) -> str:
    """A search returns paths; the interesting question is whether any of them was the module."""
    for token in set(_PATHLIKE.findall(output or "")):
        if _mlr.classify_path(token, built) == _mlr.VENDORED_IMPLEMENTATION:
            return IMPLEMENTATION_SOURCE
    return OTHER


_MARKS = None
_MODULE_FILES = None


def _fingerprint() -> "frozenset[str]":
    global _MARKS
    if _MARKS is None:
        _MARKS = _lineage.source_fingerprint(_mlr.FIXTURE / "runtime" / "objectstore")
    return _MARKS


def _module_files() -> tuple[str, ...]:
    global _MODULE_FILES
    if _MODULE_FILES is None:
        _MODULE_FILES = _lineage.module_paths(_mlr.FIXTURE / "runtime" / "objectstore")
    return _MODULE_FILES


def _components(text: str) -> dict[str, Any]:
    """This delivered text, split into disjoint representation components."""
    if _INTERNAL_RE is None:
        _internal_hits("")
    return _lineage.components(text or "", _fingerprint(), _module_files(), _INTERNAL_RE,
                               "objectstore")


def resolve_origin(route: str, requested: str, text: str, *, basis: str = BASIS_ROUTE,
                   ancestry: str | None = None,
                   comp: dict[str, Any] | None = None) -> dict[str, Any]:
    """What this delivered text is, and — separately — where the strongest available evidence says
    it came from.

    Three questions, kept apart. **Form** is what the bytes encode, and is decided by the bytes
    alone. **Origin** is where the information came from, and is decided by the strongest evidence
    there is. **Route** is how it arrived, and is the caller's to record.

    The precedence is the whole of the repair. Linked ancestry outranks a classified path; a
    classified path outranks the family of request; all of those outrank what the text looks like;
    and what the text looks like outranks nothing but the absence of evidence. Content may still
    *promote* an origin nobody could name — that is how source echoed through a log is caught — but
    it may never overwrite an origin something stronger already settled. Two byte-identical texts can
    therefore carry different origins, which is the point: a module source line read from the module
    and the same line typed out by a model that only saw bytecode are the same form and different
    histories.

    Metadata is claimed only when the module's file names are most of what came back, and only when
    nothing more substantial came with them.
    """
    comp = comp if comp is not None else _components(text)
    forms = comp["bytes"]
    total = comp["total"]
    form = _lineage.form_of(comp)
    metadata = _lineage.metadata_in(text, _module_files(), "objectstore")
    origin = ancestry if ancestry else requested
    settled = basis in SETTLED_BASES

    if not settled:
        if forms[_lineage.SOURCE_FORM] >= _lineage.MATERIAL_BYTES \
                and origin not in _lineage.IMPLEMENTATION_ORIGINS:
            origin = _lineage.IMPLEMENTATION_SOURCE
        elif (forms[_lineage.DISASSEMBLY] + forms[_lineage.RUNTIME_STRUCTURE]) * 2 >= total \
                and forms[_lineage.DISASSEMBLY] + forms[_lineage.RUNTIME_STRUCTURE] \
                >= _lineage.MATERIAL_BYTES \
                and origin not in _lineage.IMPLEMENTATION_ORIGINS:
            origin = IMPLEMENTATION_RUNTIME
        elif metadata["references"] and origin not in _lineage.IMPLEMENTATION_ORIGINS \
                and forms[_lineage.PATH_METADATA] * 2 >= total:
            # Only when the references are most of what came back. A `git ls-files` listing *is* the
            # module's structure; a test run whose traceback happens to name one file is test output
            # that disclosed a file name, and relabelling the whole artifact by its smallest part is
            # the same mistake as labelling it by its path. The references are recorded on the item
            # either way, so a minority disclosure is visible without being promoted.
            origin = _lineage.IMPLEMENTATION_METADATA

    # How much of this is *direct* implementation source. When the artifact opened is one of the
    # module's own files the whole delivered rendering counts, because a line-numbered read of a
    # 2,200-byte file delivered 2,697 bytes of that file and charging only the distinctive lines
    # would understate what the model received. Everywhere else only the lines demonstrably verbatim
    # from the module are claimed — and only when the origin is source at all, so a reconstruction
    # that matches byte for byte contributes nothing to the primary measurand.
    source_bytes = 0
    identity = None
    asserted = (ancestry or requested) == _lineage.IMPLEMENTATION_SOURCE
    if origin == _lineage.IMPLEMENTATION_SOURCE:
        source_bytes = (len((text or "").encode("utf-8")) if asserted
                        else forms[_lineage.SOURCE_FORM])
        identity = _lineage.source_identity(comp["matched"]) if comp["matched"] else \
            hashlib.sha256((text or "").encode("utf-8")).hexdigest()

    # Source-shaped text that did not come from source. Reported in its own channel: it is evidence
    # about the treatment — how completely an agent rebuilt the interior it could not read — and it
    # is not evidence that the boundary leaked.
    reconstruction = forms[_lineage.SOURCE_FORM] if origin != _lineage.IMPLEMENTATION_SOURCE else 0
    reconstruction_identity = (_lineage.source_identity(comp["matched"])
                               if reconstruction >= _lineage.MATERIAL_BYTES else None)

    return {
        "origin": origin,
        "form": form,
        "form_bytes": dict(forms),
        "source_bytes": source_bytes,
        "source_lines": comp["source_lines"],
        "source_identity": identity,
        "reconstruction_bytes": reconstruction,
        "reconstruction_identity": reconstruction_identity,
        "metadata": metadata,
        "component_identities": {f: _lineage.component_identity(comp, f)
                                 for f in _lineage.SUBSTANTIVE_FORMS},
        # True when something other than the path or the route decided: the delivered bytes, or a
        # link to the event that produced them. This is the count that says whether the lineage
        # machinery did anything in a given run.
        "by_lineage": origin != requested,
    }


def _item(event: dict[str, Any], session: "_Session", *, kind: str, route: str, provenance: str,
          basis: str, ancestry: str | None, detail: str, text: str, truncated: bool,
          status: str | None) -> dict[str, Any]:
    payload = text or ""
    hits = _internal_hits(payload)
    comp = _components(payload)
    identities = {f: _lineage.component_identity(comp, f) for f in _lineage.SUBSTANTIVE_FORMS}
    if ancestry is None and basis not in SETTLED_BASES:
        # This exact content has been delivered before. Whatever it was then, it still is: a log that
        # echoes a source read echoes source, a log that echoes a disassembly echoes a disassembly,
        # and a log that echoes the model's own sentence echoes the model. The log is a route.
        seen = session.echo(identities)
        if seen:
            ancestry, basis = seen, BASIS_ANCESTRY
    lineage = resolve_origin(route, provenance, payload, basis=basis, ancestry=ancestry, comp=comp)
    origin = lineage["origin"]
    if basis not in SETTLED_BASES and origin != (ancestry or provenance):
        # Nothing stronger had an answer and the delivered bytes supplied one. Recorded as such, so
        # the audit can see how much of a run's attribution rests on the weakest evidence there is.
        basis = BASIS_CONTENT
    # An item that plainly discloses the interior but resolves to no implementation origin is not
    # quietly filed as harmless. It is marked unresolved, so the audit sees an open question rather
    # than a clean zero.
    # Fail closed on *inbound* text only, and only where nothing settled the origin. Text the model
    # wrote is downstream of what it already consumed, not a route by which information enters, and
    # marking it unresolved would flag every run that reasoned aloud about the module it had just
    # read. Where ancestry or an artifact identified the source of the bytes, a disclosure is
    # explained rather than open. It stays recorded and flagged as a disclosure diagnostic; the check
    # that matters is whether such text appears in a run that consumed no implementation at all,
    # which the audit asks separately.
    inbound = kind.startswith("tool:") or kind.startswith("user:")
    if inbound and hits and basis not in SETTLED_BASES \
            and origin not in _lineage.IMPLEMENTATION_ORIGINS \
            and not lineage["metadata"]["references"]:
        origin = _lineage.UNRESOLVED
    session.note_content(identities, origin)
    return {
        "ordinal": event["ordinal"],
        "kind": kind,
        "route": route,
        "basis": basis,
        "requested": provenance,
        "origin": origin,
        "provenance": origin,
        "form": lineage["form"],
        "form_bytes": lineage["form_bytes"],
        "by_lineage": lineage["by_lineage"],
        "detail": detail[:600],
        "bytes": len(payload.encode("utf-8")),
        "source_bytes": lineage["source_bytes"],
        "source_lines": lineage["source_lines"],
        "source_identity": lineage["source_identity"],
        "reconstruction_bytes": lineage["reconstruction_bytes"],
        "reconstruction_identity": lineage["reconstruction_identity"],
        "metadata_bytes": lineage["metadata"]["bytes"],
        "metadata_names": lineage["metadata"]["names"],
        "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "truncated": truncated,
        "status": status,
        "internal_names": hits,
    }


def contradiction(item: dict[str, Any]) -> str | None:
    """Whether an item's recorded origin is contradicted by what it delivered.

    Detection, never classification. This does not reassign anything — a second classifier quietly
    overruling the first is how instruments acquire two disagreeing opinions and report the louder
    one. It asks one question: given how weakly this origin is evidenced, does the delivered
    representation contradict it strongly enough that the attribution should be treated as failed?

    Only weakly evidenced origins can be contradicted. Where ancestry or an artifact settled the
    origin, a form that disagrees is not a contradiction but the finding: source-shaped text under a
    runtime ancestry is reconstruction, and reporting it as an escape would make the instrument
    unable to see the very thing it was repaired to see.
    """
    if item["basis"] in SETTLED_BASES:
        return None
    forms = item["form_bytes"]
    total = max(item["bytes"], 1)
    runtime_form = forms[_lineage.DISASSEMBLY] + forms[_lineage.RUNTIME_STRUCTURE]
    if runtime_form * 2 >= total and runtime_form >= _lineage.MATERIAL_BYTES \
            and item["origin"] not in _lineage.IMPLEMENTATION_ORIGINS:
        return "runtime-form body under a non-implementation origin"
    if forms[_lineage.SOURCE_FORM] * 2 >= total \
            and forms[_lineage.SOURCE_FORM] >= _lineage.MATERIAL_BYTES \
            and item["origin"] != _lineage.IMPLEMENTATION_SOURCE:
        return "source-form body under a non-source origin"
    if item["origin"] == _lineage.IMPLEMENTATION_SOURCE \
            and forms[_lineage.SOURCE_FORM] < _lineage.MATERIAL_BYTES:
        return "source origin with no source content"
    return None


def ledger(events: list[dict[str, Any]], built: dict[str, Any]) -> dict[str, Any]:
    """The four quantities, kept apart, with origin now decided by content rather than by path.

    `unique` counts each distinct piece of text once however often it was replayed; `delivered`
    multiplies it by the model calls that began afterwards. Both are kept because they answer
    different questions.

    **Source is counted by lineage identity, not by the blob it arrived in.** The same lines read
    directly, echoed into a log and read back again are one unique implementation-source
    representation and three deliveries. Counting them three times would inflate exactly the number
    the paired experiment turns on, and counting them once for the first route only would lose the
    context cost of the replay.

    Metadata and runtime-derived representation are reported in their own units and are never added
    to source: file names, disassembly characters and source bytes are not exchangeable.
    """
    calls = model_calls(events)
    session = _Session(built)
    items: list[dict[str, Any]] = []
    for event in events:
        item = attribute(event, built, session)
        if item is not None:
            item["delivered_to_calls"] = sum(1 for c in calls if c > item["ordinal"])
            item["delivered_bytes"] = item["bytes"] * item["delivered_to_calls"]
            item["delivered_source_bytes"] = item["source_bytes"] * item["delivered_to_calls"]
            items.append(item)

    by_class = {name: {"unique_bytes": 0, "delivered_bytes": 0, "items": 0}
                for name in PROVENANCE + (_lineage.IMPLEMENTATION_METADATA, _lineage.UNRESOLVED)}
    by_route: dict[str, dict[str, int]] = {}
    seen: set[tuple[str, str]] = set()
    for item in items:
        bucket = by_class.setdefault(item["origin"],
                                     {"unique_bytes": 0, "delivered_bytes": 0, "items": 0})
        bucket["items"] += 1
        bucket["delivered_bytes"] += item["delivered_bytes"]
        key = (item["origin"], item["sha256"])
        if key not in seen:
            seen.add(key)
            bucket["unique_bytes"] += item["bytes"]
        route = by_route.setdefault(item["route"], {"items": 0, "unique_bytes": 0})
        route["items"] += 1

    route_seen: dict[str, set[str]] = {}
    for item in items:
        got = route_seen.setdefault(item["route"], set())
        if item["sha256"] not in got:
            got.add(item["sha256"])
            by_route[item["route"]]["unique_bytes"] += item["bytes"]

    # Direct implementation source, counted once per distinct set of source lines however delivered.
    source_seen: set[str] = set()
    source_unique = 0
    source_delivered = 0
    source_routes: dict[str, int] = {}
    replays = 0
    for item in items:
        if not item["source_bytes"]:
            continue
        source_delivered += item["delivered_source_bytes"]
        source_routes[item["route"]] = source_routes.get(item["route"], 0) + item["source_bytes"]
        if item["source_identity"] in source_seen:
            replays += 1
            continue
        source_seen.add(item["source_identity"])
        source_unique += item["source_bytes"]

    metadata_seen: set[str] = set()
    metadata_names: set[str] = set()
    metadata_refs = 0
    for item in items:
        if not item["metadata_bytes"]:
            continue
        metadata_refs += 1
        metadata_names.update(item["metadata_names"])
        metadata_seen.add(item["sha256"])

    disclosure_bytes = 0
    disclosed: set[str] = set()
    disclosure_seen: set[str] = set()
    for item in items:
        if item["internal_names"]:
            disclosed.update(item["internal_names"])
            if item["sha256"] not in disclosure_seen:
                disclosure_seen.add(item["sha256"])
                disclosure_bytes += item["bytes"]

    # Source-shaped text that did not come from source. Counted in its own channel and never added
    # to the primary measurand: an agent that rebuilds the interior it was not allowed to read has
    # produced a treatment outcome, not a boundary failure, and the two must not share a number.
    # Whether the reconstruction followed implementation representation entering the session is a
    # question about observable order, and is answered as such — no claim is made about what the
    # model inferred, only about what it had already been shown.
    first_implementation = next((i["ordinal"] for i in items
                                 if i["origin"] in _lineage.IMPLEMENTATION_ORIGINS), None)
    reconstruction_seen: set[str] = set()
    reconstruction_unique = 0
    reconstruction_delivered = 0
    reconstruction_after = 0
    reconstruction_origins: dict[str, int] = {}
    for item in items:
        if not item["reconstruction_identity"]:
            continue
        reconstruction_delivered += item["reconstruction_bytes"] * item["delivered_to_calls"]
        reconstruction_origins[item["origin"]] = \
            reconstruction_origins.get(item["origin"], 0) + 1
        if first_implementation is not None and item["ordinal"] > first_implementation:
            reconstruction_after += 1
        if item["reconstruction_identity"] in reconstruction_seen:
            continue
        reconstruction_seen.add(item["reconstruction_identity"])
        reconstruction_unique += item["reconstruction_bytes"]

    by_form: dict[str, dict[str, int]] = {}
    for item in items:
        bucket = by_form.setdefault(item["form"], {"items": 0, "bytes": 0})
        bucket["items"] += 1
        bucket["bytes"] += item["bytes"]

    contradictions = []
    for item in items:
        reason = contradiction(item)
        if reason:
            contradictions.append({"ordinal": item["ordinal"], "kind": item["kind"],
                                   "route": item["route"], "origin": item["origin"],
                                   "basis": item["basis"], "form": item["form"],
                                   "bytes": item["bytes"], "reason": reason})

    unresolved = [i for i in items if i["origin"] == _lineage.UNRESOLVED]
    runtime = by_class[IMPLEMENTATION_RUNTIME]
    return {
        "model_calls": len(calls),
        "tokens": token_usage(events),
        "summarised": any(e.get("summary") for e in events),
        "by_provenance": by_class,
        "by_route": dict(sorted(by_route.items())),
        # The primary measurand's quantity, and the routes it arrived by. Replay raises delivered
        # and leaves unique alone, which is the whole point of resolving origin by content.
        "implementation_source": {
            "unique_bytes": source_unique,
            "delivered_bytes": source_delivered,
            "distinct_representations": len(source_seen),
            "replays": replays,
            "by_route": dict(sorted(source_routes.items())),
        },
        "implementation_metadata": {
            "references": metadata_refs,
            "names": sorted(metadata_names),
            "items": len(metadata_seen),
        },
        "source_equivalent_reconstruction": {
            "unique_bytes": reconstruction_unique,
            "delivered_bytes": reconstruction_delivered,
            "items": len(reconstruction_origins) and sum(reconstruction_origins.values()),
            "distinct_representations": len(reconstruction_seen),
            "by_origin": dict(sorted(reconstruction_origins.items())),
            "after_implementation_representation": reconstruction_after,
        },
        "by_form": dict(sorted(by_form.items())),
        "by_basis": dict(sorted(
            (b, sum(1 for i in items if i["basis"] == b)) for b in BASES)),
        "contradictions": contradictions,
        "implementation_source_unique_bytes": source_unique,
        "implementation_runtime_unique_bytes": runtime["unique_bytes"],
        "implementation_derived": {
            "source_unique_bytes": source_unique,
            "runtime_unique_bytes": runtime["unique_bytes"],
            "metadata_references": metadata_refs,
        },
        "disclosure": {
            "unique_bytes": disclosure_bytes,
            "items": sum(1 for i in items if i["internal_names"]),
            "names": sorted(disclosed),
        },
        "unresolved": {
            "items": len(unresolved),
            "bytes": sum(i["bytes"] for i in unresolved),
            "routes": sorted({i["route"] for i in unresolved}),
        },
        "attributed_by_lineage": sum(1 for i in items if i["by_lineage"]),
        "items_carrying_internal_names": sum(1 for i in items if i["internal_names"]),
        "truncated_items": sum(1 for i in items if i["truncated"]),
        "items": items,
    }


def consumed(db: Path, built: dict[str, Any]) -> dict[str, Any]:
    """The ledger for one attempt's recorded session."""
    return ledger(read_transcript(db), built)

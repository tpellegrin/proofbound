#!/usr/bin/env python3
"""Export what an authority-handoff run observed, and check it again after the run is gone.

A run's observations live in places that do not survive it. The session database is in a temporary
directory, the run tree is under a disposable project, and the absolute paths in both are specific
to the machine that made them. `pb-handoff-1` demonstrated the cost: its aggregate arithmetic can
still be checked from retained totals, and its per-call attribution cannot be checked at all,
because the databases were gone before anyone asked.

This module exports a **package**: the evidence bytes, a manifest that says what they are and what
is missing, and enough accounting detail to recompute the mechanical observations later, somewhere
else, with no provider and no network.

Four kinds of claim, kept apart
------------------------------

The whole point is that a package does not collapse into one `verified` flag. Every check declares
which kind it is, and the kinds do not convert into one another:

* `INTEGRITY` — a source record exists and its bytes hash to what was recorded.
* `RECOMPUTE` — a mechanical quantity or relationship, recomputed here from retained inputs and
  compared to what was exported.
* `REPORTED` — an agent or operator stated a semantic judgment. Transcribed, never verified. A
  reported check never returns `ok`; its status is `reported`, because nothing here can confirm it.
* `UNAVAILABLE` — the evidence a check needs is absent, so the claim is open. Not a pass, not a
  failure.

What this is not
----------------

Not an authority layer. A package is a copy of `L3` execution records for evaluation; copying them
does not create the durable `L4` implementation provenance
`freeze-and-binding.md` A6.6 says does not exist. Verification is **read-only and never launches a
model**: it does not admit, authorize, bind, or touch project state, and replaying a task recorded
under `C1` must not re-ask whether `C1` is current today.

Not a universal runner, an event-sourcing platform, or a second ledger. One manifest, the formats
the workflow already writes, and the accounting module the live guard already uses.

Relocation
----------

A package is relocatable. Evidence bytes are copied unchanged and the identities recorded inside
them — absolute paths, session ids, run roots — are **never rewritten**, because rewriting the
subject of a record to make a checker happy is how evidence stops being evidence. Instead the
manifest records the original roots, the package stores files under relative paths, and
verification resolves through that mapping.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "evals"))

FORMAT = "proofbound-evidence-package-v1"
MANIFEST = "manifest.json"
FILES_DIR = "files"
EVENTS = "usage-events.json"

#: This exporter's own identity. A package produced by a different adapter version may have
#: collected different things, so the reader records what produced it rather than assuming.
ADAPTER = "authority-slice-handoff-v1"

# -- the four kinds --------------------------------------------------------------------------
INTEGRITY = "integrity"
RECOMPUTE = "recompute"
REPORTED = "reported"
UNAVAILABLE = "unavailable"

OK = "ok"
MISMATCH = "mismatch"
#: The claim's subject was never observed at all. An untouched run did not "refuse"; it did
#: nothing, and those are different results. Kept apart from `unavailable`, which says the event
#: may have happened and the evidence for it is missing.
NOT_OBSERVED = "not-observed"


#: Exactly the session columns an accounting recomputation needs. Everything else in an OpenCode
#: session — prompt text, tool arguments, tool output, file contents the agent read — stays out of
#: a package by construction rather than by redaction, because a redactor that must be remembered
#: is one that will eventually be forgotten. Retaining usage must not require publishing the
#: transcript that produced it. The list is production's (`scripts/_usage_events.py`): a package
#: declares exactly the fields the reader it uses retains, never a second copy that can drift.


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check(cid: str, kind: str, status: str, detail: str, **extra: Any) -> dict[str, Any]:
    """One declared observation about a package.

    `kind` says what sort of claim it is and `status` says how it came out. A `REPORTED` check is
    forced to `reported`: a semantic judgment cannot be confirmed here, and letting one report `ok`
    is precisely the flattening this module exists to prevent.
    """
    if kind == REPORTED:
        status = REPORTED
    return {"id": cid, "kind": kind, "status": status, "detail": detail, **extra}


# -- reading a session, within the allowlist ---------------------------------------------------

# Shared with the supported operator path; historical reader predicates are unchanged.
sys.path.insert(0, str(ROOT / "scripts"))
from _usage_events import EVENT_ALLOWLIST, events_from_db, usage_from_rows


def attribution(rows: list[dict[str, Any]], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    """Which attempt spent what — established against the sessions actually retained.

    Naming a session is a claim, not a resolution. An attempt whose terminal record cites
    `ses_missing` against a trace holding only `ses_actual` used to attribute cleanly, because the
    identifier was nonempty and nothing looked it up.

    Equal aggregate start and finish counts say the totals balance. They say nothing about which
    attempt a call belongs to — an inference `pb-authority-demo-2`'s audit already caught being
    made once — and nothing about whether the same calls finished.
    """
    sessions = sorted({r["session_id"] for r in rows if r.get("session_id")})
    present = set(sessions)
    resolved: dict[str, str] = {}
    problems: list[dict[str, Any]] = []
    for attempt in attempts:
        event = attempt.get("event_dir")
        claimed = attempt.get("attributed_session") or attempt.get("session_id")
        if not claimed:
            problems.append({"event_dir": event,
                             "why": "the attempt records no session identifier"})
            continue
        if str(claimed) not in present:
            problems.append({"event_dir": event,
                             "why": f"names session {claimed!r}, absent from the retained trace"})
            continue
        resolved[str(event)] = str(claimed)

    claimed_by: dict[str, list[str]] = {}
    for event, sid in resolved.items():
        claimed_by.setdefault(sid, []).append(event)
    reused = {sid: dirs for sid, dirs in claimed_by.items() if len(dirs) > 1}
    unaccounted = sorted(present - set(claimed_by))
    established = bool(attempts) and not problems and not reused and not unaccounted
    reasons = []
    if problems:
        reasons.append(f"{len(problems)} attempt(s) resolve to no retained session")
    if reused:
        reasons.append(f"session(s) claimed by more than one attempt: {sorted(reused)}")
    if unaccounted:
        reasons.append(f"retained session(s) no attempt claims: {unaccounted}")
    if not attempts:
        reasons.append("no attempt was attributable to this run")
    return {
        "sessions_in_package": sessions,
        "attempts": len(attempts),
        "resolved": resolved,
        "unresolved": problems,
        "sessions_claimed_twice": reused,
        "sessions_no_attempt_claims": unaccounted,
        "per_attempt_attribution_established": established,
        "why": ("every attempt resolves to exactly one retained session and every retained "
                "session is claimed" if established else
                "; ".join(reasons) + "; aggregate totals remain usable, per-attempt attribution "
                "does not follow from them"),
    }


# -- what a package collects -------------------------------------------------------------------

#: Files copied from a run, by role. The role travels with the file so a reader does not have to
#: infer meaning from a path that was only ever meaningful on the machine that made it.
#: Files copied from a run, by role, and whether their absence is a collection defect. A file
#: marked required and not found becomes an omission naming the checks it blocks; an optional one
#: is simply absent, because not every condition produces one.
COLLECT = (
    ("state.json", "authority-state", True),
    ("launch-ledger.json", "launch-ledger", True),
    ("run-config.json", "run-configuration", True),
    ("frozen-identities.json", "frozen-identities", True),
    ("baseline-manifest.json", "baseline-manifest", False),
    ("final-account.json", "final-account", False),
    ("artifact-check.json", "artifact-check", False),
    ("runtime.json", "runtime", False),
    ("coordinator-input.md", "coordinator-input", False),
    ("coordinator-report.md", "coordinator-report", False),
)

#: What a missing required file costs, named at export so a reader never has to guess.
REQUIRED_BLOCKS = {
    "state.json": ["authority.binding", "authority.admission", "decision.acceptance"],
    "launch-ledger.json": ["launch.ledger-agreement"],
    "run-config.json": ["price.recompute", "identity.configured"],
    "frozen-identities.json": ["identity.frozen"],
}

#: Per-attempt files. `report.md` is the worker's own prose and is retained because a semantic
#: judgment has to be *readable* to be reported at all — but it is labelled `REPORTED`, never
#: checked.
ATTEMPT_FILES = ("attempt.json", "terminal.json", "launch-reservation.json",
                 "evidence-gate.json", "scope-baseline.json", "scope-diff.json", "report.md")


class PreservationFailure(RuntimeError):
    """Evidence collection failed. Visible, never swallowed, never a reason to erase an attempt."""


#: Names and path segments that must never enter a package. The constructed runtime stages the
#: executor's credential into its own home, and a package is a thing people copy around; a guard
#: that fails loudly costs nothing and does not have to be remembered.
CREDENTIAL_NAMES = ("auth.json", "credentials.json", ".netrc", "id_rsa")
CREDENTIAL_SEGMENTS = (".local/share/opencode", ".ssh", ".aws", ".config/gh")


def _refuse_credentials(source: Path) -> None:
    text = source.as_posix()
    if source.name in CREDENTIAL_NAMES or any(seg in text for seg in CREDENTIAL_SEGMENTS):
        raise PreservationFailure(
            f"refusing to place {source} in an evidence package: it is a credential or sits in a "
            f"credential location. Evidence is shareable; this is not.")


def _copy(source: Path, package: Path, rel: str, role: str,
          files: list[dict[str, Any]]) -> None:
    _refuse_credentials(source)
    target = package / FILES_DIR / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    files.append({"path": rel, "role": role, "source": str(source),
                  "sha256": sha256_file(source), "bytes": source.stat().st_size})


def export(*, run_root: Path, into: Path, experiment: str, condition: str,
           session_db: Path | None = None, project: Path | None = None,
           config: dict[str, Any] | None = None, artifact: Path | None = None,
           requirements: Path | None = None, extra: dict[str, Any] | None = None,
           event_dirs: list[str] | None = None, refusal: Path | None = None,
           workdir: Path | None = None) -> dict[str, Any]:
    """Collect one condition's evidence into a relocatable package.

    Called while the run's data is still there. A missing optional input is **recorded as omitted
    with the checks it blocks**, never quietly skipped: the difference between "this run spent
    nothing" and "nobody kept the record of what it spent" is the difference `pb-handoff-1` lost.
    """
    import _guard

    run_root, into = Path(run_root), Path(into)
    if not run_root.is_dir():
        raise PreservationFailure(f"no run tree to preserve at {run_root}")
    into.mkdir(parents=True, exist_ok=True)

    files: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []

    # Where preparation actually writes. `run-config.json`, `launch-ledger.json` and
    # `frozen-identities.json` live at the **workdir**, four levels above the run root, and
    # searching only the run root and its parent silently retained none of them — a package
    # missing its own identities and ledger, with nothing saying so.
    bases: list[Path] = []
    for base in (workdir, run_root, run_root.parent,
                 Path(config["paths"]["project"]).parent if config and config.get("paths", {}).get(
                     "project") else None):
        if base is not None and Path(base).is_dir() and Path(base) not in bases:
            bases.append(Path(base))
    # A file the configuration names explicitly is fetched from where the configuration says it
    # is. Inside a constructed runtime the frozen identities are written *outside* the workdir on
    # purpose — they are controller-side evidence — so searching directories alone never finds
    # them, and the package silently loses the record of what the run was frozen against.
    named = {"frozen-identities.json": config.get("identities") if config else None}
    for name, role, required in COLLECT:
        explicit = named.get(name)
        if explicit and Path(explicit).is_file():
            _copy(Path(explicit), into, f"run/{name}", role, files)
            continue
        for base in bases:
            candidate = base / name
            if candidate.is_file():
                _copy(candidate, into, f"run/{name}", role, files)
                break
        else:
            if required:
                omitted.append({
                    "what": name,
                    "why": (f"not found at {explicit}" if explicit
                            else f"not found under {[str(b) for b in bases]}"),
                    "blocks": REQUIRED_BLOCKS.get(name, [])})

    # Seeded and live attempts share one run tree, and conflating them would charge this run for
    # work no provider ever did. `event_dirs` names the launches this run's ledger reserved; the
    # rest were produced by a stand-in before the coordinator arrived. Both are retained; only
    # attribution separates them.
    facts = _guard.launch_facts(run_root, event_dirs)
    everything = _guard.launch_facts(run_root)
    seeded = [a["event_dir"] for a in everything["attempts"]
              if event_dirs is not None and a["event_dir"] not in event_dirs]
    for attempt in everything["attempts"]:
        event = Path(attempt.get("path") or (run_root / "attempts" / attempt["event_dir"]))
        for name in ATTEMPT_FILES:
            source = event / name
            if source.is_file():
                _copy(source, into, f"run/attempts/{event.name}/{name}",
                      f"attempt-{name.split('.')[0]}", files)

    for name in sorted(p.name for p in (run_root / "contracts").glob("*.md")) if (
            run_root / "contracts").is_dir() else []:
        _copy(run_root / "contracts" / name, into, f"run/contracts/{name}", "task-contract", files)

    if project is not None and Path(project).is_dir():
        for name in ("goal.md", "requirements.md", "change-graph.json"):
            source = Path(project) / name
            if source.is_file():
                _copy(source, into, f"project/{name}", "project-authority", files)
    if artifact is not None and Path(artifact).is_file():
        _copy(Path(artifact), into, f"delivered/{Path(artifact).name}", "delivered-artifact", files)
    elif artifact is not None:
        omitted.append({"what": "the delivered artifact", "why": "no artifact was produced",
                        "blocks": ["artifact.recheck"]})
    if requirements is not None and Path(requirements).is_file():
        _copy(Path(requirements), into, "delivered/accepted-requirements.md",
              "checker-requirements", files)
    if refusal is not None and Path(refusal).is_file():
        _copy(Path(refusal), into, "run/authorization-refusal.json",
              "authorization-refusal", files)
    elif refusal is not None:
        omitted.append({"what": "the authorization refusal record",
                        "why": f"no record at {refusal}",
                        "blocks": ["control.refusal"]})

    events: dict[str, Any] = {"available": False, "rows": [], "anomalies": []}
    if session_db is not None:
        events = events_from_db(Path(session_db))
        if events["available"]:
            payload = {"format": "proofbound-evidence-usage-v1", "allowlist": list(EVENT_ALLOWLIST),
                       "source": str(session_db), "rows": events["rows"],
                       "anomalies": events["anomalies"], "sessions": events.get("sessions", [])}
            raw = json.dumps(payload, indent=2, sort_keys=True).encode()
            (into / EVENTS).write_bytes(raw)
            files.append({"path": EVENTS, "role": "usage-events", "source": str(session_db),
                          "sha256": sha256_bytes(raw), "bytes": len(raw),
                          "note": "allowlisted accounting fields only; no prompts, tool arguments "
                                  "or tool output"})
        else:
            omitted.append({"what": "per-call usage events", "why": events["reason"],
                            "blocks": ["usage.recompute", "price.recompute",
                                       "usage.attribution"]})
    else:
        omitted.append({"what": "per-call usage events",
                        "why": "no session database was supplied to the exporter",
                        "blocks": ["usage.recompute", "price.recompute", "usage.attribution"]})

    spend = None
    billing = None
    if config and config.get("worker_profile"):
        # A run recorded under a worker profile is priced on its own basis, never on the
        # historical DeepSeek default a profile-less caller gets.
        import _worker_profiles
        billing = _worker_profiles.of(config)["billing"]
    if session_db is not None and Path(session_db).is_file():
        spend = (_guard.spend(run_root, session_db, event_dirs=event_dirs, billing=billing)
                 if billing else _guard.spend(run_root, session_db, event_dirs=event_dirs))
    observed = {}
    if events["available"]:
        import _profile
        observed = _profile.observed_identity(
            [{"model": r.get("model"), "provider": r.get("provider"), "variant": r.get("variant")}
             for r in events["rows"]])

    manifest = {
        "format": FORMAT,
        "experiment": experiment,
        "condition": condition,
        "exported_at": _now(),
        "producer": {
            "adapter": ADAPTER,
            "harness_revision": _harness_revision(),
            "interpreter": f"{sys.version_info.major}.{sys.version_info.minor}."
                           f"{sys.version_info.micro}",
        },
        # Recorded, never rewritten. Verification maps these to wherever the package now sits.
        "subject": {
            "run_root": str(run_root),
            "project": str(project) if project else None,
            "session_db": str(session_db) if session_db else None,
        },
        "identity": {
            "configured": _configured_identity(config),
            "observed": observed or {"note": "no session events were retained, so the identity "
                                             "the provider returned cannot be compared"},
        },
        "launch_facts": facts,
        "attempts_in_tree": everything,
        "attribution_scope": {
            "own_attempts": [a["event_dir"] for a in facts["attempts"]],
            "seeded_attempts": seeded,
            "note": ("attempts this run's ledger reserved are its own; the rest were produced by a "
                     "stand-in before the coordinator arrived and are retained without being "
                     "attributed to it")
            if event_dirs is not None else
            ("no ledger scope was supplied, so every attempt in the tree is reported without a "
             "seeded/live distinction"),
        },
        "usage": usage_from_rows(events["rows"]) if events["available"] else None,
        "usage_anomalies": events["anomalies"],
        "attribution": attribution(events["rows"], facts["attempts"]) if events["available"] else {
            "per_attempt_attribution_established": False,
            "why": "no usage events were retained"},
        "spend": spend,
        "pricing_basis": _pricing_basis(billing),
        "files": sorted(files, key=lambda f: f["path"]),
        "omitted": omitted,
        "extra": extra or {},
    }
    raw = json.dumps(manifest, indent=2, sort_keys=True).encode()
    (into / MANIFEST).write_bytes(raw)
    return {"package": str(into), "files": len(files), "omitted": len(omitted),
            "manifest_sha256": sha256_bytes(raw)}


def _harness_revision() -> dict[str, Any]:
    import subprocess
    try:
        done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                              capture_output=True, check=False)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True,
                               capture_output=True, check=False)
        return {"commit": done.stdout.strip() or None, "clean": not dirty.stdout.strip()}
    except OSError:                                            # pragma: no cover
        return {"commit": None, "clean": None}


def _configured_identity(config: dict[str, Any] | None) -> dict[str, Any]:
    """What was asked for, kept separate from what was observed.

    A requested model name is often an alias that moves, so the two are never merged. Tool and
    plugin configuration is recorded only where the run actually recorded it: an executor version
    string does not imply a tool surface, and inventing one would be a claim about capability that
    nothing measured.
    """
    if not config:
        return {"note": "no run configuration was supplied to the exporter"}
    return {
        "model": config.get("model"), "variant": config.get("variant"),
        "worker_profile": config.get("worker_profile"),
        "mode": config.get("mode"),
        "executor": config.get("executor"),
        "interpreter": config.get("interpreter"),
        "policy": config.get("policy"),
        "deadline": config.get("deadline"),
        "tool_configuration": config.get("tool_configuration",
                                         "not recorded by this run; not inferable from the "
                                         "executor version"),
    }


def _pricing_basis(billing: "dict[str, Any] | None" = None) -> dict[str, Any]:
    import _pricing
    if billing and billing.get("basis") != "dated-table":
        return {"table": None, "billing": billing,
                "note": "this worker has no external API bill; no price is derived, and local "
                        "compute cost is unknown rather than zero"}
    # A run recorded under a profile names its own table and price model; one recorded before
    # profiles is priced, as it always was, at the first retained table.
    table = (_pricing.TABLES.get(billing.get("table")) if billing else None) \
        or _pricing.DEEPSEEK_2026_09_09
    basis = {"table": table.get("id"),
             "note": "derived cost is measured usage priced at this dated table; it is neither the "
                     "executor's own cost field nor provider-confirmed billing"}
    if billing and billing.get("price_model"):
        basis["price_model"] = billing["price_model"]
    return basis


# -- verification: read-only, offline, never launches a model -----------------------------------

def load(package: Path) -> dict[str, Any]:
    package = Path(package)
    raw = package / MANIFEST
    if not raw.is_file():
        raise PreservationFailure(f"no {MANIFEST} in {package}")
    manifest = json.loads(raw.read_text(encoding="utf-8"))
    if manifest.get("format") != FORMAT:
        raise PreservationFailure(f"unsupported package format: {manifest.get('format')!r}")
    return manifest


def _resolve(package: Path, rel: str) -> Path:
    """Where a recorded file now lives. The record keeps its original path; this is the mapping."""
    return Path(package) / FILES_DIR / rel if rel != EVENTS else Path(package) / EVENTS


def _blocked(manifest: dict[str, Any], check_id: str) -> str | None:
    for entry in manifest.get("omitted") or []:
        if check_id in (entry.get("blocks") or []):
            return f"{entry.get('what')}: {entry.get('why')}"
    return None


def verify(package: Path, *, recheck_artifact: bool = False,
           timeout: float = 5.0) -> dict[str, Any]:
    """Every supported check, each declaring its kind.

    Read-only by construction: it opens files, hashes bytes and does arithmetic. It never admits,
    authorizes, binds, writes to a run tree, or asks whether a historical candidate is current
    today — a `C1` task replayed under a `C2` project is still a `C1` task
    (`freeze-and-binding.md` A6.4), and re-asking would be the bug, not the check.

    `recheck_artifact` runs the bounded external checker over the retained artifact bytes. It is
    off by default because inspecting a package must never execute code the package carries.
    """
    package = Path(package)
    manifest = load(package)
    checks: list[dict[str, Any]] = []

    checks.extend(_check_files(package, manifest))
    checks.extend(_check_launch(package, manifest))
    checks.extend(_check_usage(package, manifest))
    checks.extend(_check_authority(package, manifest))
    checks.extend(_check_artifact(package, manifest, recheck=recheck_artifact, timeout=timeout))
    checks.extend(_check_refusal(package, manifest))
    checks.extend(_check_reported(package, manifest))
    checks.extend(_check_coverage(package, manifest))

    counts: dict[str, int] = {}
    for entry in checks:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    return {
        "package": str(package),
        "experiment": manifest.get("experiment"),
        "condition": manifest.get("condition"),
        "produced_by": manifest.get("producer"),
        "relocated": str(package) != str(
            Path(manifest.get("subject", {}).get("run_root") or "")),
        "checks": checks,
        "counts": counts,
        # No aggregate verdict. A package whose integrity holds and whose usage is unavailable is
        # not "partially verified"; it is two different facts, and the caller must read both.
        "note": "each check declares its kind; integrity, recomputation, report and unavailability "
                "do not combine into a single verdict",
    }


def _check_files(package: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    missing, changed = [], []
    for entry in manifest.get("files") or []:
        path = _resolve(package, entry["path"])
        if not path.is_file():
            missing.append(entry["path"])
            continue
        if sha256_file(path) != entry["sha256"]:
            changed.append(entry["path"])
    total = len(manifest.get("files") or [])
    if missing or changed:
        out.append(check("files.integrity", INTEGRITY, MISMATCH,
                         f"{len(missing)} missing, {len(changed)} altered of {total}",
                         missing=missing, altered=changed))
    else:
        out.append(check("files.integrity", INTEGRITY, OK,
                         f"all {total} recorded files present, digests match"))
    return out


def _check_launch(package: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Recompute the attempt inventory from the retained run tree."""
    out = []
    import _guard

    staged = package / FILES_DIR / "run"
    if not staged.is_dir():
        return [check("launch.attempts", UNAVAILABLE, UNAVAILABLE,
                      "no run tree was retained in this package")]
    recomputed = _guard.launch_facts(staged)
    exported = manifest.get("attempts_in_tree") or manifest.get("launch_facts") or {}
    scope = manifest.get("attribution_scope") or {}
    own, seeded = scope.get("own_attempts"), scope.get("seeded_attempts") or []
    got, expected = recomputed.get("launched"), exported.get("launched")
    if got != expected:
        out.append(check("launch.attempts", RECOMPUTE, MISMATCH,
                         f"manifest records {expected} attempt(s) in the tree; the retained tree "
                         f"yields {got}"))
    elif own is None:
        out.append(check("launch.attempts", RECOMPUTE, OK,
                         f"{got} attempt(s) in the retained tree; the package draws no seeded/live "
                         f"distinction, so none is asserted here",
                         attempts=[a["event_dir"] for a in recomputed["attempts"]]))
    else:
        out.append(check("launch.attempts", RECOMPUTE, OK,
                         f"{len(own)} launch(es) attributable to this run, {len(seeded)} seeded by "
                         f"a stand-in beforehand, {got} retained in total",
                         own=own, seeded=seeded))

    considered = [a for a in recomputed["attempts"]
                  if own is None or a["event_dir"] in own]
    reserved = [a["event_dir"] for a in considered if a.get("reservation")]
    terminal = [a["event_dir"] for a in considered if a.get("terminal_present")]
    incomplete = sorted({a["event_dir"] for a in considered} - set(terminal))
    if incomplete:
        out.append(check("launch.lifecycle", RECOMPUTE, UNAVAILABLE,
                         f"attempt(s) with no terminal record remain incomplete: {incomplete}",
                         incomplete=incomplete))
    elif not considered:
        # An absence is not an act. This run launched nothing, and whether that is a refusal, a
        # crash before the first command, or a coordinator that never started is decided by
        # `control.refusal` against a retained refusal record — not by this check.
        out.append(check("launch.lifecycle", RECOMPUTE, NOT_OBSERVED,
                         "this run launched no worker of its own; what that means is not "
                         "established here — see control.refusal"))
    else:
        out.append(check("launch.lifecycle", RECOMPUTE, OK,
                         f"every attempt this run launched has a terminal record ({len(terminal)})"))
    out.append(check("launch.reservations", RECOMPUTE, OK,
                     f"{len(reserved)} of {len(considered)} attempt(s) reserved a slot before the "
                     f"executor was reached", reserved=reserved))
    out.append(_check_ledger_agreement(package, manifest, recomputed))
    return out


def _check_ledger_agreement(package: Path, manifest: dict[str, Any],
                            recomputed: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the owned attempt set from the retained ledger and reconcile it with the tree.

    The manifest supplies a membership list; taking it at face value would mean a package whose
    scope was miscomputed at export is never contradicted. The ledger is the durable record of what
    this run reserved, so the set is rebuilt from it and compared against what the tree actually
    holds. Equal counts are not the relationship: which directories, and in which state.
    """
    ledger_path = _resolve(package, "run/launch-ledger.json")
    if not ledger_path.is_file():
        return check("launch.ledger-agreement", UNAVAILABLE, UNAVAILABLE,
                     "no launch ledger was retained, so the owned attempt set cannot be rebuilt")
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return check("launch.ledger-agreement", INTEGRITY, MISMATCH,
                     f"the retained launch ledger is unreadable: {exc}")
    slots = ledger.get("slots") or []
    from_ledger = {Path(str(s.get("event_dir"))).name for s in slots if s.get("event_dir")}
    reserved_but_unclassified = [s.get("slot") for s in slots
                                 if s.get("classification") in (None, "unresolved")]
    pre_executor = {Path(str(s.get("event_dir"))).name for s in slots
                    if s.get("classification") == "pre-executor-failure" and s.get("event_dir")}
    declared = set((manifest.get("attribution_scope") or {}).get("own_attempts") or [])
    in_tree = {a["event_dir"] for a in recomputed["attempts"]}

    problems = []
    if from_ledger != declared:
        problems.append(f"the ledger reserved {sorted(from_ledger)} but the package declares "
                        f"{sorted(declared)} as its own")
    missing_from_tree = sorted(from_ledger - in_tree - pre_executor)
    if missing_from_tree:
        problems.append(f"the ledger reserved slots whose attempt directories are not in the "
                        f"retained tree: {missing_from_tree}")
    if reserved_but_unclassified:
        problems.append(f"slot(s) reserved and never classified: {reserved_but_unclassified}")
    if problems:
        return check("launch.ledger-agreement", RECOMPUTE, MISMATCH, "; ".join(problems))
    return check("launch.ledger-agreement", RECOMPUTE, OK,
                 f"the retained ledger's {len(from_ledger)} reserved slot(s) reconcile with the "
                 f"retained tree; {len(pre_executor)} pre-executor failure(s), "
                 f"{len(in_tree - from_ledger)} seeded attempt(s) not attributed to this run",
                 reserved=sorted(from_ledger), pre_executor_failures=sorted(pre_executor))


def _check_usage(package: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    blocked = _blocked(manifest, "usage.recompute")
    events_path = package / EVENTS
    if blocked and not events_path.is_file():
        out.append(check("usage.recompute", UNAVAILABLE, UNAVAILABLE, blocked))
        # Totals without the events they were summed from still support the *arithmetic*. The
        # price can be re-derived independently; which call spent what cannot. Collapsing those
        # two into one unavailable would discard a check that genuinely works, and reporting the
        # price as recomputed from events would claim evidence that is gone.
        totals = manifest.get("usage")
        if manifest.get("usage_source") == "retained-totals" and isinstance(totals, dict):
            out.append(_recompute_price(manifest, totals))
        else:
            out.append(check("price.recompute", UNAVAILABLE, UNAVAILABLE, blocked))
        attrib = manifest.get("attribution") or {}
        out.append(check("usage.attribution", UNAVAILABLE, UNAVAILABLE,
                         attrib.get("why") or blocked))
        return out
    if not events_path.is_file():
        for cid in ("usage.recompute", "price.recompute", "usage.attribution"):
            out.append(check(cid, UNAVAILABLE, UNAVAILABLE,
                             "the package declares usage events it does not contain"))
        return out

    payload = json.loads(events_path.read_text(encoding="utf-8"))
    rows = payload.get("rows") or []
    anomalies = payload.get("anomalies") or []
    recomputed = usage_from_rows(rows)
    exported = manifest.get("usage") or {}
    differing = {k: (exported.get(k), v) for k, v in recomputed.items() if exported.get(k) != v}
    if differing:
        out.append(check("usage.recompute", RECOMPUTE, MISMATCH,
                         f"{len(differing)} usage field(s) differ from the manifest",
                         fields=sorted(differing)))
    else:
        out.append(check("usage.recompute", RECOMPUTE, OK,
                         f"usage recomputed from {len(rows)} retained event(s) matches the "
                         f"manifest", usage=recomputed))

    import _profile

    started, finished = recomputed.get("calls_started"), recomputed.get("calls_finished")
    reconciliation = _profile.call_reconciliation(
        [{"ordinal": i, "session_id": r.get("session_id"), "message_id": r.get("message_id"),
          "part": {"type": r.get("type")}} for i, r in enumerate(rows)])
    if isinstance(started, int) and isinstance(finished, int) and started != finished:
        out.append(check("usage.completeness", RECOMPUTE, UNAVAILABLE,
                         f"{started - finished} call(s) started and did not finish; their usage is "
                         f"unknown, not zero"))
    elif not reconciliation["reconciled"]:
        # The totals balance and the calls do not. Reporting this as complete is how a session
        # carrying an interrupted call plus a stray finish passes for a settled one.
        out.append(check("usage.completeness", RECOMPUTE, UNAVAILABLE,
                         f"totals balance at {started}, but "
                         f"{len(reconciliation['unmatched_messages'])} message(s) carry unequal "
                         f"starts and finishes; equal totals do not establish that the same calls "
                         f"finished", unmatched=reconciliation["unmatched_messages"]))
    elif anomalies:
        out.append(check("usage.completeness", RECOMPUTE, UNAVAILABLE,
                         f"{len(anomalies)} anomalous row(s) recorded at export; totals are a "
                         f"lower bound, not a settled figure",
                         anomalies=sorted({a["kind"] for a in anomalies})))
    else:
        out.append(check("usage.completeness", RECOMPUTE, OK,
                         f"{started} call(s) started and {finished} finished, reconciled across "
                         f"{reconciliation['messages']} message(s), no anomalies"))

    out.append(_recompute_price(manifest, recomputed, rows=rows))
    out.append(_recompute_attribution(package, manifest, rows))
    return out


def _recompute_attribution(package: Path, manifest: dict[str, Any],
                           rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Re-derive per-attempt attribution from the retained records, not from the manifest.

    The manifest's own conclusion is an assertion by whatever produced the package. Reading it back
    as a check would mean an exporter that decided wrongly — or a hand-edited boolean — is never
    contradicted. So the attempts are re-read from their retained terminal records and resolved
    against the sessions the retained trace actually contains.
    """
    staged = package / FILES_DIR / "run"
    scope = manifest.get("attribution_scope") or {}
    own = scope.get("own_attempts")
    attempts: list[dict[str, Any]] = []
    attempts_dir = staged / "attempts"
    if attempts_dir.is_dir():
        for event in sorted(attempts_dir.iterdir()):
            if not event.is_dir() or (own is not None and event.name not in own):
                continue
            terminal = event / "terminal.json"
            record: dict[str, Any] = {"event_dir": event.name}
            if terminal.is_file():
                try:
                    data = json.loads(terminal.read_text(encoding="utf-8"))
                    record["session_id"] = data.get("session_id")
                    record["title"] = data.get("title")
                except (OSError, ValueError):
                    record["session_id"] = None
            attempts.append(record)

    recomputed = attribution(rows, attempts)
    declared = bool((manifest.get("attribution") or {}).get(
        "per_attempt_attribution_established"))
    if recomputed["per_attempt_attribution_established"] != declared:
        return check("usage.attribution", RECOMPUTE, MISMATCH,
                     f"the manifest declares attribution established={declared}; the retained "
                     f"records give {recomputed['per_attempt_attribution_established']} — "
                     f"{recomputed['why']}", recomputed=recomputed)
    if not recomputed["per_attempt_attribution_established"]:
        return check("usage.attribution", UNAVAILABLE, UNAVAILABLE, recomputed["why"],
                     recomputed=recomputed)
    return check("usage.attribution", RECOMPUTE, OK, recomputed["why"],
                 resolved=recomputed["resolved"])


def _recompute_price(manifest: dict[str, Any], usage: dict[str, Any], *,
                     rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Re-derive cost from retained usage at the *pinned* historical table.

    Pinned deliberately: a later price change must never be able to reinterpret what a historical
    run consumed. The figure is derived from measured usage and is not provider-confirmed billing.
    """
    import _pricing

    spend = manifest.get("spend") or {}
    basis = manifest.get("pricing_basis") or {}
    if "table" in basis and basis["table"] is None:
        return check("price.recompute", UNAVAILABLE, UNAVAILABLE,
                     "no external API billing is configured for this worker; money is not a "
                     "derived quantity here, and its absence is not a zero")
    exported = spend.get("derived")
    config = (manifest.get("identity") or {}).get("configured") or {}
    table = _pricing.TABLES.get(basis.get("table")) or _pricing.DEEPSEEK_2026_09_09
    model = basis.get("price_model") or str(config.get("model") or "").split("/", 1)[-1]
    when = spend.get("priced_at")
    try:
        moment = datetime.fromisoformat(str(when)) if when else None
    except ValueError:
        moment = None
    if (spend.get("cost") or {}).get("method") == _pricing.CALL_PRICING:
        if rows is None:
            return check("price.recompute", UNAVAILABLE, UNAVAILABLE,
                         "timestamp-window pricing requires retained per-call events")
        priced = _pricing.cost_rows(rows, model=model, table=table)
    else:
        priced = _pricing.cost(usage, model=model, when=moment, table=table)
    amount = (priced or {}).get("amount")
    if not isinstance(amount, (int, float)):
        return check("price.recompute", UNAVAILABLE, UNAVAILABLE,
                     "retained usage could not be priced at the pinned table")
    derived = round(float(amount), 6)
    if exported is None:
        return check("price.recompute", RECOMPUTE, UNAVAILABLE,
                     f"recomputes to {derived} at {table['id']}; the "
                     f"package records no figure to compare")
    if abs(derived - float(exported)) > 1e-6:
        return check("price.recompute", RECOMPUTE, MISMATCH,
                     f"package records {exported}; retained usage prices to {derived}")
    source = ("retained aggregate totals" if manifest.get("usage_source") == "retained-totals"
              else "retained per-call events")
    return check("price.recompute", RECOMPUTE, OK,
                 f"{derived} re-derived from {source} at "
                 f"{table['id']}; not provider-confirmed billing",
                 recomputed_from=source, complete=spend.get("complete"))


def _check_authority(package: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """The contract, candidate and admission the run actually bound — recomputed, never re-asked.

    This compares recorded bytes against recorded state. It does **not** ask whether the candidate
    is current now: authority is fixed at admission, and a package replayed after the project moved
    to `C2` describes a `C1` task that was correctly a `C1` task.
    """
    out = []
    state_path = _resolve(package, "run/state.json")
    if not state_path.is_file():
        return [check("authority.binding", UNAVAILABLE, UNAVAILABLE,
                      "no run state was retained")]
    state = json.loads(state_path.read_text(encoding="utf-8"))
    bound: list[dict[str, Any]] = []
    for phase_id, phase in (state.get("phases") or {}).items():
        for task_id, task in (phase.get("tasks") or {}).items():
            current = task.get("current_contract") or {}
            if not current:
                continue
            bound.append({"task": f"{phase_id}/{task_id}", "sha256": current.get("sha256"),
                          "path": current.get("path"), "status": task.get("status"),
                          "admission": task.get("admission")})
    if not bound:
        out.append(check("authority.binding", RECOMPUTE, OK,
                         "no task carried a bound contract; nothing was authorized to run"))
        return out

    mismatched, unresolved = [], []
    for entry in bound:
        name = Path(str(entry["path"])).name
        staged = _resolve(package, f"run/contracts/{name}")
        if not staged.is_file():
            unresolved.append(entry["task"])
            continue
        if sha256_file(staged) != entry["sha256"]:
            mismatched.append(entry["task"])
    if mismatched:
        out.append(check("authority.binding", INTEGRITY, MISMATCH,
                         f"contract bytes do not hash to what state recorded: {mismatched}"))
    elif unresolved:
        out.append(check("authority.binding", INTEGRITY, UNAVAILABLE,
                         f"contract bytes were not retained for {unresolved}"))
    else:
        out.append(check("authority.binding", INTEGRITY, OK,
                         f"{len(bound)} bound contract(s) hash to what run state recorded",
                         tasks=[e["task"] for e in bound]))

    admitted = [e for e in bound if isinstance(e.get("admission"), dict)]
    if not admitted:
        out.append(check("authority.admission", RECOMPUTE, UNAVAILABLE,
                         "no task carries an admission record; this run predates admission "
                         "enforcement, or nothing was candidate-bound execution"))
        return out
    problems = []
    for entry in admitted:
        record = entry["admission"]
        if record.get("contract_sha256") != entry["sha256"]:
            problems.append(f"{entry['task']}: admission names a different contract revision")
        declared = record.get("candidate")
        if not (isinstance(declared, str) and len(declared) == 64):
            problems.append(f"{entry['task']}: admission names no usable candidate")
    if problems:
        out.append(check("authority.admission", RECOMPUTE, MISMATCH, "; ".join(problems)))
    else:
        out.append(check("authority.admission", RECOMPUTE, OK,
                         f"{len(admitted)} admission record(s) name the contract revision actually "
                         f"bound; currentness is deliberately not re-asked (A6.4)",
                         candidates=sorted({e["admission"]["candidate"][:12] for e in admitted})))
    return out


def _check_artifact(package: Path, manifest: dict[str, Any], *, recheck: bool,
                    timeout: float) -> list[dict[str, Any]]:
    """The delivered bytes, and — only on request — a fresh check of them.

    Re-running the checker is a **new check of retained bytes**. It is not evidence that the
    historical check ran, and the two are reported separately. It is opt-in because inspecting a
    package must never execute code the package carries.
    """
    out = []
    artifact = next((f for f in manifest.get("files") or []
                     if f.get("role") == "delivered-artifact"), None)
    recorded = (manifest.get("extra") or {}).get("artifact_check")
    if artifact is None:
        out.append(check("artifact.retained", UNAVAILABLE, UNAVAILABLE,
                         "no delivered artifact was retained"))
        return out
    path = _resolve(package, artifact["path"])
    if not path.is_file():
        out.append(check("artifact.retained", INTEGRITY, MISMATCH,
                         "the manifest records a delivered artifact the package does not contain"))
        return out
    digest = sha256_file(path)
    if digest != artifact["sha256"]:
        out.append(check("artifact.retained", INTEGRITY, MISMATCH,
                         f"delivered artifact bytes changed since export ({artifact['path']})"))
        return out
    out.append(check("artifact.retained", INTEGRITY, OK,
                     f"delivered artifact retained, sha256 {digest[:12]}"))

    if recorded is not None:
        recorded_digest = (recorded or {}).get("artifact_sha256")
        if recorded_digest and recorded_digest != digest:
            out.append(check("artifact.subject", INTEGRITY, MISMATCH,
                             f"the historical check graded {str(recorded_digest)[:12]}; the "
                             f"retained artifact is {digest[:12]}"))
        else:
            out.append(check("artifact.historical-result", REPORTED, REPORTED,
                             f"the run recorded result {(recorded or {}).get('result')!r} for "
                             f"these bytes; that the check ran is reported, not reproduced here"))
    if not recheck:
        out.append(check("artifact.recheck", UNAVAILABLE, UNAVAILABLE,
                         "not requested; pass --recheck-artifact to run the bounded checker over "
                         "the retained bytes"))
        return out

    requirements = next((f for f in manifest.get("files") or []
                         if f.get("role") == "checker-requirements"), None)
    if requirements is None:
        out.append(check("artifact.recheck", UNAVAILABLE, UNAVAILABLE,
                         "the accepted requirements the checker consumed were not retained, so a "
                         "recheck would grade against a different subject"))
        return out
    import _checker
    import _obligations as oracle

    # The model is parsed from the **retained** requirements, which is the entire reason they are
    # in the package. Grading against whatever requirements happen to sit in the harness today
    # would check the delivered bytes against an authority the run never had.
    staged_requirements = _resolve(package, requirements["path"])
    if sha256_file(staged_requirements) != requirements["sha256"]:
        out.append(check("artifact.recheck", INTEGRITY, MISMATCH,
                         "the retained requirements do not hash to what was exported; a recheck "
                         "would grade against a different authority"))
        return out
    try:
        model = oracle.parse_model(staged_requirements.read_text(encoding="utf-8"))
    except Exception as exc:                          # noqa: BLE001 - reported, never raised
        out.append(check("artifact.recheck", UNAVAILABLE, UNAVAILABLE,
                         f"the retained requirements cannot be parsed into a checker model: "
                         f"{type(exc).__name__}: {exc}"))
        return out

    result = _checker.check_delivered(path, model=model, timeout=int(timeout))
    status = result.get("verdict")
    historical = (recorded or {}).get("result") if recorded is not None else None

    # The verdict is the finding. An earlier version reported `ok` whenever there was no historical
    # result to disagree with, so a delivery that fails the accepted requirements passed silently
    # — the check answered "did these two agree?" when the question is "do these bytes work?".
    if status == _checker.CHECKER_ERROR:
        out.append(check("artifact.recheck", UNAVAILABLE, UNAVAILABLE,
                         f"the checker could not reach a verdict over the retained bytes: "
                         f"{result.get('findings')}"))
        return out
    if status != _checker.PASS:
        out.append(check("artifact.recheck", RECOMPUTE, MISMATCH,
                         f"a fresh bounded check of the retained bytes returns {status!r} against "
                         f"the retained accepted requirements",
                         requirements_sha256=requirements["sha256"],
                         findings=result.get("findings")))
        return out
    if historical is not None and historical != status:
        out.append(check("artifact.recheck", RECOMPUTE, MISMATCH,
                         f"a fresh check of the retained bytes returns {status!r}; the run "
                         f"recorded {historical!r}",
                         requirements_sha256=requirements["sha256"]))
        return out
    out.append(check("artifact.recheck", RECOMPUTE, OK,
                     f"a fresh bounded check of the retained bytes returns {status!r} against the "
                     f"retained accepted requirements; this is a new check of those bytes, not "
                     f"evidence that the historical check ran",
                     requirements_sha256=requirements["sha256"]))
    return out


def _check_refusal(package: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Was a request actually refused, or did nothing happen?

    A control condition claims that the mechanism refused. Supporting that needs three things
    together: a **retained refusal record** naming what was requested and why it was refused, the
    **absence of worker execution**, and no replacement permission created to route around it. An
    untouched run supplies only the second, and an untouched run is `not-observed` — it did not
    refuse, it did nothing, and reporting those alike would let a coordinator that crashed before
    its first command pass for a successful negative control.
    """
    record = next((f for f in manifest.get("files") or [] if f.get("role") == "authorization-refusal"),
                  None)
    scope = manifest.get("attribution_scope") or {}
    own = scope.get("own_attempts") or []
    if record is None:
        return [check("control.refusal", NOT_OBSERVED, NOT_OBSERVED,
                      "no refusal record was retained; this package does not distinguish a refused "
                      "request from a run in which nothing was ever requested"
                      + ("" if not own else f", and {len(own)} launch(es) did occur"))]
    path = _resolve(package, record["path"])
    if not path.is_file() or sha256_file(path) != record["sha256"]:
        return [check("control.refusal", INTEGRITY, MISMATCH,
                      "the retained refusal record is missing or its bytes changed")]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [check("control.refusal", INTEGRITY, MISMATCH,
                      f"the retained refusal record is unreadable: {exc}")]

    findings = [f.get("code") for f in (payload.get("findings") or []) if isinstance(f, dict)]
    subject = payload.get("candidate") or payload.get("contract")
    refused = payload.get("admitted") is False or payload.get("authorized") is False
    problems = []
    if not refused:
        problems.append("the retained record does not state a refusal")
    if not findings:
        problems.append("the record names no reason")
    if not subject:
        problems.append("the record names no subject")
    if own:
        problems.append(f"{len(own)} launch(es) are attributed to this run, so execution was not "
                        f"withheld")
    if problems:
        return [check("control.refusal", RECOMPUTE, MISMATCH, "; ".join(problems),
                      findings=findings)]
    return [check("control.refusal", RECOMPUTE, OK,
                  f"a refusal of {str(subject)[:12]} was recorded for {findings}, and no worker "
                  f"execution is attributed to this run",
                  findings=findings, subject=str(subject))]


def _check_reported(package: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Semantic judgments, transcribed and labelled. Never confirmed here."""
    out = []
    for role, cid, what in (
            ("coordinator-report", "decision.coordinator", "the coordinator's account of the run"),
            ("attempt-report", "review.findings", "worker and reviewer reports")):
        # Both are prose. Retained so a reader can attribute a judgment to whoever made it, and
        # labelled REPORTED so nothing mistakes retention for confirmation.
        present = [f for f in manifest.get("files") or [] if f.get("role") == role]
        if not present:
            out.append(check(cid, UNAVAILABLE, UNAVAILABLE, f"{what}: not retained"))
            continue
        out.append(check(cid, REPORTED, REPORTED,
                         f"{len(present)} document(s) state {what}; retained verbatim and "
                         f"attributable, but nothing here confirms the judgment",
                         files=[f["path"] for f in present]))
    state_path = _resolve(package, "run/state.json")
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        accepted = [f"{p}/{t}" for p, phase in (state.get("phases") or {}).items()
                    for t, task in (phase.get("tasks") or {}).items()
                    if task.get("status") == "accepted"]
        out.append(check("decision.acceptance", INTEGRITY, OK,
                         f"{len(accepted)} task(s) recorded as accepted in run state: "
                         f"{accepted or 'none'}; acceptance is a recorded parent act, and refusal "
                         f"is the absence of one", accepted=accepted))
    return out


def _check_coverage(package: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """What the package can say about what the agent actually looked at.

    Deliberately separate constructs: file exposure, complete content delivery, semantic
    inspection, defect detection and reporting accuracy are five different things. A tool call in a
    trace establishes exposure at most. Missing telemetry establishes nothing at all — it cannot
    show that no reading occurred, and efficient targeted investigation is a legitimate workflow.
    """
    events_path = package / EVENTS
    if not events_path.is_file():
        return [check("coverage.tool-exposure", UNAVAILABLE, UNAVAILABLE,
                      "no tool trace was retained; nothing here can state what was read, and that "
                      "is not evidence that nothing was read")]
    payload = json.loads(events_path.read_text(encoding="utf-8"))
    tools = [r for r in payload.get("rows") or [] if r.get("type") == "tool"]
    if not tools:
        return [check("coverage.tool-exposure", UNAVAILABLE, UNAVAILABLE,
                      "the retained trace records no tool activity; absence of telemetry is not "
                      "absence of reading")]
    names: dict[str, int] = {}
    for row in tools:
        names[str(row.get("tool"))] = names.get(str(row.get("tool")), 0) + 1
    return [check("coverage.tool-exposure", RECOMPUTE, OK,
                  f"{len(tools)} tool call(s) retained by name and status; arguments and output "
                  f"are outside the export allowlist, so this bounds *exposure* only and "
                  f"establishes neither complete reading nor understanding", tools=names)]


# -- compatibility: reading evidence that predates packaging -------------------------------------

def adapt_handoff_1(condition_dir: Path, into: Path, *,
                    experiment: str = "pb-handoff-1") -> dict[str, Any]:
    """Build a package from `pb-handoff-1`'s retained evidence.

    A narrow adapter for one historical layout, not a migration. That run was collected by hand
    before packages existed: it kept the run tree, the ledger, the contracts, the reports and the
    final account, and it did **not** keep the session databases or the full worker logs.

    So the package it produces is honestly partial. Aggregate usage was retained as totals, which
    is enough to re-derive the price arithmetic independently; the per-call events those totals
    were summed from are gone, so per-call attribution is unavailable and stays unavailable. The
    missing records are not reconstructed, and the checks that do work are not downgraded because
    other checks cannot.

    The original files are copied, never modified, and the identities recorded inside them —
    including absolute paths on a machine that no longer exists — are left exactly as written.
    """
    import _guard

    condition_dir, into = Path(condition_dir), Path(into)
    if not (condition_dir / "state.json").is_file():
        raise PreservationFailure(
            f"{condition_dir} does not look like a retained pb-handoff-1 condition")
    into.mkdir(parents=True, exist_ok=True)

    files: list[dict[str, Any]] = []
    for name, role in (("state.json", "authority-state"),
                       ("launch-ledger.json", "launch-ledger"),
                       ("run-config.json", "run-configuration"),
                       ("frozen-identities.json", "frozen-identities"),
                       ("baseline-manifest.json", "baseline-manifest"),
                       ("final-account.json", "final-account"),
                       ("artifact-check.json", "artifact-check"),
                       ("runtime.json", "runtime"),
                       ("coordinator-input.md", "coordinator-input"),
                       ("coordinator-report.md", "coordinator-report")):
        source = condition_dir / name
        if source.is_file():
            _copy(source, into, f"run/{name}", role, files)
    for source in sorted((condition_dir / "contracts").glob("*.md")) if (
            condition_dir / "contracts").is_dir() else []:
        _copy(source, into, f"run/contracts/{source.name}", "task-contract", files)
    for source in sorted((condition_dir / "authority").glob("*")) if (
            condition_dir / "authority").is_dir() else []:
        if source.is_file():
            _copy(source, into, f"authority/{source.name}", "project-authority", files)
    for event in sorted((condition_dir / "attempts").iterdir()) if (
            condition_dir / "attempts").is_dir() else []:
        if not event.is_dir():
            continue
        for source in sorted(event.iterdir()):
            if source.is_file():
                role = ("attempt-report" if source.name == "report.md"
                        else f"attempt-{source.stem}")
                _copy(source, into, f"run/attempts/{event.name}/{source.name}", role, files)
    artifact = condition_dir / "dispatch.py"
    if artifact.is_file():
        _copy(artifact, into, "delivered/dispatch.py", "delivered-artifact", files)

    account = {}
    account_path = condition_dir / "final-account.json"
    if account_path.is_file():
        account = json.loads(account_path.read_text(encoding="utf-8"))
    spend = account.get("spend") or {}
    ledger_slots = ((account.get("launches") or {}).get("slots")) or []
    own = [Path(str(s.get("event_dir"))).name for s in ledger_slots if s.get("event_dir")]
    everything = _guard.launch_facts(into / FILES_DIR / "run") if (
        into / FILES_DIR / "run").is_dir() else {"attempts": [], "launched": 0}
    seeded = [a["event_dir"] for a in everything["attempts"] if a["event_dir"] not in own]

    recorded_check = {}
    check_path = condition_dir / "artifact-check.json"
    if check_path.is_file():
        raw = json.loads(check_path.read_text(encoding="utf-8"))
        recorded_check = {
            "result": raw.get("verdict"),
            "artifact_sha256": ((raw.get("artifact_check") or {}).get("artifact") or {}).get(
                "sha256"),
            "note": "as recorded by the run"}

    config = {}
    config_path = condition_dir / "run-config.json"
    if config_path.is_file():
        config = json.loads(config_path.read_text(encoding="utf-8"))

    omitted = [
        {"what": "the session databases",
         "why": "not retained by pb-handoff-1; its temporary workspace was removed after the run",
         "blocks": ["usage.recompute", "usage.attribution", "coverage.tool-exposure"]},
        {"what": "full worker logs",
         "why": "only the tail of each worker log was retained",
         "blocks": ["coverage.tool-exposure"]},
        {"what": "the accepted requirements the artifact checker consumed",
         "why": "not retained as a separate file by this run",
         "blocks": ["artifact.recheck"]},
    ]
    manifest = {
        "format": FORMAT,
        "experiment": experiment,
        "condition": condition_dir.name,
        "exported_at": _now(),
        "producer": {"adapter": f"{ADAPTER}+pb-handoff-1-compat",
                     "harness_revision": _harness_revision(),
                     "note": "built by a narrow compatibility adapter from evidence collected "
                             "before packages existed; the original files are unmodified"},
        "subject": {"run_root": str(condition_dir),
                    "project": None,
                    "session_db": None},
        "identity": {
            "configured": _configured_identity(config),
            "observed": {"note": "no session events were retained, so the identity the provider "
                                 "returned cannot be compared against what was requested"},
        },
        "launch_facts": {"attempts": [a for a in everything["attempts"]
                                      if a["event_dir"] in own], "launched": len(own)},
        "attempts_in_tree": everything,
        "attribution_scope": {"own_attempts": own, "seeded_attempts": seeded,
                              "note": "from the retained launch ledger's own slots"},
        # Totals, not events. The difference is the whole point of this adapter.
        "usage": spend.get("usage"),
        "usage_source": "retained-totals",
        "usage_anomalies": [],
        "attribution": {
            "per_attempt_attribution_established": False,
            "why": "the per-call events these totals were summed from were not retained, so no "
                   "call can be assigned to an attempt; the aggregate remains usable"},
        "spend": spend,
        "pricing_basis": _pricing_basis(),
        "files": sorted(files, key=lambda f: f["path"]),
        "omitted": omitted,
        "extra": {"artifact_check": recorded_check} if recorded_check else {},
    }
    raw = json.dumps(manifest, indent=2, sort_keys=True).encode()
    (into / MANIFEST).write_bytes(raw)
    return {"package": str(into), "files": len(files), "omitted": len(omitted),
            "manifest_sha256": sha256_bytes(raw)}


# -- qualification: did this condition do what it was supposed to do? ----------------------------

#: What each condition must be able to show. Frozen here rather than judged afterwards, because a
#: criterion chosen once results are visible is not a criterion.
REQUIRED_OBSERVATIONS = {
    "control": ("files.integrity", "launch.attempts", "launch.ledger-agreement",
                "control.refusal", "authority.binding"),
    "valid": ("files.integrity", "launch.attempts", "launch.ledger-agreement",
              "launch.lifecycle", "usage.recompute", "usage.completeness", "price.recompute",
              "usage.attribution", "authority.binding", "authority.admission",
              "artifact.retained", "artifact.recheck", "decision.acceptance"),
}

#: Checks whose unavailability is expected and does not fail evidence success. Content-exposure
#: telemetry is the standing example: the export allowlist deliberately keeps tool output out, so
#: `coverage.tool-exposure` bounds exposure at best and is often unavailable by design.
EXPECTED_OMISSIONS = ("coverage.tool-exposure", "artifact.historical-result",
                      "decision.coordinator", "review.findings")


def qualify(package: Path, *, recheck_artifact: bool = True,
            timeout: float = 10.0) -> dict[str, Any]:
    """Three predicates, reported separately. None of them is `verify`'s exit code.

    `verify` returning zero means it found no mismatch. A package consisting entirely of
    `unavailable` also returns zero, and would be worthless. Qualification therefore asks a
    different question — *are the required observations actually available and passing* — and asks
    it per condition, because a control that launched nothing and a valid condition that delivered
    nothing are not the same outcome.

    A completed run can fail qualification and still be a valuable recorded result. That is the
    point of separating them.
    """
    package = Path(package)
    manifest = load(package)
    condition = str(manifest.get("condition") or "")
    report = verify(package, recheck_artifact=recheck_artifact, timeout=timeout)
    by_id = {c["id"]: c for c in report["checks"]}

    required = REQUIRED_OBSERVATIONS.get(condition)
    evidence: dict[str, Any] = {"required": list(required or ()), "missing": [], "failing": [],
                                "expected_omissions": []}
    if required is None:
        evidence["passed"] = False
        evidence["why"] = (f"condition {condition!r} declares no required observations; "
                           f"qualification is defined for {sorted(REQUIRED_OBSERVATIONS)}")
    else:
        for check_id in required:
            entry = by_id.get(check_id)
            if entry is None or entry["status"] in (UNAVAILABLE, NOT_OBSERVED):
                evidence["missing"].append(check_id)
            elif entry["status"] == MISMATCH:
                evidence["failing"].append(check_id)
        evidence["expected_omissions"] = [
            c for c in EXPECTED_OMISSIONS
            if c in by_id and by_id[c]["status"] in (UNAVAILABLE, NOT_OBSERVED)]
        evidence["passed"] = not evidence["missing"] and not evidence["failing"]
        evidence["why"] = ("every required observation is available and passing"
                           if evidence["passed"] else
                           f"missing={evidence['missing']} failing={evidence['failing']}")

    outcome = _condition_outcome(condition, by_id, manifest)
    return {
        "package": str(package),
        "experiment": manifest.get("experiment"),
        "condition": condition,
        "outcome_success": outcome,
        "evidence_success": evidence,
        "qualified": bool(outcome.get("passed") and evidence.get("passed")),
        "counts": report["counts"],
        "note": "outcome and evidence are separate predicates; a completed run that fails either "
                "is still a recorded result, and `verify` exiting zero satisfies neither",
    }


def _condition_outcome(condition: str, by_id: dict[str, Any],
                       manifest: dict[str, Any]) -> dict[str, Any]:
    """Did the condition reach the outcome it was declared to test?"""
    scope = manifest.get("attribution_scope") or {}
    own = scope.get("own_attempts") or []
    reasons: list[str] = []

    if condition == "control":
        refusal = by_id.get("control.refusal") or {}
        if refusal.get("status") != OK:
            reasons.append(f"control.refusal is {refusal.get('status', 'absent')}; a refusal must "
                           f"be recorded, not inferred from an empty run")
        if own:
            reasons.append(f"{len(own)} worker launch(es) are attributed to this run")
        state = manifest.get("attempts_in_tree") or {}
        return {"predicate": "control", "passed": not reasons,
                "why": "; ".join(reasons) or
                       "the mechanism recorded a refusal, its subject and reason, and no worker "
                       "execution is attributed to this run",
                "launches": len(own), "attempts_in_tree": state.get("launched")}

    if condition == "valid":
        for check_id, why in (("authority.admission", "admission did not go through the "
                                                      "supported path"),
                              ("artifact.recheck", "the delivered bytes do not satisfy the "
                                                   "accepted requirements"),
                              ("authority.binding", "the accepted contract does not match what "
                                                    "was bound"),
                              ("decision.acceptance", "no acceptance is recorded")):
            entry = by_id.get(check_id) or {}
            if entry.get("status") != OK:
                reasons.append(f"{check_id} is {entry.get('status', 'absent')}: {why}")
        if len(own) < 2:
            reasons.append(f"{len(own)} launch(es); a valid condition needs at least an "
                           f"implementation and an independent review")
        return {"predicate": "valid", "passed": not reasons,
                "why": "; ".join(reasons) or
                       "authority was recovered and admitted through supported paths, the "
                       "delivered bytes passed the external check against the accepted "
                       "requirements, and acceptance refers to that result",
                "launches": len(own)}

    return {"predicate": condition or "unnamed", "passed": False,
            "why": "no outcome predicate is defined for this condition"}

#!/usr/bin/env python3
"""The guard that decides whether another paid launch is permitted, and records what happened.

Enumerating permitted paths establishes a maximum. It does not enforce one: `pb-authority-demo-2`
enumerated nothing, discovered mid-run that its ceiling omitted a path its own text granted, and
raised the ceiling by the party it benefited. `_launch_paths` derives the number; this module makes
the running experiment obey it.

**A slot is reserved durably before the executor is reached, not after.** The order matters: a
launcher that crashes after spending is indistinguishable from one that never started unless the
intent was written down first. `dsd_attempt.py launch` already writes an immutable
`launch-reservation.json` before worker execution and *removes the whole attempt directory* when no
reservation was created — which is correct for the run tree and destroys exactly the evidence a
"this one was free" claim needs. So the intent, the launcher's own output and the post-hoc state of
the attempt directory are all recorded here, and a pre-executor classification rests on that record
rather than on an assertion.

**Nothing is admitted while the previous slot is unreconciled.** Reconciliation means: the attempt
reached a terminal disposition, its usage is attributable to a session, and the spend figure is
complete. An interrupted call whose cost is unknown leaves the figure incomplete, which is terminal
for the run — the corrected rule from that demonstration's audit, applied prospectively rather than
rediscovered.

**Executor launches and model calls are different quantities.** One launch is one slot against the
ceiling; the same attempt may make dozens of model calls against the budget. Both are reported, and
neither is used as the other.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "evals"))

import _launch_paths                     # noqa: E402

LEDGER_FORMAT = "proofbound-launch-ledger-v1"

#: Frozen resource policy for `pb-handoff-1`. Changing any of these after the first paid attempt
#: invalidates the observation; they are constants here so a mid-run change is a diff, not a flag.
AGGREGATE_LIMIT = 0.30
RESERVE = 0.06
LAUNCH_CEILING = _launch_paths.ceiling()["ceiling"]           # derived, not chosen
MODEL = "deepseek/deepseek-v4-flash"
VARIANT = "high"

#: Classifications a recorded slot can end in.
EXECUTOR_REACHED = "executor-reached"      # a reservation exists; the slot is spent
PRE_EXECUTOR_FAILURE = "pre-executor-failure"   # evidenced: intent recorded, no reservation
UNRESOLVED = "unresolved"                  # recorded intent whose outcome is not yet classified


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# -- what the run tree says --------------------------------------------------------------------

def launch_facts(run_root: "str | Path",
                 event_dirs: "list[str] | None" = None) -> "dict[str, Any]":
    """Attempts the run tree records, independent of any ledger or session database.

    `event_dirs` narrows the inventory to named attempts. The live half of an experiment must
    reconcile *its own* launches: the upstream state is seeded by a fake executor whose attempts sit
    in the same run tree, and pricing those would charge the budget for work no provider ever did.
    Both remain in the tree; only attribution is separated.
    """
    run_root = Path(run_root)
    attempts = []
    for attempt_json in sorted(run_root.rglob("attempt.json")):
        event = attempt_json.parent
        if event_dirs is not None and event.name not in event_dirs:
            continue
        try:
            data = json.loads(attempt_json.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            attempts.append({"event_dir": event.name, "readable": False})
            continue
        terminal: "dict[str, Any]" = {}
        terminal_path = event / "terminal.json"
        if terminal_path.is_file():
            try:
                terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                terminal = {"unreadable": True}
        attempts.append({
            "event_dir": event.name, "readable": True,
            "path": str(event),
            "started_at": data.get("started_at"),
            "reservation": (event / "launch-reservation.json").is_file(),
            "session_id": terminal.get("session_id"),
            "title": terminal.get("title"),
            "terminal_status": terminal.get("status"),
            "terminal_present": bool(terminal),
        })
    return {"attempts": attempts, "launched": len(attempts)}


def _priced_at(facts: "dict[str, Any]") -> datetime:
    stamps = [a.get("started_at") for a in facts["attempts"] if a.get("started_at")]
    for raw in sorted(stamps):
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:                                   # pragma: no cover
            continue
    return datetime.now(tz=timezone.utc)


def _session_by_title(db: Path, title: str) -> "str | None":
    import sqlite3
    from contextlib import closing
    try:
        with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as conn:
            rows = conn.execute("select id from session where title = ?", (title,)).fetchall()
    except sqlite3.Error:
        return None
    return str(rows[0][0]) if len(rows) == 1 else None


def spend(run_root: "str | Path", db: "str | Path", *, model: str = MODEL,
          variant: str = VARIANT, event_dirs: "list[str] | None" = None) -> "dict[str, Any]":
    """What this run has spent, and whether that figure can be established at all.

    The discipline is the one `pb-authority-demo-2`'s audit settled: reconcile the run tree's
    launches against the session's usage; unknown expenditure is unknown rather than zero; an
    unfinished model call has no ceiling unless something enforces a per-call limit, and without one
    the figure is **incomplete**, which refuses further launches.

    The quantity the guard admits against is `derived`: measured token usage priced at a dated
    table. The executor's own cost field is reported beside it because the two are known to
    disagree, and neither is provider-confirmed billing.
    """
    import _pricing
    import _profile

    run_root, db = Path(run_root), Path(db)
    facts = launch_facts(run_root, event_dirs)
    account: "dict[str, Any]" = {
        "launched_attempts": facts["launched"], "attempts": facts["attempts"],
        "scope": ("every attempt in the run tree" if event_dirs is None else
                  "the launches this ledger reserved; seeded attempts are excluded from "
                  "attribution and remain in the run tree"),
        "limit": AGGREGATE_LIMIT, "reserve": RESERVE,
        "quantity": "derived: measured token usage priced at a dated table; not provider billing",
    }
    if not db.is_file():
        if facts["launched"] == 0:
            return {**account, "derived": 0.0, "complete": True,
                    "claim": "nothing has been launched, so nothing has been spent"}
        return {**account, "derived": 0.0, "complete": False,
                "claim": f"{facts['launched']} attempt(s) were launched and no session database "
                         "exists; what they spent is unknown, not zero"}

    stage = _profile.profile(db, stage="implementer", model=model, variant=variant,
                             elapsed_seconds=0.0, verification_seconds=0.0)
    usage = dict(stage.get("usage") or {})
    account["usage"] = usage
    account["executor_reported_cost"] = usage.get("executor_cost")
    started, finished = usage.get("calls_started"), usage.get("calls_finished")
    account["model_calls"] = {"started": started, "finished": finished}

    unsettled: "list[str]" = []
    unfinished = (started - finished
                  if isinstance(started, int) and isinstance(finished, int) else None)
    missing_terminal = [a["event_dir"] for a in facts["attempts"]
                        if a.get("readable") and not a.get("terminal_present")]
    if missing_terminal:
        unsettled.append(f"attempt(s) without a terminal record: {missing_terminal}")
    unreadable = [a["event_dir"] for a in facts["attempts"] if not a.get("readable")]
    if unreadable:
        unsettled.append(f"attempt(s) whose record is unreadable: {unreadable}")
    account["interrupted_attempts"] = [
        a["event_dir"] for a in facts["attempts"]
        if a.get("terminal_present") and a.get("terminal_status") not in (None, "completed")]

    unattributed = []
    for attempt in facts["attempts"]:
        if not attempt.get("readable"):
            continue
        resolved, how = attempt.get("session_id"), "recorded in the terminal record"
        if not resolved and attempt.get("title"):
            resolved = _session_by_title(db, str(attempt["title"]))
            how = "recovered from the session database by exact title"
        attempt["attributed_session"] = resolved
        attempt["attributed_by"] = how if resolved else None
        if not resolved:
            unattributed.append(attempt["event_dir"])
    if unattributed:
        unsettled.append(f"attempt(s) whose usage cannot be attributed to a session: "
                         f"{unattributed}")

    priced = _pricing.cost(usage, model=model.split("/", 1)[-1], when=_priced_at(facts))
    amount = (priced or {}).get("amount")
    account["priced_at"] = _priced_at(facts).isoformat()
    if not isinstance(amount, (int, float)):
        return {**account, "derived": 0.0, "complete": False,
                "claim": "a session exists but no usage could be priced; spend is unknown, not zero"}
    account["cost"] = priced
    if unfinished:
        unsettled.append(
            f"{unfinished} model call(s) started and did not finish; no enforced per-call limit "
            "makes their cost boundable, so it is unknown, not zero")
    derived = round(float(amount), 6)
    if unsettled:
        return {**account, "derived": derived, "complete": False,
                "claim": "the derived figure omits work this run cannot account for — "
                         + "; ".join(unsettled)}
    return {**account, "derived": derived, "complete": True,
            "headroom": round(AGGREGATE_LIMIT - RESERVE - derived, 6),
            "claim": "the run tree's launches and the session's usage agree; this is the whole of "
                     "what this run's measured usage prices to"}


# -- the durable slot ledger ---------------------------------------------------------------------

class LaunchLedger:
    """Slots reserved, spent and classified. One JSON file, written before anything is launched."""

    def __init__(self, path: "str | Path") -> None:
        self.path = Path(path)
        if self.path.is_file():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {"format": LEDGER_FORMAT, "ceiling": LAUNCH_CEILING,
                         "limit": AGGREGATE_LIMIT, "reserve": RESERVE, "slots": []}
        if self.data.get("format") != LEDGER_FORMAT:
            raise ValueError(f"unexpected launch ledger format: {self.data.get('format')!r}")

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")

    # -- accounting over the ledger's own records ------------------------------------------------
    @property
    def slots(self) -> "list[dict[str, Any]]":
        return self.data["slots"]

    def spent_slots(self) -> int:
        """Slots that reached the executor. A pre-executor failure does not consume one."""
        return sum(1 for s in self.slots if s.get("classification") == EXECUTOR_REACHED)

    def pre_executor_failures(self) -> int:
        return sum(1 for s in self.slots if s.get("classification") == PRE_EXECUTOR_FAILURE)

    def unresolved(self) -> "list[dict[str, Any]]":
        return [s for s in self.slots if s.get("classification") in (None, UNRESOLVED)]

    def producer_attempts(self, phase: str, task: str) -> int:
        """How many producer attempts this task has had — the repair allowance's own test."""
        return sum(1 for s in self.slots
                   if s.get("phase") == phase and s.get("task") == task
                   and s.get("role") in ("implementer", "spec-author", "fixer")
                   and s.get("classification") == EXECUTOR_REACHED)

    # -- the guard -------------------------------------------------------------------------------
    def own_event_dirs(self) -> "list[str]":
        """The attempts this ledger reserved, by event-directory name."""
        return [Path(s["event_dir"]).name for s in self.slots if s.get("event_dir")]

    def admit(self, *, phase: str, task: str, role: str, run_root: "str | Path",
              db: "str | Path") -> "dict[str, Any]":
        """May another paid launch begin? Every refusal names the rule that refused it."""
        account = spend(run_root, db, event_dirs=self.own_event_dirs())
        findings: "list[str]" = []

        pending = self.unresolved()
        if pending:
            findings.append(
                f"slot(s) {[s['slot'] for s in pending]} were reserved and never classified; "
                "reconcile them before another launch")
        if not account["complete"]:
            findings.append(f"the spend figure is not complete: {account['claim']}")
        # The ceiling counts *reserved* slots, not just successful ones. It is derived as the worst
        # enumerated path plus one evidenced pre-executor relaunch, so a pre-executor failure that
        # consumed nothing would make that allowance unlimited — the arithmetic hole that let a
        # previous demonstration discover mid-run that its ceiling omitted a path its own text
        # granted.
        spent = self.spent_slots()
        reserved = spent + self.pre_executor_failures()
        if reserved + 1 > LAUNCH_CEILING:
            findings.append(
                f"a further launch would be slot {reserved + 1} of a ceiling of {LAUNCH_CEILING} "
                f"({spent} reached the executor, {self.pre_executor_failures()} did not)")
        derived = account.get("derived", 0.0)
        if account["complete"] and derived + RESERVE > AGGREGATE_LIMIT:
            findings.append(f"derived {derived} + reserve {RESERVE} exceeds {AGGREGATE_LIMIT}")
        if role in ("implementer", "spec-author", "fixer") and self.producer_attempts(
                phase, task) >= 2:
            findings.append(
                f"{phase}/{task} has already had {self.producer_attempts(phase, task)} producer "
                "attempts; the single shared repair allowance is spent")
        return {"admit": not findings, "why": findings,
                "slots_spent": spent, "slots_reserved": reserved, "ceiling": LAUNCH_CEILING,
                "pre_executor_failures": self.pre_executor_failures(),
                "derived": derived, "accounting_complete": account["complete"],
                "spend": account}

    def reserve(self, *, phase: str, task: str, role: str, note: str = "") -> "dict[str, Any]":
        """Write the intent down **before** the launcher runs. This is the durable reservation."""
        slot = {"slot": len(self.slots) + 1, "reserved_at": _now(), "phase": phase, "task": task,
                "role": role, "note": note, "classification": UNRESOLVED}
        self.slots.append(slot)
        self._flush()
        return slot

    def classify(self, slot_number: int, *, run_root: "str | Path", event_dir: "str | Path | None",
                 launcher_returncode: int, launcher_output: str) -> "dict[str, Any]":
        """Say what the reserved slot actually became, from evidence rather than from intent.

        A slot is `executor-reached` when an immutable launch reservation exists for it. It is a
        `pre-executor-failure` only when this ledger recorded the intent, no reservation was
        created, and the launcher's own output is retained to say why — the evidence a free
        reclassification requires.
        """
        slot = next(s for s in self.slots if s["slot"] == slot_number)
        event = Path(event_dir) if event_dir else None
        reserved = bool(event and (event / "launch-reservation.json").is_file())
        slot["classified_at"] = _now()
        slot["event_dir"] = str(event) if event else None
        slot["launcher_returncode"] = launcher_returncode
        slot["launcher_output"] = launcher_output[-2000:]
        slot["reservation_present"] = reserved
        if reserved:
            slot["classification"] = EXECUTOR_REACHED
            facts = {a["event_dir"]: a for a in launch_facts(run_root)["attempts"]}
            observed = facts.get(event.name, {}) if event else {}
            slot["terminal_status"] = observed.get("terminal_status")
            slot["session_title"] = observed.get("title")
        else:
            slot["classification"] = PRE_EXECUTOR_FAILURE
            slot["evidence"] = ("intent recorded before launch; no immutable reservation was "
                                "created, so the executor was never reached")
        self._flush()
        return slot

    def describe(self) -> "dict[str, Any]":
        return {"path": str(self.path), "ceiling": LAUNCH_CEILING,
                "slots_spent": self.spent_slots(),
                "pre_executor_failures": self.pre_executor_failures(),
                "unresolved": [s["slot"] for s in self.unresolved()],
                "slots": self.slots}

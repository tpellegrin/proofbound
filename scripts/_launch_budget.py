"""Supervised launch reservations and measured usage; never a provider billing cap."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LEDGER_FORMAT = "proofbound-launch-ledger-v1"
MODEL = "deepseek/deepseek-v4-flash"
VARIANT = "high"

#: Billing bases, as `_worker_profiles` names them. Repeated rather than imported so this module
#: stays importable by the historical experiment guards that predate profiles.
PRICED = "dated-table"
NO_EXTERNAL_BILLING = "no-external-api-billing"

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

    `event_dirs` narrows the inventory to explicitly recorded attempt paths. Historical callers
    may supply leaf names; nested task attempts use project-relative identities to avoid collisions.
    """
    run_root = Path(run_root)
    attempts = []
    for attempt_json in sorted(run_root.rglob("attempt.json")):
        event = attempt_json.parent
        relative = event.relative_to(run_root).as_posix()
        if event_dirs is not None and not {event.name, str(event), relative}.intersection(event_dirs):
            continue
        identity = relative if len(event.relative_to(run_root).parts) > 2 else event.name
        try:
            data = json.loads(attempt_json.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            attempts.append({"event_dir": identity, "readable": False})
            continue
        terminal: "dict[str, Any]" = {}
        terminal_path = event / "terminal.json"
        if terminal_path.is_file():
            try:
                terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                terminal = {"unreadable": True}
        attempts.append({
            "event_dir": identity, "readable": True,
            "path": str(event),
            "started_at": data.get("started_at"),
            "reservation": (event / "launch-reservation.json").is_file(),
            "session_id": terminal.get("session_id"),
            "title": terminal.get("title"),
            "terminal_status": terminal.get("status"),
            "terminal_present": bool(terminal),
        })
    return {"attempts": attempts, "launched": len(attempts)}


def sessions_in(db: Path) -> "dict[str, list[str]]":
    """Every session the database actually holds, id -> titles.

    Read once and compared against, because an attempt naming a session is a *claim*. A terminal
    record carrying `ses_missing` against a database holding only `ses_actual` used to attribute
    cleanly and report the run complete: the identifier was nonempty, and nothing looked it up.
    """
    import sqlite3
    from contextlib import closing
    out: "dict[str, list[str]]" = {}
    try:
        with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as conn:
            for sid, title in conn.execute("select id, title from session").fetchall():
                out.setdefault(str(sid), []).append(str(title))
    except sqlite3.Error:
        return {}
    return out


def _resolve_session(attempt: "dict[str, Any]", present: "dict[str, list[str]]",
                     ) -> "tuple[str | None, str, str | None]":
    """Which retained session this attempt's usage belongs to — or why that is not established.

    Returns `(session_id, how, problem)`. A recorded identifier must exist in the retained
    database; a title recovery must be unambiguous. Anything else leaves the attempt
    unattributed, which is a different fact from "attributed to nothing".
    """
    recorded = attempt.get("session_id")
    if recorded:
        if str(recorded) in present:
            return str(recorded), "recorded in the terminal record and present in the session "\
                                  "database", None
        return None, "recorded in the terminal record", (
            f"names session {recorded!r}, which the retained database does not contain")
    title = attempt.get("title")
    if title:
        matches = [sid for sid, titles in present.items() if str(title) in titles]
        if len(matches) == 1:
            return matches[0], "recovered from the session database by exact title", None
        if len(matches) > 1:
            return None, "title recovery", (
                f"title {title!r} matches {len(matches)} sessions; recovery is ambiguous")
        return None, "title recovery", f"no session carries the title {title!r}"
    return None, "no identifier", "the attempt records neither a session id nor a title"


def spend(run_root: "str | Path", db: "str | Path", *, model: str = MODEL,
          variant: str = VARIANT, event_dirs: "list[str] | None" = None,
          limit: float = 0, reserve: float = 0,
          billing: "dict[str, Any] | None" = None,
          output_token_allowance: "int | None" = None) -> "dict[str, Any]":
    """What this run has spent, and whether that figure can be established at all.

    Reconcile the run tree's launches against the session's usage; unknown expenditure is unknown
    rather than zero; an
    unfinished model call has no ceiling unless something enforces a per-call limit, and without one
    the figure is **incomplete**, which refuses further launches.

    The quantity the guard admits against is `derived`: measured token usage priced at a dated
    table. The executor's own cost field is reported beside it because the two are known to
    disagree, and neither is provider-confirmed billing.

    `billing` is the run's worker-profile basis. Absent, the historical DeepSeek table and `model`
    apply, which is how every caller before profiles existed was interpreted; the supervised
    workflow always passes it, so a run whose worker has no external bill is never priced through
    that default. An unbilled run reports usage and lifecycle facts and no money at all.
    """
    import _worker_pricing as _pricing
    import _worker_profile as _profile

    run_root, db = Path(run_root), Path(db)
    facts = launch_facts(run_root, event_dirs)
    account: "dict[str, Any]" = {
        "launched_attempts": facts["launched"], "attempts": facts["attempts"],
        "scope": ("every attempt in the run tree" if event_dirs is None else
                  "the launches this ledger reserved; other retained attempts are excluded"),
        "limit": limit, "reserve": reserve,
        "quantity": "derived: measured token usage priced at a dated table; not provider billing",
    }
    if billing is not None:
        account["billing"] = billing
        if billing.get("basis") == NO_EXTERNAL_BILLING:
            return _unbilled(run_root, db, facts, account, output_token_allowance)
        if billing.get("basis") != PRICED or billing.get("table") not in _pricing.TABLES:
            return {**account, "derived": None, "complete": False,
                    "claim": f"the worker profile names billing {billing!r}, which no retained "
                             "price table prices; spend is unknown, not zero"}
    price_model = (str(billing["price_model"]) if billing is not None
                   else model.split("/", 1)[-1])
    table = (_pricing.TABLES[billing["table"]] if billing is not None
             else _pricing.DEEPSEEK_2026_09_09)
    if not db.is_file():
        if facts["launched"] == 0:
            return {**account, "derived": 0.0, "complete": True,
                    "claim": "nothing has been launched, so nothing has been spent"}
        return {**account, "derived": None, "complete": False,
                "claim": f"{facts['launched']} attempt(s) were launched and no session database "
                         "exists; what they spent is unknown, not zero"}

    from _usage_events import events_from_db
    events = events_from_db(db)
    if not events["available"] or events["anomalies"]:
        return {**account, "derived": None, "complete": False,
                "anomalies": events["anomalies"],
                "claim": events.get("reason", "usage anomalies leave charges unknown")}
    stage = _profile.profile(db, stage="implementer", model=model, variant=variant,
                             elapsed_seconds=0.0, verification_seconds=0.0)
    usage = dict(stage.get("usage") or {})
    account["usage"] = usage
    account["executor_reported_cost"] = usage.get("executor_cost")
    started, finished = usage.get("calls_started"), usage.get("calls_finished")
    account["model_calls"] = {"started": started, "finished": finished}

    unfinished = (started - finished
                  if isinstance(started, int) and isinstance(finished, int) else None)
    lifecycle, telemetry = _settle(facts, db, account)
    unsettled: "list[str]" = lifecycle + telemetry

    priced = _pricing.cost_rows(events["rows"], model=price_model, table=table)
    amount = (priced or {}).get("amount")
    account["cost"] = priced
    if not isinstance(amount, (int, float)):
        return {**account, "derived": None, "complete": False,
                "claim": "a session exists but no usage could be priced; spend is unknown, not zero"}
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
            "headroom": round(limit - reserve - derived, 6),
            "claim": "the run tree's launches and the session's usage agree; this is the whole of "
                     "what this run's measured usage prices to"}


def _settle(facts: "dict[str, Any]", db: Path, account: "dict[str, Any]",
            ) -> "tuple[list[str], list[str]]":
    """What the run tree and the session database fail to agree on, in two kinds.

    *Lifecycle* findings say an attempt's own outcome is unknown — no terminal record, or one that
    cannot be read — and block any further trajectory whatever the worker costs. *Telemetry*
    findings say usage cannot be attributed or reconciled; they block exactly the allowances that
    are computed from usage. Recorded into `account`, returned as sentences.
    """
    import _worker_profile as _profile

    lifecycle: "list[str]" = []
    telemetry: "list[str]" = []
    missing_terminal = [a["event_dir"] for a in facts["attempts"]
                        if a.get("readable") and not a.get("terminal_present")]
    if missing_terminal:
        lifecycle.append(f"attempt(s) without a terminal record: {missing_terminal}")
    unreadable = [a["event_dir"] for a in facts["attempts"] if not a.get("readable")]
    if unreadable:
        lifecycle.append(f"attempt(s) whose record is unreadable: {unreadable}")
    account["interrupted_attempts"] = [
        a["event_dir"] for a in facts["attempts"]
        if a.get("terminal_present") and a.get("terminal_status") not in (None, "completed")]

    present = sessions_in(db)
    account["sessions_in_database"] = sorted(present)
    unattributed = []
    claimed: "dict[str, list[str]]" = {}
    for attempt in facts["attempts"]:
        if not attempt.get("readable"):
            continue
        resolved, how, problem = _resolve_session(attempt, present)
        attempt["attributed_session"] = resolved
        attempt["attributed_by"] = how if resolved else None
        attempt["attribution_problem"] = problem
        if resolved:
            claimed.setdefault(resolved, []).append(attempt["event_dir"])
        else:
            unattributed.append({"event_dir": attempt["event_dir"], "why": problem})
    if unattributed:
        telemetry.append(
            "attempt(s) whose usage cannot be attributed to a retained session: "
            + "; ".join(f"{u['event_dir']} {u['why']}" for u in unattributed))

    # Two attempts claiming one session is a **split** problem, not a total problem: both attempts
    # are this run's and so is the session, so the aggregate is still whole and only the per-attempt
    # division is unavailable. A session *no* attempt claims is different — its usage is being
    # priced here with nothing to attach it to, which means either an attempt is missing or the
    # figure includes work that is not this run's.
    reused = {sid: dirs for sid, dirs in claimed.items() if len(dirs) > 1}
    unaccounted = sorted(set(present) - set(claimed))
    if unaccounted:
        telemetry.append(f"session(s) in the database that no attempt claims, whose usage is "
                         f"nonetheless priced here: {unaccounted}")
    account["session_attribution"] = {
        "claimed": claimed, "unaccounted": unaccounted, "reused": reused,
        "unattributed_attempts": unattributed,
        "per_attempt_attribution_established": not (unattributed or reused or unaccounted),
        "why": ("each attempt resolves to its own retained session"
                if not (unattributed or reused or unaccounted) else
                "usage cannot be divided per attempt; the aggregate may still be settled"),
    }

    # Balanced totals are not a reconciliation: a start and a finish in different messages sum to
    # one of each while no call is known to have completed.
    parts = _profile.read_parts(db)
    reconciliation = _profile.call_reconciliation(parts)
    account["call_reconciliation"] = reconciliation
    if not reconciliation["reconciled"]:
        telemetry.append(
            f"{len(reconciliation['unmatched_messages'])} message(s) whose model-call starts and "
            f"finishes do not balance; equal totals do not establish that the same calls finished")

    # A finished call that consumed no input consumed no prompt, which no real call does. Observed,
    # not assumed: when a server omits its `usage` field, OpenCode 1.18.29 records zeros, so a zero
    # here is the executor's default rather than a measurement — unknown, never free.
    zero = [e["part_id"] for e in parts if e["part"].get("type") == "step-finish"
            and isinstance(e["part"].get("tokens"), dict)
            and not e["part"]["tokens"].get("input") and not e["part"]["tokens"].get("output")]
    account["zero_usage_calls"] = zero
    if zero:
        telemetry.append(
            f"{len(zero)} finished model call(s) record zero input and zero output tokens; the "
            "executor records zero when a server omits usage, so these counts are unknown, not zero")
    return lifecycle, telemetry


def _unbilled(run_root: Path, db: Path, facts: "dict[str, Any]", account: "dict[str, Any]",
              allowance: "int | None") -> "dict[str, Any]":
    """Accounting for a worker with no external API bill: usage and lifecycle, never money.

    No price is derived, and none is implied: a known absence of API billing is not a claim that
    compute, electricity or hardware cost nothing. Missing token counts stay missing. What blocks
    another launch follows from what the admission rule actually consumes — an attempt whose
    outcome is unknown always blocks, and telemetry gaps block only when an output-token allowance
    is configured, because that allowance is the one thing computed from them.
    """
    account["quantity"] = ("usage and lifecycle only: no external API billing is configured for "
                           "this worker, so no price is derived")
    account["cost"] = {"basis": NO_EXTERNAL_BILLING, "amount": None,
                       "reason": "no external API bill is expected; local compute, electricity "
                                 "and hardware cost are unknown, not zero"}
    account["derived"] = None
    account["output_token_allowance"] = allowance
    lifecycle: "list[str]" = []
    telemetry: "list[str]" = []
    if not db.is_file():
        if facts["launched"]:
            telemetry.append(f"{facts['launched']} attempt(s) were launched and no session "
                             "database exists; their usage is unknown, not zero")
            missing = [a["event_dir"] for a in facts["attempts"]
                       if not a.get("readable") or not a.get("terminal_present")]
            if missing:
                lifecycle.append(f"attempt(s) without a readable terminal record: {missing}")
    else:
        import _worker_profile as _profile
        from _usage_events import events_from_db
        events = events_from_db(db)
        if not events["available"] or events["anomalies"]:
            account["anomalies"] = events["anomalies"]
            telemetry.append(events.get("reason", "usage anomalies leave token counts unknown"))
        usage = _profile.usage(_profile.read_parts(db))
        account["usage"] = usage
        account["executor_reported_cost"] = usage.get("executor_cost")
        started, finished = usage.get("calls_started"), usage.get("calls_finished")
        account["model_calls"] = {"started": started, "finished": finished}
        more_lifecycle, more_telemetry = _settle(facts, db, account)
        lifecycle += more_lifecycle
        telemetry += more_telemetry
        if isinstance(started, int) and isinstance(finished, int) and started > finished:
            telemetry.append(f"{started - finished} model call(s) started and did not finish; "
                             "their token counts are unknown, and the server may still be "
                             "generating")
    lifecycle_complete, telemetry_complete = not lifecycle, not telemetry
    blocking = lifecycle + (telemetry if allowance is not None else [])
    account.update(lifecycle_complete=lifecycle_complete, telemetry_complete=telemetry_complete,
                   telemetry_gaps=telemetry, complete=not blocking)
    if blocking:
        account["claim"] = ("admission depends on facts this run cannot settle — "
                            + "; ".join(blocking))
    elif telemetry:
        account["claim"] = ("every attempt's outcome is recorded; usage telemetry is incomplete "
                            "and nothing admitted depends on it: " + "; ".join(telemetry))
    else:
        account["claim"] = ("every attempt's outcome is recorded and usage reconciles; no money "
                            "is derived because none is billed")
    return account


# -- the durable slot ledger ---------------------------------------------------------------------

class LaunchLedger:
    """Slots reserved, spent and classified. One JSON file, written before anything is launched."""

    def __init__(self, path: "str | Path", *, limit: float = 0, reserve: float = 0,
                 ceiling: int = 0, repair_cycles: int = 1,
                 billing: "dict[str, Any] | None" = None,
                 output_token_allowance: "int | None" = None) -> None:
        """`billing` and `output_token_allowance` are frozen into a new ledger with its limits.

        A ledger that recorded neither predates worker profiles and keeps the historical DeepSeek
        interpretation. One that recorded a basis refuses a caller naming a different one: the
        guard must never price a run against a basis other than the one its first slot was
        reserved under.
        """
        self.path = Path(path)
        if self.path.is_file():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {"format": LEDGER_FORMAT, "ceiling": ceiling,
                         "limit": limit, "reserve": reserve, "repair_cycles": repair_cycles, "slots": []}
            if billing is not None:
                self.data["billing"] = billing
                self.data["output_token_allowance"] = output_token_allowance
        if self.data.get("format") != LEDGER_FORMAT:
            raise ValueError(f"unexpected launch ledger format: {self.data.get('format')!r}")
        recorded = self.data.get("billing")
        if billing is not None and recorded is not None and recorded != billing:
            raise ValueError(f"this launch ledger was frozen under billing {recorded!r}; the caller "
                             f"names {billing!r}. Nothing was admitted")
        if billing is not None and recorded is None and billing.get("basis") != PRICED:
            raise ValueError("this launch ledger predates worker profiles and is interpreted "
                             "under the historical DeepSeek price table; it cannot be reused by "
                             f"a worker billed as {billing.get('basis')!r}")

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        from dsd_state import atomic_json
        atomic_json(self.path, self.data)

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
        """Retain flat-run wire names; nested attempts use distinct run-relative identities."""
        return [s.get("event_identity", Path(s["event_dir"]).name)
                for s in self.slots if s.get("event_dir")]

    def admit(self, *, phase: str, task: str, role: str, run_root: "str | Path",
              db: "str | Path") -> "dict[str, Any]":
        """May another paid launch begin? Every refusal names the rule that refused it."""
        billing = self.data.get("billing")
        allowance = self.data.get("output_token_allowance")
        unbilled = (billing or {}).get("basis") == NO_EXTERNAL_BILLING
        account = spend(run_root, db, event_dirs=self.own_event_dirs(),
                        limit=self.data["limit"], reserve=self.data["reserve"],
                        billing=billing, output_token_allowance=allowance)
        ceiling, limit, reserve = self.data["ceiling"], self.data["limit"], self.data["reserve"]
        findings: "list[str]" = []

        pending = self.unresolved()
        if pending:
            account = {**account, "complete": False, "claim": "launch intent is unreconciled; charges may be unknown. " + account["claim"]}
            findings.append(
                f"slot(s) {[s['slot'] for s in pending]} were reserved and never classified; "
                "reconcile them before another launch")
        if not account["complete"]:
            findings.append(f"the spend figure is not complete: {account['claim']}")
        # Count classified pre-executor failures too: a failed launch must not create an
        # unlimited retry allowance. Pending reservations separately refuse admission above.
        spent = self.spent_slots()
        reserved = spent + self.pre_executor_failures()
        if reserved + 1 > ceiling:
            findings.append(
                f"a further launch would be slot {reserved + 1} of a ceiling of {ceiling} "
                f"({spent} reached the executor, {self.pre_executor_failures()} did not)")
        derived = account.get("derived", 0.0)
        if not unbilled and account["complete"] and derived + reserve > limit:
            findings.append(f"derived {derived} + reserve {reserve} exceeds {limit}")
        if unbilled and allowance is not None and account["complete"]:
            used = sum(int((account.get("usage") or {}).get(k) or 0)
                       for k in ("output", "reasoning"))
            if used >= allowance:
                findings.append(f"{used} generated tokens (output + reasoning) reach the "
                                f"output-token allowance of {allowance}")
        if role in ("implementer", "spec-author", "fixer") and self.producer_attempts(
                phase, task) >= 1 + self.data.get("repair_cycles", 1):
            findings.append(
                f"{phase}/{task} has already had {self.producer_attempts(phase, task)} producer "
                "attempts; the single shared repair allowance is spent")
        return {"admit": not findings, "why": findings,
                "slots_spent": spent, "slots_reserved": reserved, "ceiling": ceiling,
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
        if event:
            relative = event.resolve().relative_to(Path(run_root).resolve())
            slot["event_identity"] = relative.as_posix() if len(relative.parts) > 2 else event.name
        slot["launcher_returncode"] = launcher_returncode
        slot["launcher_output"] = launcher_output[-2000:]
        slot["reservation_present"] = reserved
        if reserved:
            slot["classification"] = EXECUTOR_REACHED
            facts = {a["path"]: a for a in launch_facts(run_root)["attempts"] if a.get("path")}
            observed = facts.get(str(event), {}) if event else {}
            slot["terminal_status"] = observed.get("terminal_status")
            slot["session_title"] = observed.get("title")
        else:
            slot["classification"] = PRE_EXECUTOR_FAILURE
            slot["evidence"] = ("intent recorded before launch; no immutable reservation was "
                                "created, so the executor was never reached")
        self._flush()
        return slot

    def describe(self) -> "dict[str, Any]":
        return {"path": str(self.path), "ceiling": self.data["ceiling"],
                "slots_spent": self.spent_slots(),
                "pre_executor_failures": self.pre_executor_failures(),
                "unresolved": [s["slot"] for s in self.unresolved()],
                "slots": self.slots}

"""Minimal accounting evidence; no prompts or tool payloads are retained."""
from __future__ import annotations
import json
import math
import sqlite3
from pathlib import Path
from typing import Any

EVENT_ALLOWLIST = (
    "session_id", "message_id", "part_id", "time_created", "role", "type",
    "model", "provider", "variant",
    "input", "output", "reasoning", "cache_read", "cache_write", "executor_cost",
    "tool", "tool_status", "tool_started", "tool_ended",
)

def events_from_db(db: Path) -> dict[str, Any]:
    """Allowlisted accounting rows from an OpenCode session database.

    Anomalies are *recorded*, never dropped. A malformed row that vanishes silently turns a
    collection defect into a cheap-looking run, and a duplicated row that is summed twice turns one
    call into two. Both are reported so a reader can decide what the record supports.
    """
    db = Path(db)
    if not db.is_file():
        return {"available": False, "reason": f"no session database at {db}", "rows": [],
                "anomalies": []}
    uri = f"file:{db.as_posix()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        return {"available": False, "reason": f"session database unavailable: {exc}", "rows": [], "anomalies": []}
    try:
        raw = conn.execute(
            "SELECT p.id, p.message_id, p.data, m.data, m.time_created, m.session_id "
            "FROM part p JOIN message m ON m.id = p.message_id "
            "ORDER BY m.time_created, p.message_id, p.id").fetchall()
    except sqlite3.Error as exc:
        conn.close()
        return {"available": False, "reason": f"session database unreadable: {exc}", "rows": [],
                "anomalies": []}
    finally:
        try:
            conn.close()
        except sqlite3.Error:                                  # pragma: no cover
            pass

    rows: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    seen: set[str] = set()
    for part_id, message_id, part_raw, message_raw, created, session_id in raw:
        try:
            part = json.loads(part_raw)
            message = json.loads(message_raw)
        except (json.JSONDecodeError, TypeError) as exc:
            anomalies.append({"part_id": part_id, "kind": "unparseable-row", "detail": str(exc)})
            continue
        if part_id in seen:
            anomalies.append({"part_id": part_id, "kind": "duplicate-part-id",
                              "detail": "the same part id appears more than once"})
        seen.add(part_id)
        if not isinstance(part, dict) or not isinstance(message, dict):
            anomalies.append({"part_id": part_id, "kind": "non-object-row"})
            continue
        row = {k: None for k in EVENT_ALLOWLIST}
        row.update({
            "session_id": session_id, "message_id": message_id, "part_id": part_id,
            "time_created": created, "role": message.get("role"),
            "type": part.get("type"),
            "model": message.get("modelID") if isinstance(message.get("modelID"), str) else None,
            "provider": message.get("providerID"), "variant": message.get("variant"),
        })
        if part.get("type") == "step-finish":
            tokens = part.get("tokens")
            cache = tokens.get("cache") if isinstance(tokens, dict) else {}
            cache = cache if isinstance(cache, dict) else {}
            if not isinstance(tokens, dict):
                anomalies.append({"part_id": part_id, "kind": "step-finish-without-tokens",
                                  "detail": "a finished call carries no token counts; its usage "
                                            "is unknown, not zero"})
            else:
                for key, value in (("input", tokens.get("input")), ("output", tokens.get("output")),
                                   ("reasoning", tokens.get("reasoning")),
                                   ("cache_read", cache.get("read")),
                                   ("cache_write", cache.get("write"))):
                    if value is None:
                        if key != "reasoning":
                            anomalies.append({"part_id": part_id, "kind": "missing-token-count", "field": key})
                        continue
                    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                        anomalies.append({"part_id": part_id, "kind": "non-numeric-token-count",
                                          "detail": f"invalid count in {key}"})
                        continue
                    row[key] = int(value)
            if isinstance(part.get("cost"), (int, float)):
                row["executor_cost"] = float(part["cost"])
        elif part.get("type") == "tool":
            state = part.get("state") or {}
            time_block = state.get("time") or {}
            row.update({"tool": part.get("tool"), "tool_status": state.get("status"),
                        "tool_started": time_block.get("start"),
                        "tool_ended": time_block.get("end")})
        rows.append(row)
    return {"available": True, "rows": rows, "anomalies": anomalies,
            "sessions": sorted({r["session_id"] for r in rows if r["session_id"]})}


def usage_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Recompute usage totals from allowlisted rows, through the module the live guard uses.

    `_profile.usage` is the one implementation of this summation. Re-deriving the arithmetic here
    would let the exporter and the reader agree with each other while both disagreeing with what
    the run actually spent.
    """
    import _worker_profile as _profile

    shaped = []
    for i, row in enumerate(rows):
        part: dict[str, Any] = {"type": row.get("type")}
        if row.get("type") == "step-finish":
            part["tokens"] = {
                "input": row.get("input"), "output": row.get("output"),
                "reasoning": row.get("reasoning"),
                "cache": {"read": row.get("cache_read"), "write": row.get("cache_write")}}
            if row.get("executor_cost") is not None:
                part["cost"] = row["executor_cost"]
        shaped.append({"ordinal": i, "part": part})
    return _profile.usage(shaped)

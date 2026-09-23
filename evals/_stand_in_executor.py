#!/usr/bin/env python3
"""A scripted stand-in for the `opencode` executable. It makes no model call and needs no key.

The qualification replay installs a two-line `opencode` shim that runs this file with a role
script beside it. The launcher resolves that shim through `PATH` exactly as it resolves the real
executor, pins its bytes, and runs it inside the same attempt lifecycle; this file then does what
the role script says — writes the named files and the report — and records a session in the same
SQLite shape OpenCode writes, so accounting, attribution and evidence export run on real rows.

Everything it "decides" was written in advance by the replay driver. It is evidence that the
production path and the graders behave as declared, and never evidence about a model.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import time
from contextlib import closing
from pathlib import Path


def main(argv: list[str], script_path: Path) -> int:
    db = Path(os.environ["OPENCODE_DB"])
    if argv[:2] == ["session", "list"]:
        with closing(sqlite3.connect(db)) as conn:
            rows = conn.execute("select id, title from session").fetchall()
        print(json.dumps([{"id": s, "title": t} for s, t in rows]))
        return 0
    title = argv[argv.index("--title") + 1]
    prompt = argv[-1]
    task, role = title.split(":")[1:3]
    report = Path(re.search(r"^Report: (.+)$", prompt, re.M).group(1))
    scripts = json.loads(script_path.read_text(encoding="utf-8"))
    script = scripts.get(f"{task}:{role}") or scripts.get(role) or {}
    files = {Path(p): text for p, text in (script.get("files") or {}).items()}
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    report.write_text(script.get("report") or (
        f"# Stand-in report ({role})\n\nScripted by the qualification replay; no model produced "
        "this and no semantic review was performed.\n"), encoding="utf-8")

    sid = "ses_" + hashlib.sha256(title.encode()).hexdigest()[:12]
    now = int(time.time() * 1000)
    db.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("create table if not exists session (id text, title text)")
        conn.execute("create table if not exists message "
                     "(id text, session_id text, time_created integer, data text)")
        conn.execute("create table if not exists part (id text, message_id text, data text)")
        conn.execute("insert into session values (?, ?)", (sid, title))
        message = json.dumps({"role": "assistant", "modelID": "stand-in-executor",
                              "providerID": "stand-in", "variant": None})
        conn.execute("insert into message values (?, ?, ?, ?)", (sid, sid, now, message))
        tokens = {"input": 1000, "output": 50, "reasoning": 0, "cache": {"read": 0, "write": 0}}
        conn.execute("insert into part values (?, ?, ?)",
                     (sid + "-start", sid, json.dumps({"type": "step-start"})))
        for n, path in enumerate([*files, report]):
            conn.execute("insert into part values (?, ?, ?)", (f"{sid}-tool-{n}", sid, json.dumps(
                {"type": "tool", "tool": "write",
                 "state": {"status": "completed", "time": {"start": now, "end": now + 1}}})))
        conn.execute("insert into part values (?, ?, ?)", (sid + "-finish", sid, json.dumps(
            {"type": "step-finish", "cost": 0, "tokens": tokens})))
        conn.commit()
    print(str(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], Path(os.environ["PB_STAND_IN_SCRIPT"])))

#!/usr/bin/env python3
"""Rehearse `pb-authority-demo-2`'s command sequence with a fake executor. Unpaid.

No provider, no credentials, no cost. Two things the predecessor's rehearsal did not do:

* it **invokes `pb_execution.py authorize`** before launching implementation. The predecessor only
  wrote a candidate string into a contract, which is not the guard — a candidate in a contract is a
  declaration, and the guard is the three derived checks in `pb_execution`;
* it rehearses the **repair path**, not only the clean one: a rejected specification, a second
  author attempt on the same immutable contract, a fresh reflection of that attempt, and the
  acceptance that only the fresh review can support.

The fake is credential-free and its environment is constructed rather than inherited: `PATH` is
replaced, `HOME` points at an empty directory, `OPENCODE_*` is dropped, the resolved executable is
checked **by content**, and the environment is passed explicitly at every call.

    python3 demo/pb-authority-demo-2/rehearse.py --into <workdir> [--path clean|repair]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRIPTS = ROOT / "scripts"
CONTRACTS = HERE / "contracts"

FAKE = r'''#!/usr/bin/env python3
"""A fake `opencode`. Branches on ROLE, never on task: a reviewer runs on the producer's task."""
import json, os, pathlib, re, sys

args = sys.argv[1:]
db = pathlib.Path(os.environ["OPENCODE_DB"]); db.parent.mkdir(parents=True, exist_ok=True)
if args[:2] == ["session", "list"]:
    t = db.with_suffix(".title")
    print(json.dumps([{"id": "ses_fake", "title": t.read_text() if t.exists() else ""}]))
    raise SystemExit(0)
if not args or args[0] != "run":
    raise SystemExit(2)
title = args[args.index("--title") + 1]
db.with_suffix(".title").write_text(title)
prompt = args[-1]
report = pathlib.Path(re.search(r"^Report: (.+)$", prompt, re.M).group(1).strip())
task, role, attempt = title.split(":")[1], title.split(":")[2], title.split(":")[3]
mode = os.environ.get("PB_FAKE_SPEC_MODE", "good")

if role == "spec-author":
    faulty = (mode == "faulty" and attempt == "1")
    pathlib.Path("spec.md").write_text(
        "# Specification - retry_after\n\n"
        + ("`retry_after` returns `(1.0 - available) / refill_per_second`, and waiting exactly "
           "that long admits.\n" if faulty else
           "`retry_after(key)` returns 0.0 when a call would be admitted now, and otherwise a "
           "delay such that advancing the clock by it reaches an instant where `allow` admits, "
           "exceeding the exact requirement by at most four units in the last place of that "
           "instant. It is a pure query. Infinity when no finite delay exists.\n")
        + "\n## Not changing\n- `allow`, the constructor, the clock.\n"
        + "\n## Advice, not requirement\nSharing the refill arithmetic is suggested.\n",
        encoding="utf-8")
    report.write_text(f"# {task} spec-author attempt {attempt}\n\nWrote `spec.md`"
                      + (" using the exact-boundary formula.\n" if faulty else
                         " promising a usable delay in instant space.\n"), encoding="utf-8")
elif role == "spec-reflector" and task == "RG-spec":
    verdict = "FAIL - the exact-boundary claim is false of the formula it mandates." \
        if (mode == "faulty" and attempt == "1") else \
        "No task-relevant defect found."
    report.write_text(f"# {task} specification-reflection attempt {attempt}\n\n{verdict}\n",
                      encoding="utf-8")
elif role == "implementer":
    source = pathlib.Path("rateguard/__init__.py")
    text = source.read_text(encoding="utf-8")
    text = text.replace("import time\n", "import math\nimport time\n", 1)
    text = text.replace(
        "    def allow(self, key: str) -> bool:",
        "    def _available(self, key, now):\n"
        "        tokens = self._tokens.get(key, float(self.capacity))\n"
        "        last = self._last.get(key, now)\n"
        "        elapsed = now - last\n"
        "        if elapsed < 0.0:\n"
        "            elapsed = 0.0\n"
        "        tokens = tokens + elapsed * self.refill_per_second\n"
        "        if tokens > self.capacity:\n"
        "            tokens = float(self.capacity)\n"
        "        return tokens\n\n"
        "    def retry_after(self, key):\n"
        "        now = self._clock()\n"
        "        available = self._available(key, now)\n"
        "        if available >= 1.0:\n"
        "            return 0.0\n"
        "        wait = (1.0 - available) / self.refill_per_second\n"
        "        if not math.isfinite(wait):\n"
        "            return math.inf\n"
        "        for _ in range(256):\n"
        "            reached = now + wait\n"
        "            if not math.isfinite(reached):\n"
        "                return math.inf\n"
        "            if self._available(key, reached) >= 1.0:\n"
        "                return wait\n"
        "            target = math.nextafter(reached, math.inf)\n"
        "            nxt = target - now\n"
        "            if not (math.isfinite(nxt) and nxt > wait):\n"
        "                nxt = math.nextafter(wait, math.inf)\n"
        "                if not (nxt > wait):\n"
        "                    return math.inf\n"
        "            wait = nxt\n"
        "        return math.inf\n\n"
        "    def allow(self, key: str) -> bool:", 1)
    source.write_text(text, encoding="utf-8")
    report.write_text(f"# {task} implementer attempt {attempt}\n\nAdded `retry_after`.\n",
                      encoding="utf-8")
else:
    report.write_text(f"# {task} {role} attempt {attempt}\n\nIndependent review reached the "
                      "production path; no task-relevant defect found.\n", encoding="utf-8")
'''


def sh(argv: "list[Any]", **kw: Any) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, check=False, **kw)


def must(done: subprocess.CompletedProcess, what: str) -> str:
    if done.returncode != 0:
        raise SystemExit(f"REHEARSAL STOPPED at {what}:\n{done.stdout}\n{done.stderr}")
    return done.stdout.strip()


class Rehearsal:
    def __init__(self, into: Path, *, spec_mode: str = "good") -> None:
        self.into = into.expanduser().resolve()
        self.project = self.into / "project"
        self.run = self.project / "DeepSeekAndDestroy/plans/demo2/runs/r1"
        self.ledger = self.into / "ledger.json"
        self.graph = self.project / "change-graph.json"
        self.freezes = self.into / "freezes"
        self.consistency = self.into / "consistency"
        self.contracts = self.run / "contracts"
        self.log: "list[dict[str, Any]]" = []

        bin_dir = self.into / "fakebin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        fake = bin_dir / "opencode"
        fake.write_text(FAKE, encoding="utf-8")
        fake.chmod(0o755)
        home = self.into / "credential-free-home"
        home.mkdir(parents=True, exist_ok=True)

        self.env = {k: v for k, v in os.environ.items() if not k.startswith("OPENCODE")}
        self.env["PATH"] = os.pathsep.join([str(bin_dir), "/usr/bin", "/bin"])
        self.env["HOME"] = str(home)
        self.env["PB_FAKE_SPEC_MODE"] = spec_mode
        resolved = shutil.which("opencode", path=self.env["PATH"])
        if resolved != str(fake):
            raise SystemExit(f"refusing to rehearse: `opencode` resolved to {resolved}")
        if Path(resolved).read_text(encoding="utf-8") != FAKE:
            raise SystemExit("refusing to rehearse: the resolved `opencode` is not this fake")
        if (home / ".local/share/opencode/auth.json").exists():
            raise SystemExit("refusing to rehearse: the constructed home holds a credential")

    def note(self, step: str, detail: Any = None) -> None:
        self.log.append({"step": step, "detail": detail})
        print(f"  ok  {step}")

    def contract(self, task: str, candidate: "str | None" = None) -> Path:
        text = (CONTRACTS / f"{task}.md").read_text(encoding="utf-8")
        if candidate is not None:
            text = text.replace("<CANDIDATE>", candidate)
        elif "<CANDIDATE>" in text:
            raise SystemExit(f"{task} binds a candidate but none was supplied")
        target = self.contracts / f"{task}.md"
        target.write_text(text, encoding="utf-8")
        return target

    def bind(self, phase: str, task: str, contract: Path) -> None:
        must(sh([sys.executable, SCRIPTS / "dsd_state.py", "bind-contract",
                 "--run-root", self.run, "--phase-id", phase, "--task-id", task,
                 "--contract", contract]), f"bind {phase}/{task}")

    def work(self, phase: str, task: str, role: str, *,
             inputs: "list[Path] | None" = None) -> Path:
        argv = [sys.executable, SCRIPTS / "dsd_attempt.py", "launch",
                "--run-root", self.run, "--phase-id", phase, "--task-id", task,
                "--role", role, "--auto-flag=", "--timeout", "120"]
        for path in inputs or []:
            argv += ["--input", str(path)]
        must(sh(argv, env=self.env), f"launch {phase}/{task} as {role}")
        must(sh([sys.executable, SCRIPTS / "dsd_attempt.py", "gate",
                 "--run-root", self.run, "--phase-id", phase, "--task-id", task], env=self.env),
             f"gate {phase}/{task} as {role}")
        state = json.loads((self.run / "state.json").read_text(encoding="utf-8"))
        event = Path(state["phases"][phase]["tasks"][task]["current_attempt"]["event_dir"])
        if not event.is_absolute():
            event = self.run / event
        gate = event / "evidence-gate.json"
        if not gate.is_file():
            raise SystemExit(f"no evidence gate for {phase}/{task} at {gate}")
        return gate

    def accept(self, phase: str, task: str, gate: Path) -> subprocess.CompletedProcess:
        return sh([sys.executable, SCRIPTS / "dsd_state.py", "accept-task",
                   "--run-root", self.run, "--phase-id", phase, "--task-id", task,
                   "--evidence-gate", gate])

    def authorize(self, *, contract: "Path | None" = None,
                  candidate: "str | None" = None) -> subprocess.CompletedProcess:
        argv = [sys.executable, SCRIPTS / "pb_execution.py", "authorize",
                "--graph", self.graph, "--ledger", self.ledger,
                "--project-root", self.project, "--consistency", self.consistency,
                "--run-root", self.run]
        if contract is not None:
            argv += ["--contract", str(contract)]
        if candidate is not None:
            argv += ["--candidate", candidate]
        return sh(argv)

    # -- the sequence ---------------------------------------------------------------------------
    def design_phase(self, *, repair: bool) -> str:
        self.bind("design", "RG-spec", self.contract("RG-spec"))
        author = self.work("design", "RG-spec", "spec-author")
        self.note("spec authored", {"attempt": author.parent.name})

        refused = self.accept("design", "RG-spec", author)
        if refused.returncode == 0:
            raise SystemExit("the author's own gate was accepted as its own review")
        self.note("author's own gate refused as its own review",
                  (refused.stderr or refused.stdout).strip()[:120])

        reflector = self.work("design", "RG-spec", "spec-reflector",
                              inputs=[author.parent / "report.md"])
        self.note("specification reflected", {"attempt": reflector.parent.name})

        if repair:
            # The one budgeted repair: the parent rejects, the same immutable contract gets a
            # second author attempt, and the earlier review is then stale by construction.
            stale = self.accept("design", "RG-spec", reflector)
            author2 = self.work("design", "RG-spec", "spec-author",
                                inputs=[reflector.parent / "report.md"])
            invalidated = self.accept("design", "RG-spec", reflector)
            if invalidated.returncode == 0:
                raise SystemExit("a review predating the repair was still acceptable")
            self.note("the repair invalidated the earlier review",
                      (invalidated.stderr or invalidated.stdout).strip()[:140])
            reflector = self.work("design", "RG-spec", "spec-reflector",
                                  inputs=[author2.parent / "report.md"])
            self.note("repaired specification reflected afresh",
                      {"attempt": reflector.parent.name, "first_accept_ok": stale.returncode == 0})

        must(self.accept("design", "RG-spec", reflector), "accept design/RG-spec")
        self.note("specification accepted against the current reflection")

        must(sh([sys.executable, SCRIPTS / "pb_ledger.py", "record",
                 "--run-root", self.run, "--phase-id", "design", "--task-id", "RG-spec",
                 "--artifact", self.project / "spec.md", "--ledger", self.ledger]),
             "ledger record spec.md")
        graph = json.loads(must(sh([sys.executable, SCRIPTS / "pb_graph.py", "validate",
                                    "--graph", self.graph, "--ledger", self.ledger,
                                    "--project-root", self.project]), "graph validate"))
        self.note("ledger recorded and graph satisfied",
                  {"findings": [f["code"] for f in graph.get("findings", [])]})

        frozen = json.loads(must(sh([sys.executable, SCRIPTS / "pb_freeze.py", "create",
                                     "--graph", self.graph, "--ledger", self.ledger,
                                     "--project-root", self.project, "--into", self.freezes]),
                                 "freeze create"))
        candidate = frozen.get("identity") or frozen.get("candidate")
        self.note("candidate frozen", {"candidate": candidate})

        # Before consistency acceptance the guard must refuse: no acceptance record yet.
        early = self.authorize(candidate=candidate)
        if early.returncode == 0:
            raise SystemExit("authorization succeeded before consistency acceptance")
        self.note("authorization refused before the aggregate was accepted",
                  (early.stdout or early.stderr).strip()[-160:])

        self.bind("design", "RG-consistency", self.contract("RG-consistency", candidate))
        consistency = self.work("design", "RG-consistency", "spec-reflector")
        must(self.accept("design", "RG-consistency", consistency), "accept design/RG-consistency")
        must(sh([sys.executable, SCRIPTS / "pb_consistency.py", "record",
                 "--run-root", self.run, "--phase-id", "design", "--task-id", "RG-consistency",
                 "--freeze", self.freezes / f"{candidate}.json", "--into", self.consistency]),
             "consistency record")
        self.note("aggregate accepted", {"candidate": candidate})
        return candidate

    def build_phase(self, candidate: str) -> None:
        contract = self.contract("RG-impl", candidate)
        verdict = self.authorize(contract=contract)
        must(verdict, "pb_execution authorize")
        self.note("implementation authorized by the guard",
                  json.loads(verdict.stdout) if verdict.stdout.strip().startswith("{") else None)

        self.bind("build", "RG-impl", contract)
        impl = self.work("build", "RG-impl", "implementer")
        review = self.work("build", "RG-impl", "reviewer", inputs=[impl.parent / "report.md"])
        must(self.accept("build", "RG-impl", review), "accept build/RG-impl")
        self.note("implementation accepted against the reviewer's gate")

    def run_all(self, *, repair: bool) -> "dict[str, Any]":
        candidate = self.design_phase(repair=repair)
        self.build_phase(candidate)
        return {"candidate": candidate, "steps": len(self.log)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--into", type=Path, required=True)
    ap.add_argument("--path", choices=["clean", "repair"], default="clean")
    args = ap.parse_args()
    repair = args.path == "repair"
    result = Rehearsal(args.into, spec_mode="faulty" if repair else "good").run_all(repair=repair)
    print(json.dumps({"rehearsal": args.path, **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

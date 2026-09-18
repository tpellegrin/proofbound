#!/usr/bin/env python3
"""Rehearse `pb-authority-demo-1`'s command sequence with a fake executor. Unpaid.

No provider, no credentials, no cost. The fake writes plausible artifacts and reports so that the
*sequence* can be proved before real agents are paid for it: bind, launch, gate, accept against a
fresh reviewer's gate, record in the ledger, validate the graph, freeze a candidate, accept the
aggregate, authorize a candidate-bound implementation, review it, accept.

This exists because the committed design's command list was wrong in several places, each
discovered only by running it. Finding the rest of them with a fake worker costs nothing; finding
them with a real one costs the demonstration's budget.

It rehearses the *mechanics*. It says nothing about whether a real agent can do the work.

    python3 demo/pb-authority-demo-1/rehearse.py --into <workdir>
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
"""A fake `opencode`: writes what each role would write, and nothing else."""
import json, os, pathlib, re, sys

args = sys.argv[1:]
db = pathlib.Path(os.environ["OPENCODE_DB"]); db.parent.mkdir(parents=True, exist_ok=True)
if args[:2] == ["session", "list"]:
    title = db.with_suffix(".title")
    print(json.dumps([{"id": "ses_fake", "title": title.read_text() if title.exists() else ""}]))
    raise SystemExit(0)
if not args or args[0] != "run":
    raise SystemExit(2)
title = args[args.index("--title") + 1]
db.with_suffix(".title").write_text(title)
prompt = args[-1]
report = pathlib.Path(re.search(r"^Report: (.+)$", prompt, re.M).group(1).strip())
task, role = title.split(":")[1], title.split(":")[2]

if role == "spec-author":
    attempt = title.split(":")[3]
    pathlib.Path("spec.md").write_text(
        ("" if attempt == "1" else f"<!-- revision {attempt} -->\n") +
        "# Specification — `retry_after`\n\n"
        "`RateGuard.retry_after(key)` returns a float: the seconds until `allow(key)` would "
        "admit, and `0.0` when it would admit now. It is a query: it consumes no token and "
        "changes no later answer. It agrees with `allow` at the same instant. It never increases "
        "while the clock advances. An unseen key answers `0.0`. `allow` is unchanged, as are the "
        "constructor, per-key independence, the burst allowance, the refill rate and the "
        "injectable clock. No I/O and no sleeping.\n\n"
        "## Not changing\n- `allow`'s meaning.\n- The existing suite, which must pass unedited.\n\n"
        "## Advice, not requirement\nSharing the refill arithmetic is suggested, not required.\n",
        encoding="utf-8")
    report.write_text("# RG-spec\n\nWrote `spec.md` specifying `retry_after` from the accepted "
                      "intent. No other file touched.\n", encoding="utf-8")
elif role == "implementer":
    source = pathlib.Path("rateguard/__init__.py")
    text = source.read_text(encoding="utf-8")
    text = text.replace(
        "    def allow(self, key: str) -> bool:",
        "    def _available(self, key: str, now: float) -> float:\n"
        "        tokens = self._tokens.get(key, float(self.capacity))\n"
        "        last = self._last.get(key, now)\n"
        "        elapsed = now - last\n"
        "        if elapsed < 0.0:\n"
        "            elapsed = 0.0\n"
        "        tokens = tokens + elapsed * self.refill_per_second\n"
        "        if tokens > self.capacity:\n"
        "            tokens = float(self.capacity)\n"
        "        return tokens\n\n"
        "    def retry_after(self, key: str) -> float:\n"
        "        tokens = self._available(key, self._clock())\n"
        "        if tokens >= 1.0:\n"
        "            return 0.0\n"
        "        return (1.0 - tokens) / self.refill_per_second\n\n"
        "    def allow(self, key: str) -> bool:")
    source.write_text(text, encoding="utf-8")
    report.write_text("# RG-impl\n\nAdded `retry_after` and a shared `_available` helper. The "
                      "existing suite passes unedited.\n", encoding="utf-8")
else:
    report.write_text(f"# {task} ({role})\n\nIndependent review reached the production path; "
                      "no task-relevant defect found.\n", encoding="utf-8")
'''


def sh(argv: list[str], **kw: Any) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, check=False, **kw)


def must(done: subprocess.CompletedProcess, what: str) -> str:
    if done.returncode != 0:
        raise SystemExit(f"REHEARSAL STOPPED at {what}:\n{done.stdout}\n{done.stderr}")
    return done.stdout.strip()


class Rehearsal:
    def __init__(self, into: Path) -> None:
        self.into = into.expanduser().resolve()
        self.project = self.into / "project"
        self.run = self.project / "DeepSeekAndDestroy/plans/demo/runs/r1"
        self.ledger = self.into / "ledger.json"
        self.graph = self.project / "change-graph.json"
        self.freezes = self.into / "freezes"
        self.consistency = self.into / "consistency"
        self.contracts = self.run / "contracts"
        self.log: list[dict[str, Any]] = []

        bin_dir = self.into / "fakebin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        fake = bin_dir / "opencode"
        fake.write_text(FAKE, encoding="utf-8")
        fake.chmod(0o755)
        home = self.into / "sealed-home"
        home.mkdir(parents=True, exist_ok=True)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("OPENCODE")}
        self.env["PATH"] = os.pathsep.join([str(bin_dir), "/usr/bin", "/bin"])
        self.env["HOME"] = str(home)
        if shutil.which("opencode", path=self.env["PATH"]) != str(fake):
            raise SystemExit("refusing to rehearse: `opencode` does not resolve to the fake")

    def note(self, step: str, detail: Any) -> None:
        self.log.append({"step": step, "detail": detail})
        print(f"  ok  {step}")

    def contract(self, task: str, candidate: str | None = None) -> Path:
        text = (CONTRACTS / f"{task}.md").read_text(encoding="utf-8")
        if candidate is not None:
            text = text.replace("<CANDIDATE>", candidate)
        elif "<CANDIDATE>" in text:
            raise SystemExit(f"{task} binds a candidate but none was supplied")
        target = self.contracts / f"{task}.md"
        target.write_text(text, encoding="utf-8")
        return target

    def bind(self, phase: str, task: str, contract: Path) -> None:
        """Bind a contract by whichever route its own kind requires.

        Candidate-bound execution — a contract that names a candidate and writes the project —
        enters through `pb_execution.py admit`, which authorizes and binds in one act. Everything
        else binds directly. The choice belongs to the contract, not to the caller.
        """
        sys.path.insert(0, str(SCRIPTS))
        from _contract import requires_admission
        if not requires_admission(contract.read_text(encoding="utf-8", errors="replace")):
            must(sh([sys.executable, SCRIPTS / "dsd_state.py", "bind-contract",
                     "--run-root", self.run, "--phase-id", phase, "--task-id", task,
                     "--contract", contract]), f"bind {phase}/{task}")
            return
        must(sh([sys.executable, SCRIPTS / "pb_execution.py", "admit",
                 "--run-root", self.run, "--phase-id", phase, "--task-id", task,
                 "--contract", contract, "--graph", self.graph, "--ledger", self.ledger,
                 "--project-root", self.project, "--consistency", self.consistency]),
             f"admit {phase}/{task}")

    def work(self, phase: str, task: str, role: str, *,
             inputs: "list[Path] | None" = None) -> Path:
        """One attempt on a task, by one role. Returns the gate the parent could accept against.

        Reviews are *later attempts on the same task and the same contract*, not separate tasks —
        which is what the shipped spec-reflection slice does and what the first version of this
        rehearsal got wrong. A reviewer gate bound to some other task's contract is refused with
        "source gate is not bound to task.current_contract", and rightly.

        `inputs` is how the producer's **report** reaches the reviewer: an exact artifact, named by
        authority. Not its session, not its reasoning.
        """
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
        attempt = state["phases"][phase]["tasks"][task]["current_attempt"]
        event = Path(attempt["event_dir"])
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

    def run_all(self) -> dict[str, Any]:
        # -- the specification, and an independent challenge of it, on one task ------------------
        self.bind("design", "RG-spec", self.contract("RG-spec"))
        author = self.work("design", "RG-spec", "spec-author")
        self.note("spec authored", {"gate": str(author)})

        # The producer's own gate must not be acceptable as its own review.
        refused = self.accept("design", "RG-spec", author)
        if refused.returncode == 0:
            raise SystemExit("the author's own gate was accepted as its own review")
        self.note("author's own gate refused as its own review",
                  {"stderr": refused.stderr.strip()[:120]})

        reflector = self.work("design", "RG-spec", "spec-reflector",
                              inputs=[author.parent / "report.md"])
        must(self.accept("design", "RG-spec", reflector), "accept design/RG-spec")
        self.note("specification accepted against the reflector's gate", {})

        must(sh([sys.executable, SCRIPTS / "pb_ledger.py", "record",
                 "--run-root", self.run, "--phase-id", "design", "--task-id", "RG-spec",
                 # Absolute: `--artifact` resolves against the caller's cwd, not the project root.
                 "--artifact", self.project / "spec.md",
                 "--ledger", self.ledger]), "ledger record spec.md")
        self.note("spec.md recorded in the ledger", {})

        graph = json.loads(must(sh([sys.executable, SCRIPTS / "pb_graph.py", "validate",
                                    "--graph", self.graph, "--ledger", self.ledger,
                                    "--project-root", self.project]), "graph validate"))
        self.note("graph satisfied", {"findings": [f["code"] for f in graph.get("findings", [])]})

        frozen = json.loads(must(sh([sys.executable, SCRIPTS / "pb_freeze.py", "create",
                                     "--graph", self.graph, "--ledger", self.ledger,
                                     "--project-root", self.project, "--into", self.freezes]),
                                 "freeze create"))
        candidate = (frozen.get("identity") or frozen.get("candidate")
                     or frozen.get("freeze", {}).get("identity"))
        self.note("candidate frozen", {"candidate": candidate, "keys": sorted(frozen)})

        # -- aggregate consistency ---------------------------------------------------------------
        self.bind("design", "RG-consistency", self.contract("RG-consistency", candidate))
        consistency = self.work("design", "RG-consistency", "spec-reflector")
        must(self.accept("design", "RG-consistency", consistency), "accept design/RG-consistency")
        must(sh([sys.executable, SCRIPTS / "pb_consistency.py", "record",
                 "--run-root", self.run, "--phase-id", "design", "--task-id", "RG-consistency",
                 "--freeze", self.freezes / f"{candidate}.json", "--into", self.consistency]),
             "consistency record")
        status = json.loads(must(sh([sys.executable, SCRIPTS / "pb_consistency.py", "status",
                                     "--into", self.consistency, "--candidate", candidate]),
                                 "consistency status"))
        self.note("aggregate accepted and readable", status)

        # -- candidate-bound implementation, then a fresh review ---------------------------------
        self.bind("build", "RG-impl", self.contract("RG-impl", candidate))
        impl = self.work("build", "RG-impl", "implementer")
        self.note("implementation attempted", {"gate": str(impl)})

        review = self.work("build", "RG-impl", "reviewer", inputs=[impl.parent / "report.md"])
        must(self.accept("build", "RG-impl", review), "accept build/RG-impl")
        self.note("implementation accepted against the reviewer's gate", {})

        return {"candidate": candidate, "log": self.log}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--into", type=Path, required=True)
    args = ap.parse_args()
    result = Rehearsal(args.into).run_all()
    print(json.dumps({"rehearsal": "complete", "candidate": result["candidate"],
                      "steps": len(result["log"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

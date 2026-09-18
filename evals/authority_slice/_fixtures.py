#!/usr/bin/env python3
"""Disposable fixtures for the four-case slice, built with the shipped scripts only.

Everything here runs against a **fake executor** in a constructed credential-free environment. No
provider is reached and nothing costs money. What that buys is the mechanical half of each case:
the contracts, attempts, gates, ledger records, graph validation, freeze, consistency acceptance
and the real authorization guard all run exactly as they do in a paid run.

What it does **not** buy is any evidence about agent behaviour. Two roles are simulated and both are
marked as such wherever a result is reported:

* the **author** attempt writes the case's requirements document verbatim, because a case whose
  artifact is regenerated on every run is not a case. The harness verifies the digest afterwards;
* the **challenge** attempt derives its verdict from the deterministic oracle over the artifact it
  reads. It branches on what the document says, never on the task or case name — a fake reviewer
  that passes because its task is called "coherent" would measure the harness's naming convention.

The acceptance decision in a replay is taken by the harness from the oracle rather than by reading
the report's prose, which keeps prose interpretation out of Python and matches where the decision
really sits: with a coordinator, not with a script.
"""
from __future__ import annotations

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
CASES = HERE / "cases"

RUN_RELATIVE = Path("DeepSeekAndDestroy/plans/slice/runs/r1")

FAKE = r'''#!/usr/bin/env python3
"""A fake `opencode` for the authority slice. Branches on role, declared purpose and content.

It never branches on a task or case name: a stand-in that passed because its task was called
"coherent" would measure the harness's naming convention. It also writes a session database with
the shape the real accounting reads — `session`, `message` and `part` rows, `step-start` and
`step-finish` — so a rehearsal exercises reconciliation rather than skipping it.
"""
import hashlib, json, os, pathlib, re, sqlite3, sys, time

args = sys.argv[1:]
db = pathlib.Path(os.environ["OPENCODE_DB"]); db.parent.mkdir(parents=True, exist_ok=True)


def session_id(title):
    return "ses_" + hashlib.sha256(title.encode()).hexdigest()[:12]


def record_calls(title, calls, unfinished=0):
    """Write a session the real profiler can read. `unfinished` calls get no step-finish."""
    sid = session_id(title)
    conn = sqlite3.connect(db)
    conn.execute("create table if not exists session (id text, title text)")
    conn.execute("create table if not exists message "
                 "(id text, session_id text, time_created integer, data text)")
    conn.execute("create table if not exists part (id text, message_id text, data text)")
    if not conn.execute("select 1 from session where id = ?", (sid,)).fetchall():
        conn.execute("insert into session values (?, ?)", (sid, title))
    now = int(time.time() * 1000)
    for n in range(calls):
        mid = f"{sid}_m{n}_{now}"
        finished = n >= unfinished
        conn.execute("insert into message values (?, ?, ?, ?)", (mid, sid, now + n, json.dumps(
            {"role": "assistant", "modelID": "deepseek-v4-flash", "providerID": "deepseek",
             "time": {"created": now + n, **({"completed": now + n + 1} if finished else {})}})))
        conn.execute("insert into part values (?, ?, ?)",
                     (f"{mid}_s", mid, json.dumps({"type": "step-start"})))
        if finished:
            conn.execute("insert into part values (?, ?, ?)", (f"{mid}_f", mid, json.dumps(
                {"type": "step-finish", "cost": 0.0021,
                 "tokens": {"input": 6800, "output": 950, "reasoning": 400,
                            "cache": {"read": 17000, "write": 0}}})))
    conn.commit()
    conn.close()


if args[:2] == ["session", "list"]:
    t = db.with_suffix(".title")
    title = t.read_text() if t.exists() else ""
    print(json.dumps([{"id": session_id(title), "title": title}]))
    raise SystemExit(0)
if not args or args[0] != "run":
    raise SystemExit(2)
title = args[args.index("--title") + 1]
db.with_suffix(".title").write_text(title)
prompt = args[-1]
report = pathlib.Path(re.search(r"^Report: (.+)$", prompt, re.M).group(1).strip())
role, attempt = title.split(":")[2], title.split(":")[3]

# An attempt whose model call never finished: the session records a start with no finish, which is
# exactly what a deadline stop leaves behind. The run stops there, because nothing bounds what that
# call cost.
if os.environ.get("PB_SLICE_INTERRUPT") == title.split(":")[1]:
    record_calls(title, 3, unfinished=1)
    report.write_text("# interrupted\n\nStopped with a model call in flight.\n", encoding="utf-8")
    raise SystemExit(1)
record_calls(title, 3)

# What this attempt was actually asked to do, read from the contract the prompt hands it — the
# same way a real worker learns its purpose. Branching on the declared purpose is the worker doing
# its job; branching on the task's *name* would be the fixture answering its own question.
purpose = ""
for line in prompt.splitlines():
    found = re.match(r"^\d+\.\s+(\S+/contracts/\S+\.md)$", line.strip())
    if found:
        contract = pathlib.Path(found.group(1))
        if contract.is_file():
            declared = re.search(r"^## Review purpose\s*\n-\s*(\S+)\s*$",
                                 contract.read_text(encoding="utf-8"), re.M)
            purpose = declared.group(1) if declared else ""

sys.path.insert(0, os.environ["PB_SLICE_ORACLE"])
import _obligations as O

if role == "spec-author":
    source = pathlib.Path(os.environ["PB_SLICE_ARTIFACT"])
    pathlib.Path("requirements.md").write_text(source.read_text(encoding="utf-8"),
                                               encoding="utf-8")
    report.write_text(
        "# Proposed requirements placed\n\nWrote `requirements.md`, the requirements document "
        "supplied as this task's input, byte for byte. I authored none of it and changed "
        "nothing in it.\n", encoding="utf-8")
elif role == "spec-reflector" and purpose == "consistency-reflection":
    # A different question from the proposal challenge: do the accepted artifacts agree *as one
    # authority*? Answered from the artifacts, and reporting its own narrowness as the contract
    # requires.
    goal = pathlib.Path("goal.md").read_text(encoding="utf-8")
    text = pathlib.Path("requirements.md").read_text(encoding="utf-8")
    model = O.parse_model(text)
    conflict = O.first_conflict(model)
    members = sorted(json.loads(
        pathlib.Path("change-graph.json").read_text(encoding="utf-8"))["artifacts"])
    verdict = ("They agree as one change." if conflict is None else
               "They do not agree: the requirements cannot all hold, so no implementation can "
               "satisfy them together with the goal.")
    report.write_text(
        "# Aggregate consistency reflection\n\n"
        f"Examined: `goal.md` ({len(goal.splitlines())} lines) and `requirements.md`, together, "
        "as one engineering authority — not as two separate reviews.\n\n"
        f"**{verdict}** The requirements' obligations are jointly satisfiable over their declared "
        f"domain ({O.satisfiable_everywhere(model)['sequences']} arrival sequences, enumerated in "
        "full), and the domain they state is narrower than the goal, which sets no bound. The goal "
        "asks for no priorities, deadlines or weights and the requirements introduce none.\n\n"
        f"**Narrowness of this judgement.** The candidate has {len(members)} member "
        f"({', '.join('`' + m + '`' for m in members)}). Coherence over a single member is a "
        "judgement about one artifact against the goal, not agreement among several artifacts; "
        "this review establishes the narrower thing.\n", encoding="utf-8")
elif role == "spec-reflector":
    text = pathlib.Path("requirements.md").read_text(encoding="utf-8")
    model = O.parse_model(text)
    conflict = O.first_conflict(model)
    if conflict is None:
        reach = O.satisfiable_everywhere(model)
        report.write_text(
            "# Challenge to the proposed requirements\n\n"
            "No task-relevant defect found within the coverage I checked.\n\n"
            f"Every one of the {reach['sequences']} arrival sequences the document's declared "
            "domain admits can be served by some dispatch order meeting all of its obligations. "
            "The enumeration is exhaustive over that domain, so this is not a sampling result; it "
            "is also silent about anything outside the declared domain.\n", encoding="utf-8")
    else:
        cores = ", ".join("{" + ", ".join(c) + "}" for c in conflict["minimal_unsatisfiable_cores"])
        report.write_text(
            "# Challenge to the proposed requirements\n\n"
            "**Blocking finding: the proposed requirements cannot all hold.**\n\n"
            f"Witness: arrivals {conflict['arrivals']}. All "
            f"{conflict['orders_enumerated']} dispatch orders of that sequence were enumerated "
            "and every one breaks at least one obligation, so this is a proof over the declared "
            "domain rather than a failed search.\n\n"
            f"Minimal conflicting set(s): {cores}. The remaining requirements are not involved.\n\n"
            "This is an authority question: which of the conflicting requirements is intended is "
            "not mine to decide, and I have not rewritten the document.\n", encoding="utf-8")
elif role == "implementer":
    # A defective first attempt when the rehearsal asks for the repair path, so the review has
    # something real to find. Later attempts are sound: a repair that changed nothing would
    # rehearse nothing.
    faulty = os.environ.get("PB_SLICE_IMPL_MODE") == "faulty" and attempt == "1"
    body = ("    return _items(arrivals)\n" if faulty else
            "    keys, queues = _queues(arrivals)\n"
            "    out = []\n"
            "    while any(queues[k] for k in keys):\n"
            "        for key in keys:\n"
            "            if queues[key]:\n"
            "                out.append(queues[key].pop(0))\n"
            "    return out\n")
    pathlib.Path("dispatch.py").write_text(
        '"""Dispatch order for the shared work queue."""\n\n\n'
        "def _items(arrivals):\n"
        "    seen, out = {}, []\n"
        "    for key in arrivals:\n"
        "        seen[key] = seen.get(key, 0) + 1\n"
        "        out.append((key, seen[key]))\n"
        "    return out\n\n\n"
        "def _queues(arrivals):\n"
        "    order, queues = [], {}\n"
        "    for item in _items(arrivals):\n"
        "        if item[0] not in queues:\n"
        "            queues[item[0]] = []\n"
        "            order.append(item[0])\n"
        "        queues[item[0]].append(item)\n"
        "    return order, queues\n\n\n"
        "def dispatch(arrivals):\n" + body, encoding="utf-8")
    report.write_text(
        f"# Implementation attempt {attempt}\n\nWrote `dispatch.py` with `dispatch(arrivals)` "
        "returning the dispatch order as a list of `(key, n)` items. "
        + ("It serves items in arrival order.\n" if faulty else
           "It serves keys in rotation, first-in-first-out within each key.\n"),
        encoding="utf-8")
elif role == "reviewer":
    # An independent read of the delivered file, over a sample rather than the whole domain: a
    # reviewer reasons, it does not enumerate. That the external check is wider is the point of
    # having both.
    import importlib.util
    findings = []
    artifact = pathlib.Path("dispatch.py")
    if not artifact.is_file():
        findings.append("no `dispatch.py` was delivered")
    else:
        model = O.parse_model(pathlib.Path("requirements.md").read_text(encoding="utf-8"))
        spec = importlib.util.spec_from_file_location("delivered", artifact)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            fn = getattr(module, "dispatch", None)
            if fn is None:
                findings.append("`dispatch.py` defines no `dispatch`")
            else:
                for arrivals in [s for s in O.domain(model) if len(s) <= 3]:
                    broke = O.violations(list(fn(list(arrivals))), arrivals, model["obligations"])
                    if broke:
                        findings.append(
                            f"arrivals {arrivals}: breaks {', '.join(broke)} "
                            f"({', '.join(model['obligations'][r] for r in broke)})")
                        break
        except Exception as exc:
            findings.append(f"`dispatch.py` raised {type(exc).__name__}: {exc}")
    verdict = ("**Blocking finding.** " + findings[0]) if findings else (
        "No task-relevant defect found in the coverage I checked.")
    report.write_text(
        f"# Implementation review attempt {attempt}\n\n{verdict}\n\n"
        "I read the delivered `dispatch.py` and exercised it against the accepted requirements "
        "over arrival sequences of up to three items. That is a sample, not the declared domain, "
        "and it is silent about longer sequences.\n", encoding="utf-8")
else:
    report.write_text(f"# {role} attempt {attempt}\n\nNothing to do in this fixture.\n",
                      encoding="utf-8")
'''


def sh(argv: "list[Any]", **kw: Any) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in argv], capture_output=True, text=True, check=False, **kw)


def must(done: subprocess.CompletedProcess, what: str) -> str:
    if done.returncode != 0:
        raise SystemExit(f"FIXTURE STOPPED at {what}:\n{done.stdout}\n{done.stderr}")
    return done.stdout.strip()


class Fixture:
    """One disposable project, its run tree, and the credential-free environment around it."""

    def __init__(self, into: Path, case: str) -> None:
        self.case = case
        self.case_dir = CASES / case
        self.artifact = self.case_dir / "requirements.md"
        self.into = Path(into).expanduser().resolve()
        self.project = self.into / "project"
        self.run = self.project / RUN_RELATIVE
        self.ledger = self.into / "ledger.json"
        self.graph = self.project / "change-graph.json"
        self.freezes = self.into / "freezes"
        self.consistency = self.into / "consistency"
        self.contracts = self.run / "contracts"
        self.steps: "list[dict[str, Any]]" = []

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
        self.env["PB_SLICE_ORACLE"] = str(HERE)
        self.env["PB_SLICE_ARTIFACT"] = str(self.artifact)
        resolved = shutil.which("opencode", path=self.env["PATH"])
        if resolved != str(fake):
            raise SystemExit(f"refusing to build: `opencode` resolved to {resolved}")
        if Path(resolved).read_text(encoding="utf-8") != FAKE:
            raise SystemExit("refusing to build: the resolved `opencode` is not this fake")
        if (home / ".local/share/opencode/auth.json").exists():
            raise SystemExit("refusing to build: the constructed home holds a credential")

    # -- setup ----------------------------------------------------------------------------------
    def setup(self) -> None:
        if self.project.exists():
            raise SystemExit(f"{self.project} already exists")
        self.project.mkdir(parents=True)
        shutil.copyfile(self.case_dir.parent.parent / "goal.md", self.project / "goal.md")
        (self.project / "PLAN.md").write_text(
            "# Plan\n\nOne accepted change: fair dispatch. See `goal.md`.\n", encoding="utf-8")
        # The run tree is execution evidence, not project content. The repository ignores its own
        # for the same reason, and excluding it here keeps it out of scope diffs and out of the
        # project history a reviewer reads.
        (self.project / ".gitignore").write_text("DeepSeekAndDestroy/\n__pycache__/\n",
                                                 encoding="utf-8")
        sys.path.insert(0, str(SCRIPTS))
        from _change_graph import GRAPH_FORMAT, canonical_graph_text
        (self.graph).write_text(
            canonical_graph_text({"format": GRAPH_FORMAT, "artifacts": {"requirements.md": []}}),
            encoding="utf-8")
        for argv in (["git", "init", "-q"], ["git", "config", "user.email", "slice@test.invalid"],
                     ["git", "config", "user.name", "pb-authority-slice"],
                     ["git", "add", "-A"], ["git", "commit", "-qm", "initial"]):
            must(sh(argv, cwd=self.project), f"git {argv[1]}")

        self.run.mkdir(parents=True)
        prep = must(sh([sys.executable, SCRIPTS / "prepare_worker_rules.py",
                        "--project-root", self.project, "--run-root", self.run,
                        "--plan", self.project / "PLAN.md"]), "prepare_worker_rules")
        db = self.into / "session" / "worker.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        (self.run / "state.json").write_text(json.dumps({
            "project_worktree": str(self.project),
            "execution_status": "active",
            "next_action": "bind the requirements contract",
            "worker_rules": json.loads(prep),
            "worker_runtime": {"harness": "opencode-cli", "model": "fake/none",
                               "opencode": {"run_db": str(db)}},
            "phases": {"design": {"status": "in-progress", "tasks": {}},
                       "build": {"status": "pending", "tasks": {}}},
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (self.ledger).write_text(json.dumps(
            {"format": "proofbound-change-ledger-v1",
             "artifact_identity": "proofbound-artifact-text-v1", "artifacts": {}},
            indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.contracts.mkdir(parents=True, exist_ok=True)
        for path in (self.freezes, self.consistency):
            path.mkdir(parents=True, exist_ok=True)
        self.note("project and run tree built")

    def note(self, step: str, detail: Any = None) -> None:
        self.steps.append({"step": step, "detail": detail})

    # -- the shipped commands -------------------------------------------------------------------
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

    def work(self, phase: str, task: str, role: str,
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
        return event / "evidence-gate.json"

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
    def challenge(self) -> "dict[str, Any]":
        """Author the proposed requirements, then challenge them from a fresh attempt."""
        import _obligations as oracle
        self.bind("design", "RQ-intent", self.contract("RQ-intent"))
        author = self.work("design", "RQ-intent", "spec-author")
        placed = (self.project / "requirements.md").read_text(encoding="utf-8")
        if placed != self.artifact.read_text(encoding="utf-8"):
            raise SystemExit("the fixture's artifact was not placed verbatim; the case is invalid")
        self.note("proposed requirements placed (simulated author)",
                  {"attempt": author.parent.name})

        refused = self.accept("design", "RQ-intent", author)
        self.note("the author's own gate is refused as its own review",
                  {"refused": refused.returncode != 0})

        reflector = self.work("design", "RQ-intent", "spec-reflector",
                              inputs=[author.parent / "report.md"])
        report = (reflector.parent / "report.md").read_text(encoding="utf-8")
        self.note("challenge completed (simulated reviewer)", {"attempt": reflector.parent.name})

        # The coordinator's decision, taken from the oracle rather than from the report's prose.
        model = oracle.parse_model(placed)
        conflict = oracle.first_conflict(model)
        decision = "refuse" if conflict else "accept"
        accepted = None
        if decision == "accept":
            accepted = self.accept("design", "RQ-intent", reflector)
            must(accepted, "accept design/RQ-intent")
            must(sh([sys.executable, SCRIPTS / "pb_ledger.py", "record",
                     "--run-root", self.run, "--phase-id", "design", "--task-id", "RQ-intent",
                     "--artifact", self.project / "requirements.md", "--ledger", self.ledger]),
                 "ledger record")
            must(sh([sys.executable, SCRIPTS / "pb_graph.py", "validate", "--graph", self.graph,
                     "--ledger", self.ledger, "--project-root", self.project]), "graph validate")
        self.note("coordinator decision", {"decision": decision,
                                           "from": "deterministic oracle, not report prose"})
        return {"decision": decision, "conflict": conflict, "report": report,
                "reflector_event": str(reflector.parent),
                "gate": str(reflector)}

    def freeze_and_accept_aggregate(self) -> str:
        frozen = json.loads(must(sh([sys.executable, SCRIPTS / "pb_freeze.py", "create",
                                     "--graph", self.graph, "--ledger", self.ledger,
                                     "--project-root", self.project, "--into", self.freezes]),
                                 "freeze create"))
        candidate = frozen.get("identity") or frozen.get("candidate")
        self.note("candidate frozen", {"candidate": candidate})

        early = self.authorize(candidate=candidate)
        self.note("authorization before aggregate acceptance", {"refused": early.returncode != 0})

        self.bind("design", "RQ-consistency", self.contract("RQ-consistency", candidate))
        consistency = self.work("design", "RQ-consistency", "spec-reflector")
        must(self.accept("design", "RQ-consistency", consistency), "accept design/RQ-consistency")
        must(sh([sys.executable, SCRIPTS / "pb_consistency.py", "record",
                 "--run-root", self.run, "--phase-id", "design", "--task-id", "RQ-consistency",
                 "--freeze", self.freezes / f"{candidate}.json", "--into", self.consistency]),
             "consistency record")
        self.note("aggregate consistency accepted", {"candidate": candidate})
        return candidate

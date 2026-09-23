"""Configuration qualification: graders, frozen plans, comparisons, and one complete offline path.

Graders are checked against expectations computed by hand from the obligation definitions, never
by round-tripping their own output. The offline path goes through the public CLIs end to end —
select a profile, freeze a plan, replay with stand-ins through `pb_workflow.py`, relocate the
result, re-derive every grade, then tamper with it — and shows that defective stand-in output and
missing evidence do not count as a dimension met. Stand-ins establish mechanics only.
"""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))
sys.path.insert(0, str(ROOT / "scripts"))

import _qualify                                                            # noqa: E402
import _compare                                                            # noqa: E402

CLI = ROOT / "evals" / "pb_qualify.py"


class FindingGraders(unittest.TestCase):
    """Hand-computed. Arrivals a,a,b make items a1,a2,b1; fifo-global forces exactly that order,
    and round-robin forbids serving a twice while b1 waits — so no order satisfies both."""

    def setUp(self):
        self.contradictory = _qualify._model("contradictory")
        self.coherent = _qualify._model("coherent")

    def test_a_correct_finding_and_its_witness_are_graded_apart(self):
        got = _qualify.grade_requirement_findings(
            [{"requirements": ["R2", "R3"], "witness": ["a", "a", "b"]},
             {"requirements": ["R2", "R3"], "witness": ["a", "b"]},      # a1,b1 satisfies both
             {"requirements": ["R1", "R4"], "witness": ["a"]},           # always satisfiable
             {"requirements": ["R2", "R3"], "witness": ["z", "z"]},      # outside the domain
             {"requirements": ["R9"], "witness": ["a"]},                 # not a requirement
             "not an object"], self.contradictory)
        rows = [(r["correct"], r["witness_reproduces"]) for r in got["rows"]]
        self.assertEqual(rows, [(True, True), (True, False), (False, False), (True, False),
                                (False, False), (False, False)])
        self.assertEqual((got["substantiated"], got["correct_but_unsubstantiated"], got["false"]),
                         (1, 2, 3))

    def test_the_sound_control_turns_any_claimed_conflict_into_a_false_finding(self):
        got = _qualify.grade_requirement_findings(
            [{"requirements": ["R2", "R3"], "witness": ["a", "a", "b"]}], self.coherent)
        self.assertEqual((got["correct"], got["false"]), (0, 1),
                         "fifo-per-key and round-robin both hold for a1,b1,a2")

    def test_implementation_findings_reproduce_on_the_delivered_bytes(self):
        tmp = Path(tempfile.mkdtemp(prefix="pb-impl-findings-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        fifo = tmp / "fifo.py"
        fifo.write_text(_qualify._dispatch_source("global-fifo"))
        got = _qualify.grade_implementation_findings(
            [{"requirements": ["R3"], "witness": ["a", "a", "b"]},  # a1,a2,b1: a twice, b waits
             {"requirements": ["R3"], "witness": ["a", "b"]},       # a1,b1: nothing violated
             {"requirements": ["R2"], "witness": ["a", "a"]}],      # per-key order is kept
            fifo, self.coherent)
        self.assertTrue(got["defect_present"])
        self.assertEqual([(r["correct"], r["witness_reproduces"]) for r in got["rows"]],
                         [(True, True), (True, False), (False, False)])
        sound = tmp / "sound.py"
        sound.write_text(_qualify._dispatch_source("round-robin"))
        control = _qualify.grade_implementation_findings(
            [{"requirements": ["R3"], "witness": ["a", "a", "b"]}], sound, self.coherent)
        self.assertFalse(control["defect_present"])
        self.assertEqual((control["correct"], control["false"]), (0, 1))

    def test_a_report_without_a_findings_block_is_ungradeable_not_clean(self):
        self.assertEqual(_qualify.parse_findings("I found nothing wrong."),
                         (None, "the report carries no fenced json block with a `findings` list"))
        self.assertEqual(_qualify.parse_findings('```json\n{"verdict": "ok"}\n```')[0], None)
        self.assertEqual(_qualify.parse_findings('x\n```json\n{"findings": []}\n```\n')[0], [])


class ToolLoopGrader(unittest.TestCase):
    MARK = "abc123"

    def rows(self, *, finishes, tools, tokens=(10, 5)):
        out = [{"type": "tool", "tool_status": status, "part_id": f"t{i}"}
               for i, status in enumerate(tools)]
        out += [{"type": "step-finish", "time_created": i, "input": tokens[0],
                 "output": tokens[1], "part_id": f"f{i}"} for i in range(finishes)]
        return out

    def grade(self, rows, artifact=f"# R\n\nQUALIFICATION-TOOL-LOOP {MARK}\n", gate=True):
        return _qualify.grade_tool_loop(rows, artifact, self.MARK, {"integrity_ok": gate})

    def test_pass_needs_a_completed_tool_a_continuation_the_bytes_and_a_gate(self):
        self.assertEqual(self.grade(self.rows(finishes=2, tools=["completed"]))["outcome"], "pass")
        for why, got in (
                ("no continuation", self.grade(self.rows(finishes=1, tools=["completed"]))),
                ("tool failed", self.grade(self.rows(finishes=2, tools=["error"]))),
                ("marker absent", self.grade(self.rows(finishes=2, tools=["completed"]),
                                             artifact="# R\n")),
                ("marker not on its own line",
                 self.grade(self.rows(finishes=2, tools=["completed"]),
                            artifact=f"QUALIFICATION-TOOL-LOOP {self.MARK}x\n")),
                ("gate not interpretable", self.grade(self.rows(finishes=2, tools=["completed"]),
                                                      gate=False))):
            with self.subTest(why):
                self.assertEqual(got["outcome"], "protocol-failure")

    def test_zero_token_retries_are_infrastructure_and_zero_usage_is_unknown(self):
        storm = self.grade(self.rows(finishes=40, tools=[], tokens=(0, 0)), artifact="# R\n")
        self.assertEqual(storm["outcome"], _qualify.INFRASTRUCTURE)
        self.assertFalse(storm["gradeable"])
        unreported = self.grade(self.rows(finishes=2, tools=["completed"], tokens=(0, 0)))
        self.assertEqual(unreported["outcome"], "pass")
        self.assertTrue(unreported["usage_reported"].startswith("unknown"))


class Plans(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-plans-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_a_live_plan_needs_authorization_and_limits(self):
        with self.assertRaises(_qualify.QualificationError):
            _qualify.build_plan(profile="deepseek-v4-flash-high", mode="live",
                                cases=["tool-loop"])
        with self.assertRaises(_qualify.QualificationError):
            _qualify.build_plan(profile="deepseek-v4-flash-high", mode="live",
                                cases=["tool-loop"], owner_authorization="yes")
        with self.assertRaises(_qualify.QualificationError):
            _qualify.build_plan(profile="deepseek-v4-flash-high", mode="live",
                                cases=["authority-recovery"], owner_authorization="yes",
                                aggregate_limit=1, reserve=.1)
        plan = _qualify.build_plan(profile="deepseek-v4-flash-high", mode="live",
                                   cases=["tool-loop"], owner_authorization="TEST",
                                   aggregate_limit=.5, reserve=.1)
        self.assertEqual(plan["allocation"]["order"], ["tool-loop--marker"])

    def test_an_unreachable_local_endpoint_prepares_nothing(self):
        profile = self.tmp / "down.json"
        import socket
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        profile.write_text(json.dumps({
            "format": "proofbound-worker-profile-v1", "id": "local-down",
            "kind": "local-openai-compatible", "endpoint": f"http://127.0.0.1:{port}/v1",
            "model": "m", "limits": {"context": 8192, "output": 1024}, "tool_call": True}))
        executor = self.tmp / "opencode"
        executor.write_text("#!/bin/sh\necho 1.18.29\n")
        executor.chmod(0o755)
        plan_dir = self.tmp / "live-plan"
        subprocess.run([sys.executable, str(CLI), "plan", "--worker-profile", str(profile),
                        "--mode", "live", "--case", "tool-loop", "--owner-authorization",
                        "TEST ONLY: never driven", "--executor", str(executor),
                        "--into", str(plan_dir)], check=True, capture_output=True)
        runs = self.tmp / "runs"
        cp = subprocess.run([sys.executable, str(CLI), "prepare-live", "--plan", str(plan_dir),
                             "--into", str(runs)], capture_output=True, text=True,
                            stdin=subprocess.DEVNULL)
        self.assertEqual(cp.returncode, 2, cp.stdout)
        error = json.loads(cp.stdout)["error"]
        self.assertIn("is not reachable", error)
        self.assertIn("nothing prepared", error)
        self.assertFalse(runs.exists())

    def test_prepare_live_launches_nothing_and_grade_records_undriven_runs_as_not_run(self):
        """Readiness passes against a stand-in endpoint, so this exercises preparation and grading
        only: nothing is launched, no model is involved, and nothing live is claimed."""
        if _qualify.pinned_executor() is None or not _qualify.sandbox_available():
            self.skipTest("needs the pinned executor and sandbox-exec on this host")
        from _stand_in_endpoint import StandInEndpoint
        with StandInEndpoint(model="m") as endpoint:
            profile = self.tmp / "local.json"
            profile.write_text(json.dumps({
                "format": "proofbound-worker-profile-v1", "id": "local-undriven",
                "kind": "local-openai-compatible", "endpoint": endpoint.url, "model": "m",
                "limits": {"context": 8192, "output": 1024}, "tool_call": True}))
            plan_dir, runs = self.tmp / "live-plan", self.tmp / "runs"
            subprocess.run([sys.executable, str(CLI), "plan", "--worker-profile", str(profile),
                            "--mode", "live", "--case", "tool-loop", "--owner-authorization",
                            "TEST ONLY: prepared, never driven", "--executor",
                            str(_qualify.pinned_executor()), "--into", str(plan_dir)],
                           check=True, capture_output=True)
            prepared = subprocess.run([sys.executable, str(CLI), "prepare-live", "--plan",
                                       str(plan_dir), "--into", str(runs)], capture_output=True,
                                      text=True, stdin=subprocess.DEVNULL)
            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
            self.assertEqual(json.loads(prepared.stdout)["launched"], 0)
            self.assertEqual([r for r in endpoint.requests if r["method"] == "POST"], [])
        for trial in json.loads((runs / "live.json").read_text())["trials"]:
            config = json.loads((Path(trial["run"]) / "run-config.json").read_text())
            self.addCleanup(shutil.rmtree, Path(config["home"]).parent, True)
        graded = subprocess.run([sys.executable, str(CLI), "grade", "--plan", str(plan_dir),
                                 "--live", str(runs)], capture_output=True, text=True,
                                stdin=subprocess.DEVNULL)
        self.assertEqual(graded.returncode, 0, graded.stdout + graded.stderr)
        record = json.loads((runs / "result.json").read_text())
        self.assertEqual([t["status"] for t in record["trials"]], [_qualify.NOT_RUN])
        self.assertEqual(record["denominators"]["attempted"], 0)
        self.assertIn("not a rate", record["claim"])

    def test_a_frozen_plan_refuses_edits_and_a_changed_profile(self):
        profile = self.tmp / "local.json"
        raw = {"format": "proofbound-worker-profile-v1", "id": "local-plan",
               "kind": "local-openai-compatible", "endpoint": "http://127.0.0.1:18080/v1",
               "model": "m", "limits": {"context": 8192, "output": 1024}, "tool_call": True}
        profile.write_text(json.dumps(raw))
        plan = _qualify.build_plan(profile=str(profile), mode="replay", cases=["tool-loop"])
        (self.tmp / "p").mkdir()
        _qualify._write_json(self.tmp / "p" / "plan.json", plan)
        _qualify.assert_executable(_qualify.load_plan(self.tmp / "p"))
        profile.write_text(json.dumps({**raw, "limits": {"context": 8192, "output": 512}}))
        with self.assertRaises(_qualify.QualificationError) as caught:
            _qualify.assert_executable(plan)
        self.assertIn("limits.output", str(caught.exception))
        edited = {**plan, "cases": ["requirements-challenge"]}
        _qualify._write_json(self.tmp / "p" / "plan.json", edited)
        with self.assertRaises(_qualify.QualificationError):
            _qualify.load_plan(self.tmp / "p")

    def test_case_identity_follows_content_and_excludes_the_trial_nonce(self):
        before = _qualify.case_identity("requirements-challenge")
        self.assertEqual(_qualify.case_identity("requirements-challenge"), before)
        original = _qualify.CASES["requirements-challenge"]
        copy_of = self.tmp / "requirements.md"
        copy_of.write_bytes(_qualify.COHERENT.read_bytes() + b"\n")
        _qualify.CASES["requirements-challenge"] = {**original,
                                                    "fixtures": [copy_of, _qualify.CONTRADICTORY]}
        try:
            self.assertNotEqual(_qualify.case_identity("requirements-challenge"), before,
                                "one fixture byte is a different task")
        finally:
            _qualify.CASES["requirements-challenge"] = original
        goal = _qualify._goal("tool-loop", "marker")
        self.assertIn("{nonce}", goal, "the identity covers the template, never a trial's nonce")
        self.assertNotEqual(_qualify.trial_goal({"trial_id": "x", "case": "tool-loop",
                                                 "subject": "marker"}), goal)

def result(*, trials=None, **configuration):
    base = {"suite": "s1", "mode": "live", "control_plane": "cp", "interpreter": "3.10",
            "executor": "e1", "worker.profile_kind": "k", "worker.provider": "p1",
            "worker.endpoint": "provider-managed", "worker.model": "p1/m1",
            "worker.variant": "high", "worker.limits": "provider defaults",
            "worker.network": "unrestricted", "coordinator": "codex/gpt", "resources": "r1"}
    base.update(configuration)
    return {"configuration": base, "plan_digest": "d", "started_at": configuration.get("_t", "t"),
            "claim": "test", "denominators": {"planned": 1},
            "trials": trials or [{"trial_id": "tool-loop--marker", "case": "tool-loop",
                                  "case_identity": "c1", "subject": "marker", "variant": None,
                                  "status": "completed", "transport": "none",
                                  "outcome": {"outcome": "pass", "gradeable": True}}]}


class QualificationComparison(unittest.TestCase):
    def compare(self, a, b):
        return _compare.compare_qualification(a, b)

    def test_each_question_is_named_by_what_varied(self):
        cases = {
            "worker-profile": (dict(**{"worker.model": "p1/m2"}), True),
            "coordinator": (dict(coordinator="claude-code/opus"), True),
            "harness-treatment": (dict(control_plane="cp2"), True),
            "agent-system": (dict(executor="e2", **{"worker.model": "p1/m2"}), True),
            "replication": (dict(_t="t2"), False),
        }
        for question, (changes, controlled) in cases.items():
            with self.subTest(question):
                got = self.compare(result(), result(**changes))
                self.assertTrue(got["question"].startswith(question), got["question"])
                self.assertEqual(got["controlled"], controlled)
        bundle = self.compare(result(), result(**{"worker.provider": "p2",
                                                  "worker.model": "p2/m1"}))
        self.assertFalse(bundle["attributable_to_one_field"],
                         "a provider change riding with a model is a bundle")
        self.assertEqual(self.compare(result(), result())["question"].split(":")[0],
                         "the same record twice")

    def test_an_unrecorded_control_or_a_different_measurement_is_never_controlled(self):
        unknown = self.compare(result(coordinator=None), result(**{"worker.model": "p1/m2"}))
        self.assertFalse(unknown["controlled"])
        self.assertIn("coordinator", unknown["unverified_fields"])
        mixed = self.compare(result(), result(mode="replay", **{"worker.model": "p1/m2"}))
        self.assertIsNone(mixed["question"])
        self.assertFalse(mixed["controlled"])

    def test_tasks_pair_by_identity_and_missing_or_duplicate_trials_are_named(self):
        renamed = copy.deepcopy(result()["trials"])
        renamed[0]["trial_id"] = "renamed"
        paired = self.compare(result(), result(trials=renamed, **{"worker.model": "p1/m2"}))
        self.assertEqual(len(paired["paired"]), 1, "same identity, different name: paired")
        other = copy.deepcopy(renamed) + [{**renamed[0], "case_identity": "c2",
                                           "trial_id": "tool-loop--marker"}]
        got = self.compare(result(), result(trials=other + [other[0]],
                                            **{"worker.model": "p1/m2"}))
        self.assertEqual(got["only_in_b"], ["tool-loop--marker"],
                         "same name, different identity: not paired")
        self.assertEqual(got["duplicates"]["b"], ["renamed"])
        self.assertFalse(got["controlled"])

    def test_it_never_names_a_winner(self):
        text = _compare.render_qualification(self.compare(result(),
                                                          result(**{"worker.model": "p1/m2"})))
        blob = text.lower()
        for word in ("winner", "better", "best", "recommend", "rank", "score:"):
            self.assertNotIn(word, blob)
        self.assertIn("no ordering is computed", blob)


class CompleteOfflinePath(unittest.TestCase):
    """Select a profile, freeze a plan, replay through the front door, relocate, re-derive, tamper,
    compare. Stand-ins throughout; nothing here is evidence about a model."""

    ONLY = ["requirements-challenge--contradictory--found-with-witness",
            "requirements-challenge--coherent--invented",
            "dispatch-implementation--coherent--defective-accepted",
            "authority-recovery--never-earned--scripted",
            "authority-recovery--derived-record-deleted--scripted"]

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="pb-offline-path-"))
        plan = cls.tmp / "plan"
        cls.cli("plan", "--worker-profile", "deepseek-v4-flash-high", "--into", plan,
                "--deadline-seconds", 60)
        args = ["replay", "--plan", plan, "--into", cls.tmp / "result"]
        for trial in cls.ONLY:
            args += ["--only", trial]
        cls.replayed = cls.cli(*args)
        profile = cls.tmp / "local.json"
        profile.write_text(json.dumps({
            "format": "proofbound-worker-profile-v1", "id": "local-compare",
            "kind": "local-openai-compatible", "endpoint": "http://127.0.0.1:18080/v1",
            "model": "m", "limits": {"context": 8192, "output": 1024}, "tool_call": True}))
        cls.cli("plan", "--worker-profile", profile, "--into", cls.tmp / "plan-local",
                "--deadline-seconds", 60)
        cls.cli("replay", "--plan", cls.tmp / "plan-local", "--into", cls.tmp / "result-local",
                "--only", cls.ONLY[0], "--only", cls.ONLY[1])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    @classmethod
    def cli(cls, *args, expect=0):
        cp = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True,
                            text=True, stdin=subprocess.DEVNULL)
        if cp.returncode != expect:
            raise AssertionError(f"exit {cp.returncode}: {cp.stdout[-2000:]}{cp.stderr[-2000:]}")
        return json.loads(cp.stdout) if cp.stdout.lstrip().startswith("{") else cp.stdout

    def relocated(self, name):
        target = self.tmp / name
        shutil.copytree(self.tmp / "result", target)
        return target

    def test_the_replay_graded_as_declared_and_defects_do_not_count_as_met(self):
        self.assertEqual(self.replayed["replay_as_declared"]["not_as_declared"], [])
        self.assertEqual(self.replayed["replay_as_declared"]["as_declared"], len(self.ONLY))
        summary = self.replayed["summary"]
        self.assertIn("dispatch-implementation--coherent--defective-accepted",
                      summary["dispatch-implementation"]["not_met"])
        self.assertIn("requirements-challenge--coherent--invented",
                      summary["requirements-challenge"]["not_met"])
        self.assertEqual(summary["authority-recovery"]["met"], 2)
        record = json.loads((self.tmp / "result" / "result.json").read_text())
        self.assertIn("No model was qualified", record["claim"])
        self.assertEqual(record["denominators"]["planned"], len(self.ONLY))

    def test_every_grade_re_derives_after_relocation(self):
        report = self.cli("inspect", "--result", self.relocated("moved"))
        self.assertEqual(report["mismatches"], 0, report)
        self.assertEqual(len(report["checks"]), len(self.ONLY))

    def test_tampered_or_missing_evidence_is_reported_not_repaired(self):
        target = self.relocated("tampered")
        record = json.loads((target / "result.json").read_text())
        trials = {t["trial_id"]: t for t in record["trials"]}
        dispatch = target / trials[self.ONLY[2]]["evidence_dir"] / "artifacts" / "dispatch.py"
        dispatch.write_text(_qualify._dispatch_source("round-robin"))     # a "better" artifact
        report = target / trials[self.ONLY[0]]["evidence_dir"]
        next(report.rglob("requirements/attempts/spec-reflector-1/report.md")).unlink()
        got = self.cli("inspect", "--result", target, expect=1)
        status = {c["trial_id"]: c for c in got["checks"]}
        self.assertEqual(status[self.ONLY[2]]["status"], "mismatch")
        self.assertIn("artifacts/dispatch.py", status[self.ONLY[2]]["altered_files"])
        self.assertFalse(status[self.ONLY[2]]["grade_recomputes"])
        self.assertEqual(status[self.ONLY[0]]["status"], "mismatch")
        self.assertEqual(status[self.ONLY[3]]["status"], "ok")

    def test_a_retained_record_never_carries_a_credential_or_the_session_database(self):
        for path in (self.tmp / "result").rglob("*"):
            if path.is_file():
                with self.subTest(path=path.name):
                    self.assertNotEqual(path.suffix, ".db")
                    self.assertNotEqual(path.name, "auth.json")
                    self.assertNotEqual(path.name, "launch-prompt.txt")
                    self.assertNotEqual(path.name, "worker.log")

    def test_the_two_replays_compare_as_a_worker_profile_question_with_populations_named(self):
        got = self.cli("compare", self.tmp / "result", self.tmp / "result-local", "--json")
        self.assertTrue(got["question"].startswith("worker-profile"))
        self.assertFalse(got["controlled"], "the populations differ")
        self.assertEqual(sorted(got["only_in_a"]), sorted(self.ONLY[2:]))
        self.assertEqual(len(got["paired"]), 2)
        self.assertFalse(got["tokens_comparable"])
        text = self.cli("compare", self.tmp / "result", self.tmp / "result-local")
        self.assertIn("both results are replays", text)


if __name__ == "__main__":
    unittest.main()

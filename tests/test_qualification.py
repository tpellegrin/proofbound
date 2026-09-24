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


def call(session, message, created, *, reason, tools=(), tokens=(1000, 50)):
    """One model call as the pinned executor records it: one assistant message holding a
    `step-start`, its tool parts, and a `step-finish` carrying why the call ended. Shape observed
    in a real OpenCode 1.18.29 session; see `continuation()`."""
    rows = [{"session_id": session, "message_id": message, "part_id": f"{message}-start",
             "time_created": created, "type": "step-start"}]
    for n, (name, status, started, ended) in enumerate(tools):
        rows.append({"session_id": session, "message_id": message,
                     "part_id": f"{message}-tool{n}", "time_created": created, "type": "tool",
                     "tool": name, "tool_status": status, "tool_started": started,
                     "tool_ended": ended})
    rows.append({"session_id": session, "message_id": message, "part_id": f"{message}-finish",
                 "time_created": created, "type": "step-finish", "finish_reason": reason,
                 "input": tokens[0], "output": tokens[1]})
    return rows


class ToolLoopGrader(unittest.TestCase):
    """Continuation is decided by the executor's own sequence, and never by counting rows."""

    MARK = "abc123"
    ARTIFACT = f"# R\n\nQUALIFICATION-TOOL-LOOP {MARK}\n"

    def grade(self, rows, artifact=ARTIFACT, gate=True, **kw):
        return _qualify.grade_tool_loop(rows, artifact, self.MARK, {"integrity_ok": gate}, **kw)

    def loop(self, session="ses_a"):
        return (call(session, "msg_01", 100, reason="tool-calls",
                     tools=[("read", "completed", 110, 115)])
                + call(session, "msg_02", 120, reason="tool-calls",
                       tools=[("write", "completed", 125, 130)])
                + call(session, "msg_03", 140, reason="stop"))

    def test_an_actual_continuation_passes(self):
        got = self.grade(self.loop(), session_id="ses_a")
        self.assertEqual(got["outcome"], "pass")
        self.assertTrue(got["continuation_observed"])
        self.assertEqual([c["next_call"] for c in got["continuation"]["continued"]],
                         ["msg_02", "msg_03"])

    def test_the_external_reproduction_no_longer_passes(self):
        """Finished calls at 1 and 2, the only completed tool at 3: nothing followed the tool."""
        rows = [{"type": "step-finish", "time_created": 1, "input": 10, "output": 5,
                 "part_id": "f1"},
                {"type": "step-finish", "time_created": 2, "input": 10, "output": 5,
                 "part_id": "f2"},
                {"type": "tool", "tool_status": "completed", "time_created": 3, "part_id": "t1"}]
        got = self.grade(rows)
        self.assertNotEqual(got["outcome"], "pass")
        self.assertIsNone(got["continuation_observed"])

    def test_calls_that_precede_the_tool_are_not_its_continuation(self):
        rows = (call("s", "msg_01", 1, reason="stop") + call("s", "msg_02", 2, reason="stop")
                + call("s", "msg_03", 3, reason="tool-calls",
                       tools=[("write", "completed", 4, 5)]))
        got = self.grade(rows, session_id="s")
        self.assertEqual(got["outcome"], "protocol-failure")
        self.assertIs(got["continuation_observed"], False)

    def test_a_call_in_another_session_does_not_continue_this_one(self):
        rows = (call("ses_a", "msg_01", 1, reason="tool-calls",
                     tools=[("write", "completed", 2, 3)])
                + call("ses_b", "msg_02", 5, reason="stop"))
        self.assertIs(self.grade(rows, session_id="ses_a")["continuation_observed"], False)
        self.assertIsNone(self.grade(rows)["continuation_observed"],
                          "two sessions and no identified one decide nothing")

    def test_duplicate_events_and_recorded_anomalies_decide_nothing(self):
        rows = self.loop()
        self.assertEqual(self.grade(rows + [dict(rows[1])], session_id="ses_a")["outcome"],
                         "insufficient-evidence")
        self.assertEqual(self.grade(rows, session_id="ses_a",
                                    anomalies=[{"kind": "duplicate-part-id"}])["outcome"],
                         "insufficient-evidence")

    def test_a_failed_tool_is_not_continued(self):
        rows = (call("s", "msg_01", 1, reason="tool-calls", tools=[("write", "error", 2, 3)])
                + call("s", "msg_02", 5, reason="stop"))
        got = self.grade(rows, session_id="s")
        self.assertIs(got["continuation_observed"], False)
        self.assertEqual(got["tools_failed"], 1)

    def test_a_call_that_did_not_end_for_its_tools_is_not_continued(self):
        rows = (call("s", "msg_01", 1, reason="stop", tools=[("write", "completed", 2, 3)])
                + call("s", "msg_02", 5, reason="stop"))
        self.assertIs(self.grade(rows, session_id="s")["continuation_observed"], False)

    def test_insufficient_or_contradictory_evidence_never_establishes_continuation(self):
        cases = {
            "finish reason not retained": [
                {**r, "finish_reason": None} if r["type"] == "step-finish" else r
                for r in self.loop()],
            "no message identifiers": [{k: v for k, v in r.items() if k != "message_id"}
                                       for r in self.loop()],
            "identifier order contradicts creation order": (
                call("ses_a", "msg_02", 100, reason="tool-calls",
                     tools=[("write", "completed", 110, 115)])
                + call("ses_a", "msg_01", 140, reason="stop")),
            "tool ended after the next call began": (
                call("ses_a", "msg_01", 100, reason="tool-calls",
                     tools=[("write", "completed", 110, 190)])
                + call("ses_a", "msg_02", 140, reason="stop")),
        }
        for why, rows in cases.items():
            with self.subTest(why):
                got = self.grade(rows, session_id="ses_a")
                self.assertEqual(got["outcome"], "insufficient-evidence", got["continuation"])
                self.assertFalse(got["gradeable"])

    def test_the_marker_and_the_gate_are_still_required(self):
        self.assertEqual(self.grade(self.loop(), artifact="# R\n", session_id="ses_a")["outcome"],
                         "protocol-failure")
        self.assertEqual(self.grade(self.loop(), gate=False, session_id="ses_a")["outcome"],
                         "protocol-failure")

    def test_zero_token_retries_are_infrastructure_and_zero_usage_is_unknown(self):
        storm = []
        for n in range(40):
            storm += call("s", f"msg_{n:03d}", n, reason="unknown", tokens=(0, 0))
        got = self.grade(storm, artifact="# R\n", session_id="s")
        self.assertEqual(got["outcome"], _qualify.INFRASTRUCTURE)
        self.assertFalse(got["gradeable"])
        unreported = [{**r, "input": 0, "output": 0} if r["type"] == "step-finish" else r
                      for r in self.loop()]
        got = self.grade(unreported, session_id="ses_a")
        self.assertEqual(got["outcome"], "pass")
        self.assertTrue(got["usage_reported"].startswith("unknown"))


class Plans(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-plans-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def pinned(self):
        executor = _qualify.pinned_executor()
        if executor is None:
            self.skipTest("the pinned OpenCode 1.18.29 build is not installed on this host")
        return executor

    def test_a_live_plan_is_a_proposal_or_authorized_and_never_forges_either(self):
        kw = dict(profile="deepseek-v4-flash-high", mode="live", cases=["tool-loop"],
                  executor=str(self.pinned()), per_launch_allowance=.05)
        for bad in ({}, {"owner_authorization": "yes", "proposal": True}):
            with self.subTest(bad=bad), self.assertRaises(_qualify.QualificationError):
                _qualify.build_plan(**kw, **bad)
        with self.assertRaises(_qualify.QualificationError):
            _qualify.build_plan(**{**kw, "per_launch_allowance": None}, proposal=True)
        with self.assertRaises(_qualify.QualificationError):
            _qualify.build_plan(**{**kw, "cases": ["authority-recovery"]}, proposal=True)
        proposal = _qualify.build_plan(**kw, proposal=True)
        self.assertEqual(proposal["status"], _qualify.PROPOSED)
        self.assertIsNone(proposal["authorization"]["owner"])
        self.assertEqual(proposal["authorization"]["status"], "NOT AUTHORIZED")
        with self.assertRaises(_qualify.QualificationError):
            _qualify.assert_executable(proposal)
        with self.assertRaises(_qualify.QualificationError):
            _qualify.authorize(proposal, self.tmp, "tool-loop")
        with self.assertRaises(_qualify.QualificationError):
            _qualify.authorize_proposal(proposal, "   ")
        plan = _qualify.authorize_proposal(proposal, "TEST ONLY: an owner statement")
        self.assertEqual(plan["status"], _qualify.AUTHORIZED)
        self.assertEqual(plan["proposal_digest"], proposal["digest"])
        self.assertNotEqual(plan["digest"], proposal["digest"])
        for frozen in ("suite", "worker_profile", "resources", "executor", "control_plane",
                       "allocation", "cases"):
            self.assertEqual(plan[frozen], proposal[frozen], frozen)
        with self.assertRaises(_qualify.QualificationError):
            _qualify.authorize_proposal(plan, "again")

    def test_a_live_plan_names_the_pinned_executor(self):
        fake = self.tmp / "opencode"
        fake.write_text("#!/bin/sh\necho 1.18.29\n")
        with self.assertRaises(_qualify.QualificationError) as caught:
            _qualify.build_plan(profile="deepseek-v4-flash-high", mode="live",
                                cases=["tool-loop"], executor=str(fake), proposal=True,
                                per_launch_allowance=.05)
        self.assertIn("pinned build", str(caught.exception))

    def test_each_trial_gets_its_enumerated_launches_and_the_campaign_is_their_sum(self):
        got = _qualify.allocation(["tool-loop", "requirements-challenge",
                                   "dispatch-implementation"], per_launch=.05)
        per = got["per_case"]
        self.assertEqual([per[c]["ceiling"] for c in ("tool-loop", "requirements-challenge",
                                                      "dispatch-implementation")], [2, 3, 11])
        self.assertEqual([per[c]["aggregate_limit"] for c in per], [.1, .15, .55])
        self.assertEqual(per["dispatch-implementation"]["minimum"], 5)
        # requirements-challenge runs twice: once per subject.
        self.assertEqual(got["campaign"], {**got["campaign"], "trials": 4, "launch_ceiling": 19,
                                           "minimum_launches": 10,
                                           "aggregate_derived_limit": .95})
        self.assertIn("never renew", got["campaign"]["note"])

    def test_an_unreachable_local_endpoint_prepares_nothing(self):
        executor = self.pinned()
        profile = self.tmp / "down.json"
        import socket
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        profile.write_text(json.dumps({
            "format": "proofbound-worker-profile-v1", "id": "local-down",
            "kind": "local-openai-compatible", "endpoint": f"http://127.0.0.1:{port}/v1",
            "model": "m", "limits": {"context": 8192, "output": 1024}, "tool_call": True}))
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
        executor = self.pinned()
        if not _qualify.sandbox_available():
            self.skipTest("needs sandbox-exec in this process")
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
                            "TEST ONLY: prepared, never driven", "--executor", str(executor),
                            "--into", str(plan_dir)], check=True, capture_output=True)
            prepared = subprocess.run([sys.executable, str(CLI), "prepare-live", "--plan",
                                       str(plan_dir), "--into", str(runs)], capture_output=True,
                                      text=True, stdin=subprocess.DEVNULL)
            self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
            self.assertEqual(json.loads(prepared.stdout)["launched"], 0)
            self.assertEqual([r for r in endpoint.requests if r["method"] == "POST"], [])
        for trial in json.loads((runs / "live.json").read_text())["trials"]:
            config = json.loads((Path(trial["run"]) / "run-config.json").read_text())
            self.addCleanup(shutil.rmtree, Path(config["home"]).parent, True)
            self.assertEqual(config["policy"]["launch_ceiling"], 2,
                             "the trial's own enumerated ceiling, not a campaign figure")
        graded = subprocess.run([sys.executable, str(CLI), "grade", "--plan", str(plan_dir),
                                 "--live", str(runs)], capture_output=True, text=True,
                                stdin=subprocess.DEVNULL)
        self.assertEqual(graded.returncode, 0, graded.stdout + graded.stderr)
        record = json.loads((runs / "result.json").read_text())
        self.assertEqual([t["status"] for t in record["trials"]], [_qualify.NOT_RUN])
        self.assertEqual(record["denominators"]["attempted"], 0)
        self.assertEqual(record["configuration_basis"], "planned")
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

def redigest(plan):
    plan["digest"] = _qualify._sha(_qualify._canonical({k: v for k, v in plan.items()
                                                         if k != "digest"}))
    return plan


class IdentityEnforcement(unittest.TestCase):
    """What a plan froze is what executes and what grades; inspection enforces nothing."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-identity-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.plan = _qualify.build_plan(profile="deepseek-v4-flash-high", mode="replay",
                                        cases=["requirements-challenge"])

    def test_a_plan_frozen_on_another_interpreter_neither_executes_nor_grades(self):
        """Reproduced on 0d2f9ee: a validly digested plan recording `0.0` executed on 3.12."""
        plan = redigest({**self.plan, "control_plane": {**self.plan["control_plane"],
                                                         "interpreter": {"minor": "0.0"}}})
        for check in (_qualify.assert_executable, _qualify.assert_gradeable):
            with self.subTest(check=check.__name__), \
                    self.assertRaises(_qualify.QualificationError) as caught:
                check(plan)
            self.assertIn("Python 0.0", str(caught.exception))

    def test_executor_bytes_that_moved_refuse_execution(self):
        executor = self.tmp / "opencode"
        executor.write_bytes(b"one build")
        plan = _qualify.build_plan(profile="deepseek-v4-flash-high", mode="replay",
                                   cases=["requirements-challenge"], executor=str(executor))
        _qualify.assert_executable(plan)
        executor.write_bytes(b"another build")
        with self.assertRaises(_qualify.QualificationError) as caught:
            _qualify.assert_executable(plan)
        self.assertIn("not the bytes the plan recorded", str(caught.exception))

    def test_grading_under_changed_instrument_bytes_refuses_and_names_the_commit(self):
        """Reproduced on 0d2f9ee: `grade` ran after the grader's bytes changed."""
        plan = redigest({**self.plan, "suite": {**self.plan["suite"], "digest": "0" * 64}})
        with self.assertRaises(_qualify.QualificationError) as caught:
            _qualify.assert_gradeable(plan)
        message = str(caught.exception)
        self.assertIn("qualification CLI", message)
        self.assertIn("Nothing was graded", message)
        self.assertIn(str(plan["control_plane"]["harness"]["commit"]), message)

    def test_the_instrument_covers_the_cli_and_the_stand_ins(self):
        covered = set(self.plan["suite"]["instrument"])
        for path in ("evals/pb_qualify.py", "evals/_stand_in_executor.py",
                     "evals/_stand_in_endpoint.py", "evals/authority_slice/_checker_corpus.py",
                     "evals/_qualify.py", "evals/authority_slice/_checker.py"):
            self.assertIn(path, covered)

    def test_a_run_that_froze_another_identity_does_not_join_the_plan(self):
        run = self.tmp / "run"
        run.mkdir()
        (run / "run-config.json").write_text(json.dumps({
            "interpreter": {"version": "3.0.1"}, "executor": {"sha256": "a" * 64},
            "worker_profile": {"digest": "b" * 64}}))
        with self.assertRaises(_qualify.QualificationError) as caught:
            _qualify.assert_run_matches(self.plan, run, executor_sha="c" * 64)
        message = str(caught.exception)
        self.assertIn("Python 3.0.1", message)
        self.assertIn("executor bytes", message)
        self.assertIn("retained", message)


class TrialStatus(unittest.TestCase):
    """An `attempt.json` proves a launch, not a conclusion."""

    def setUp(self):
        self.ev = Path(tempfile.mkdtemp(prefix="pb-status-"))
        self.addCleanup(shutil.rmtree, self.ev, True)

    def attempt(self, task, role, *, terminal=True, gate=True):
        event = self.ev / "run" / "phases" / "design" / "tasks" / task / "attempts" / f"{role}-1"
        event.mkdir(parents=True)
        (event / "attempt.json").write_text("{}")
        if terminal:
            (event / "terminal.json").write_text('{"status": "completed"}')
        if gate:
            (event / "evidence-gate.json").write_text('{"integrity_ok": true}')

    def test_nothing_launched_is_not_run(self):
        self.assertEqual(_qualify.trial_status(self.ev, "tool-loop")[0], _qualify.NOT_RUN)

    def test_an_attempt_without_a_terminal_record_is_incomplete(self):
        """Reproduced on 0d2f9ee: `grade` labelled exactly this `completed`."""
        self.attempt("requirements", "spec-author", terminal=False, gate=False)
        status, why = _qualify.trial_status(self.ev, "tool-loop")
        self.assertEqual(status, _qualify.INCOMPLETE)
        self.assertIn("spec-author-1", why)

    def test_an_unclassified_launch_slot_is_incomplete(self):
        self.attempt("requirements", "spec-author")
        (self.ev / "run" / "launch-ledger.json").write_text(json.dumps(
            {"slots": [{"slot": 1, "classification": "unresolved"}]}))
        self.assertEqual(_qualify.trial_status(self.ev, "tool-loop")[0], _qualify.INCOMPLETE)

    def test_completion_needs_the_cases_own_stopping_point(self):
        self.attempt("requirements", "spec-author")
        self.assertEqual(_qualify.trial_status(self.ev, "tool-loop"), ("completed", None))
        self.attempt("requirements", "spec-reflector")
        status, why = _qualify.trial_status(self.ev, "requirements-challenge")
        self.assertEqual(status, _qualify.INCOMPLETE)
        self.assertIn("never adjudicated", why)
        status, why = _qualify.trial_status(self.ev, "dispatch-implementation")
        self.assertIn("no delivery was sealed", why)


class ReviewedBytes(unittest.TestCase):
    """A review is graded against the bytes its own scope baseline says it saw."""

    def setUp(self):
        self.ev = Path(tempfile.mkdtemp(prefix="pb-reviewed-"))
        self.addCleanup(shutil.rmtree, self.ev, True)
        artifacts = self.ev / "artifacts"
        artifacts.mkdir()
        self.first = artifacts / "dispatch.first-attempt.py"
        self.first.write_text(_qualify._dispatch_source("global-fifo"))
        self.delivered = artifacts / "dispatch.py"
        self.delivered.write_text(_qualify._dispatch_source("round-robin"))
        (self.ev / "exposure.json").write_text('{"status": "unavailable"}')
        self.base = self.ev / "run" / "phases" / "build" / "tasks" / "implementation" / "attempts"

    def reviewer(self, n, seen, findings):
        event = self.base / f"reviewer-{n}"
        event.mkdir(parents=True)
        (event / "scope-baseline.json").write_text(json.dumps(
            {"entries": {"dispatch.py": {"sha256": seen}}}))
        (event / "report.md").write_text("```json\n" + json.dumps({"findings": findings})
                                         + "\n```\n")

    def test_each_review_meets_its_own_bytes(self):
        """Reproduced on 0d2f9ee: reviewer-2's clean report about the repaired code was graded
        as the review of the defective first attempt."""
        self.reviewer(1, _qualify._file_sha(self.first),
                      [{"requirements": ["R3"], "witness": ["a", "a", "b"]}])
        self.reviewer(2, _qualify._file_sha(self.delivered), [])
        self.reviewer(3, "f" * 64, [])
        (self.base / "fixer-1").mkdir()
        (self.base / "fixer-1" / "attempt.json").write_text("{}")
        got = _qualify.grade(self.ev, {"trial_id": "t", "case": "dispatch-implementation",
                                       "subject": "coherent", "variant": None})
        first, second, third = got["reviews"]
        self.assertEqual((first["reviewed_bytes"], first["substantiated"]),
                         ("dispatch.first-attempt.py", 1))
        self.assertEqual((second["reviewed_bytes"], second["reported"],
                          second["defect_present"]), ("dispatch.py", 0, False))
        self.assertIn("not retained", third["unavailable"])
        self.assertEqual(got["review"], first)
        self.assertEqual((got["first_attempt"], got["after_bounded_repair"]), ("fail", "pass"))

    def test_a_snapshot_that_is_not_what_the_first_reviewer_saw_stays_unavailable(self):
        self.reviewer(1, "e" * 64, [])
        (self.base / "fixer-1").mkdir()
        (self.base / "fixer-1" / "attempt.json").write_text("{}")
        got = _qualify.grade(self.ev, {"trial_id": "t", "case": "dispatch-implementation",
                                       "subject": "coherent", "variant": None})
        self.assertEqual(got["first_attempt"], "unavailable")
        self.assertIn("unavailable", got["first_attempt_source"])


class ChallengeExposure(unittest.TestCase):
    """A review that returns the witness it was shown verifies; it does not discover.

    Reproduced on the suite frozen at `89c4c16`: its findings-format example was the contradictory
    case's defect and witness, so every goal showed the answer, and the failed trial's author
    proposal repeated it.
    """

    def evidence(self, proposal: str, *, goal=None, seen=None):
        root = Path(tempfile.mkdtemp(prefix="pb-exposure-"))
        self.addCleanup(shutil.rmtree, root, True)
        (root / "artifacts").mkdir()
        (root / "artifacts" / "requirements.md").write_text(proposal)
        goal = goal if goal is not None else _qualify._goal("requirements-challenge",
                                                            "contradictory")
        attempt = root / "run/phases/design/tasks/requirements/attempts/spec-reflector-1"
        attempt.mkdir(parents=True)
        sha = lambda text: _qualify._sha(text.encode("utf-8"))
        (attempt / "scope-baseline.json").write_text(json.dumps({"entries": {
            "specs/QUAL/requirements.md": {"sha256": seen or sha(proposal)},
            "specs/QUAL/goal.md": {"sha256": sha(goal)}}}))
        return root

    def exposure(self, evidence, witness=("a", "a", "b")):
        graded = _qualify.grade_requirement_findings(
            [{"requirements": ["R2", "R3"], "witness": list(witness)}],
            _qualify._model("contradictory"))
        return _qualify.challenge_exposure(evidence, "requirements-challenge", "contradictory",
                                           graded)

    def test_no_goal_shows_any_case_answer(self):
        for case, subject in (("requirements-challenge", "contradictory"),
                              ("requirements-challenge", "coherent"),
                              ("dispatch-implementation", "coherent")):
            goal = _qualify._goal(case, subject)
            self.assertNotIn('"a", "a", "b"', goal)
            self.assertNotIn('["R2", "R3"]', goal)

    def test_a_witness_the_proposal_stated_is_verification(self):
        got = self.exposure(self.evidence('R2 and R3 conflict, witness ["a","a","b"].\n'))
        self.assertTrue(got["available"])
        self.assertTrue(got["correct_findings"][0]["shown"])
        self.assertTrue(got["claim"].startswith("verification"))

    def test_a_witness_nobody_showed_is_found_but_prose_is_not_excluded(self):
        got = self.exposure(self.evidence("The owner's four requirements, verbatim.\n"))
        self.assertFalse(got["correct_findings"][0]["shown"])
        self.assertTrue(got["claim"].startswith("found on the production path"))
        self.assertIn("described in words", got["claim"])

    def test_unretained_bytes_or_another_goal_are_unavailable(self):
        self.assertFalse(self.exposure(self.evidence("x\n", seen="0" * 64))["available"])
        self.assertFalse(self.exposure(self.evidence("x\n", goal="another goal"))["available"])


class ObservedIdentity(unittest.TestCase):
    """A planned identity is never reported as an observed one."""

    def trial(self, *, interpreter="3.10.14", coordinator="claude-code/opus", transport="none"):
        return {"transport": transport, "observed": {
            "interpreter": interpreter, "executor_sha256": "e" * 64,
            "worker_model": "deepseek/deepseek-v4-flash", "worker_variant": "high",
            "coordinator": ([{"requested": coordinator, "self_reported": None,
                              "observed": None}] if coordinator else None)}}

    def test_runs_that_agree_report_the_value_and_runs_that_differ_do_not(self):
        same = _qualify.observed_configuration([self.trial(), self.trial()])
        self.assertEqual((same["interpreter"], same["coordinator"]), ("3.10", "claude-code/opus"))
        mixed = _qualify.observed_configuration([self.trial(), self.trial(interpreter="3.14.5")])
        self.assertIn("mixed", mixed["interpreter"])
        unrecorded = _qualify.observed_configuration([self.trial(), self.trial(coordinator=None)])
        self.assertIsNone(unrecorded["coordinator"])
        stand_in = _qualify.observed_configuration([self.trial(transport="stand-in-executor")])
        self.assertEqual(stand_in["executor"], "stand-in-executor")

    def test_a_comparison_prefers_the_record_and_names_a_plan_it_contradicts(self):
        planned = result(coordinator="codex/gpt-6", executor="e" * 64, interpreter="3.10")
        planned["observed_configuration"] = _qualify.observed_configuration([self.trial()])
        other = result(coordinator="claude-code/opus", executor="e" * 64, interpreter="3.10",
                       **{"worker.model": "p1/m2"})
        got = _compare.compare_qualification(planned, other)
        self.assertFalse(got["controlled"])
        self.assertTrue(any("planned as 'codex/gpt-6' and recorded as 'claude-code/opus'" in r
                            for r in got["not_controlled_because"]))


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


class RealExecutorToolLoopReplay(unittest.TestCase):
    """The continuation rule on evidence the pinned executor actually wrote, via replay."""

    def test_well_formed_passes_on_its_causal_chain_and_malformed_does_not(self):
        executor = _qualify.pinned_executor()
        if executor is None or not _qualify.sandbox_available():
            self.skipTest("needs the pinned executor and sandbox-exec on this host")
        tmp = Path(tempfile.mkdtemp(prefix="pb-toolloop-replay-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        profile = tmp / "local.json"
        profile.write_text(json.dumps({
            "format": "proofbound-worker-profile-v1", "id": "local-replay",
            "kind": "local-openai-compatible", "endpoint": "http://127.0.0.1:18080/v1",
            "model": "m", "limits": {"context": 8192, "output": 1024}, "tool_call": True}))
        for args in (["plan", "--worker-profile", profile, "--into", tmp / "plan",
                      "--case", "tool-loop", "--deadline-seconds", 60],
                     ["replay", "--plan", tmp / "plan", "--into", tmp / "result",
                      "--only", "tool-loop--marker--well-formed",
                      "--only", "tool-loop--marker--malformed-arguments"]):
            done = subprocess.run([sys.executable, str(CLI), *map(str, args)],
                                  capture_output=True, text=True, stdin=subprocess.DEVNULL)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        record = json.loads((tmp / "result" / "result.json").read_text())
        trials = {t["trial_id"]: t for t in record["trials"]}
        good = trials["tool-loop--marker--well-formed"]["outcome"]
        self.assertEqual(good["outcome"], "pass")
        chain = good["continuation"]["continued"]
        self.assertTrue(chain and all(c["next_call"] > c["tool_call"] for c in chain))
        self.assertEqual(trials["tool-loop--marker--well-formed"]["status"], "completed")
        bad = trials["tool-loop--marker--malformed-arguments"]["outcome"]
        self.assertEqual(bad["outcome"], "protocol-failure")


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

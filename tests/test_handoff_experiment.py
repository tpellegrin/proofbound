"""Regressions for `pb-handoff-1`: the artifact checker, the launch guard, and the runtime.

The experiment these support has not run. What is testable before it runs is whether the machinery
around it would behave as declared, and each case here is one of the ways the preparation could be
wrong in a way that would only surface while spending money:

* the **checker** could grade a model of the artifact instead of the artifact, accept a container
  the contract did not ask for, or die with the code it is checking;
* the **guard** could let a run exceed its ceiling, spend against an unreconciled slot, take a
  second repair, or treat a launch that never reached the executor as free without evidence;
* the **runtime** could stage the evaluator's own answers where a worker can read them.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLICE = ROOT / "evals" / "authority_slice"
sys.path.insert(0, str(SLICE))
sys.path.insert(0, str(ROOT / "evals"))

import _checker                      # noqa: E402
import _checker_corpus               # noqa: E402
import _guard                        # noqa: E402
import _runtime                      # noqa: E402


class ArtifactCheckerTest(unittest.TestCase):
    """The instrument must discriminate before it is allowed to judge a paid delivery."""

    #: The corpus includes a deliberate non-terminating artifact, so the whole validation is run
    #: once with a short bound rather than once per case with a generous one.
    validated: "dict" = {}

    @classmethod
    def setUpClass(cls) -> None:
        cls.validated = _checker_corpus.validate(timeout=3)

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-checker-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def artifact(self, body: str) -> Path:
        path = self.tmp / "dispatch.py"
        path.write_text(_checker_corpus._PRELUDE + "\n\n" + body + "\n", encoding="utf-8")
        return path

    def test_the_corpus_discriminates_exactly_as_declared(self):
        result = self.validated
        self.assertTrue(result["sound_accepted"], result)
        self.assertTrue(result["defective_rejected"], result)
        for name, row in result["checked"].items():
            with self.subTest(implementation=name):
                self.assertTrue(row["as_declared"], row)

    def test_two_structurally_different_sound_implementations_both_pass(self):
        """An instrument that accepted only its reference would be measuring resemblance."""
        result = self.validated
        self.assertGreaterEqual(len(result["sound"]), 2)
        for name in result["sound"]:
            self.assertEqual(result["checked"][name]["verdict"], _checker.PASS)

    def test_the_return_type_is_checked_and_not_coerced_away(self):
        """The gap this checker exists to close: `list(...)` erases what AC-001 asks for."""
        import _obligations as oracle
        model = oracle.parse_model(
            (SLICE / "cases" / "coherent-requirements" / "requirements.md").read_text())

        def generator(arrivals):
            import _implementations as impl
            return (item for item in impl.reference(arrivals))

        self.assertTrue(oracle.check_implementation(generator, model)["conforms"],
                        "the ordering model still accepts a generator, which is why the checker "
                        "cannot rely on it alone")
        report = _checker.check_delivered(
            self.artifact("def dispatch(arrivals):\n"
                          "    return (i for i in _round_robin(arrivals))"), timeout=10)
        self.assertEqual(report["verdict"], _checker.FAIL)
        self.assertIn("return-type", {f["code"] for f in report["findings"]})

    def test_the_delivered_bytes_are_what_is_graded(self):
        """A module of the same name elsewhere on the path must not be graded instead."""
        decoy = self.tmp / "decoy"
        decoy.mkdir()
        (decoy / "dispatch.py").write_text(
            "def dispatch(arrivals):\n    return []\n", encoding="utf-8")
        sys.path.insert(0, str(decoy))
        self.addCleanup(sys.path.remove, str(decoy))
        artifact = self.artifact("def dispatch(arrivals):\n    return _round_robin(arrivals)")
        report = _checker.check_delivered(artifact, timeout=10)
        self.assertEqual(report["verdict"], _checker.PASS, report["findings"])
        self.assertEqual(report["artifact"]["path"], str(artifact.resolve()))
        self.assertEqual(report["artifact"]["sha256"], _checker.digest(artifact))

    def test_a_missing_artifact_fails_rather_than_erroring(self):
        report = _checker.check_delivered(self.tmp / "absent.py")
        self.assertEqual(report["verdict"], _checker.FAIL)
        self.assertEqual([f["code"] for f in report["findings"]], ["artifact-missing"])

    def test_a_broken_checker_is_not_reported_as_a_failed_implementation(self):
        """Three outcomes, kept apart: the artifact failed, it hung, or the instrument broke."""
        self.assertEqual(_checker.CHECKER_ERROR, "checker-error")
        report = _checker.check_delivered(
            self.artifact("def dispatch(arrivals):\n"
                          "    import time; time.sleep(3600)\n"
                          "    return []"), timeout=3)
        self.assertEqual(report["verdict"], _checker.FAIL)
        self.assertEqual([f["code"] for f in report["findings"]], ["does-not-terminate"])

    def test_scope_is_checked_against_a_baseline_the_evaluator_recorded(self):
        project = self.tmp / "project"
        (project / "sub").mkdir(parents=True)
        (project / "requirements.md").write_text("accepted\n", encoding="utf-8")
        (project / "sub" / "other.py").write_text("x = 1\n", encoding="utf-8")
        baseline = _checker.baseline_manifest(project)

        (project / "dispatch.py").write_text("def dispatch(a):\n    return []\n", encoding="utf-8")
        allowed = _checker.check_scope(project, baseline)
        self.assertEqual(allowed["verdict"], _checker.PASS, allowed)

        (project / "requirements.md").write_text("edited by the worker\n", encoding="utf-8")
        refused = _checker.check_scope(project, baseline)
        self.assertEqual(refused["verdict"], _checker.FAIL)
        self.assertIn("requirements.md", refused["undeclared"])


class LaunchGuardTest(unittest.TestCase):
    """The ceiling is derived from enumerated paths; this is what makes a run obey it."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-guard-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.run_root = self.tmp / "run"
        self.run_root.mkdir()
        self.db = self.tmp / "worker.db"

    def attempt(self, name: str, *, reservation: bool = True, status: str = "completed",
                title: "str | None" = None) -> Path:
        event = self.run_root / "attempts" / name
        event.mkdir(parents=True)
        (event / "attempt.json").write_text(json.dumps(
            {"started_at": "2026-09-18T10:00:00+00:00"}), encoding="utf-8")
        if reservation:
            (event / "launch-reservation.json").write_text("{}", encoding="utf-8")
        (event / "terminal.json").write_text(json.dumps(
            {"status": status, "session_id": "ses_x", "title": title or f"dsd:RQ:{name}"}),
            encoding="utf-8")
        return event

    def session(self, *, calls: int = 3, unfinished: int = 0) -> None:
        with closing(sqlite3.connect(self.db)) as conn:
            conn.execute("create table if not exists session (id text, title text)")
            conn.execute("create table if not exists message "
                         "(id text, session_id text, time_created integer, data text)")
            conn.execute("create table if not exists part (id text, message_id text, data text)")
            conn.execute("insert into session values ('ses_x', 't')")
            for n in range(calls):
                mid = f"m{n}"
                conn.execute("insert into message values (?, 'ses_x', ?, ?)",
                             (mid, n, json.dumps({"role": "assistant"})))
                conn.execute("insert into part values (?, ?, ?)",
                             (f"{mid}s", mid, json.dumps({"type": "step-start"})))
                if n >= unfinished:
                    conn.execute("insert into part values (?, ?, ?)", (f"{mid}f", mid, json.dumps(
                        {"type": "step-finish", "cost": 0.001,
                         "tokens": {"input": 100, "output": 20, "cache": {"read": 0, "write": 0}}})))
            conn.commit()

    def ledger(self) -> _guard.LaunchLedger:
        return _guard.LaunchLedger(self.tmp / "launch-ledger.json")

    def spend_slot(self, ledger: _guard.LaunchLedger, name: str, *, role: str = "implementer",
                   task: str = "RQ-impl", reservation: bool = True) -> None:
        slot = ledger.reserve(phase="build", task=task, role=role)
        event = self.attempt(name, reservation=reservation)
        ledger.classify(slot["slot"], run_root=self.run_root,
                        event_dir=event if reservation else None,
                        launcher_returncode=0 if reservation else 2,
                        launcher_output="" if reservation else "transport failed before launch")

    def test_the_ceiling_is_enforced_not_merely_enumerated(self):
        self.session()
        ledger = self.ledger()
        for n in range(_guard.LAUNCH_CEILING):
            self.spend_slot(ledger, f"impl-{n}", role="reviewer")
        self.assertEqual(ledger.spent_slots(), _guard.LAUNCH_CEILING)
        verdict = ledger.admit(phase="build", task="RQ-impl", role="reviewer",
                               run_root=self.run_root, db=self.db)
        self.assertFalse(verdict["admit"])
        self.assertTrue(any("ceiling" in why for why in verdict["why"]), verdict["why"])

    def test_an_unreconciled_slot_blocks_the_next_launch(self):
        """A reservation with no classification is a launch nobody has accounted for."""
        self.session()
        ledger = self.ledger()
        ledger.reserve(phase="build", task="RQ-impl", role="implementer")
        verdict = ledger.admit(phase="build", task="RQ-impl", role="reviewer",
                               run_root=self.run_root, db=self.db)
        self.assertFalse(verdict["admit"])
        self.assertTrue(any("never classified" in why for why in verdict["why"]), verdict["why"])

    def test_an_unfinished_model_call_is_terminal_for_the_run(self):
        self.session(unfinished=1)
        ledger = self.ledger()
        self.spend_slot(ledger, "impl-0")
        verdict = ledger.admit(phase="build", task="RQ-impl", role="reviewer",
                               run_root=self.run_root, db=self.db)
        self.assertFalse(verdict["admit"])
        self.assertFalse(verdict["accounting_complete"])
        self.assertTrue(any("did not finish" in why for why in verdict["why"]), verdict["why"])

    def test_the_single_repair_allowance_is_counted_from_producer_attempts(self):
        self.session()
        ledger = self.ledger()
        self.spend_slot(ledger, "impl-0", role="implementer")
        self.assertTrue(ledger.admit(phase="build", task="RQ-impl", role="implementer",
                                     run_root=self.run_root, db=self.db)["admit"],
                        "the first repair is allowed")
        self.spend_slot(ledger, "impl-1", role="implementer")
        verdict = ledger.admit(phase="build", task="RQ-impl", role="implementer",
                               run_root=self.run_root, db=self.db)
        self.assertFalse(verdict["admit"])
        self.assertTrue(any("repair allowance is spent" in why for why in verdict["why"]),
                        verdict["why"])
        self.assertTrue(ledger.admit(phase="build", task="RQ-impl", role="reviewer",
                                     run_root=self.run_root, db=self.db)["admit"],
                        "a review is not a producer attempt and is still permitted")

    def test_a_pre_executor_failure_still_consumes_the_relaunch_allowance(self):
        """The ceiling is worst-path plus **one** evidenced relaunch, not plus unlimited ones."""
        self.session()
        ledger = self.ledger()
        for n in range(_guard.LAUNCH_CEILING - 1):
            self.spend_slot(ledger, f"ok-{n}", role="reviewer")
        self.spend_slot(ledger, "lost-0", role="reviewer", reservation=False)
        self.assertEqual(ledger.spent_slots(), _guard.LAUNCH_CEILING - 1)
        self.assertEqual(ledger.pre_executor_failures(), 1)
        verdict = ledger.admit(phase="build", task="RQ-impl", role="reviewer",
                               run_root=self.run_root, db=self.db)
        self.assertFalse(verdict["admit"], "reserved slots, not just successful ones, hit the cap")
        self.assertTrue(any("did not" in why for why in verdict["why"]), verdict["why"])

    def test_a_launch_that_never_reached_the_executor_is_evidenced_not_asserted(self):
        self.session()
        ledger = self.ledger()
        self.spend_slot(ledger, "impl-0", reservation=False)
        slot = ledger.slots[0]
        self.assertEqual(slot["classification"], _guard.PRE_EXECUTOR_FAILURE)
        self.assertFalse(slot["reservation_present"])
        self.assertIn("transport failed", slot["launcher_output"])
        self.assertEqual(ledger.spent_slots(), 0, "it consumed no slot")
        self.assertEqual(ledger.pre_executor_failures(), 1, "and it is still on the record")

    def test_the_ledger_survives_being_reloaded(self):
        """An interrupted coordinator must not lose what was already spent."""
        self.session()
        ledger = self.ledger()
        self.spend_slot(ledger, "impl-0")
        reloaded = self.ledger()
        self.assertEqual(reloaded.spent_slots(), 1)
        self.assertEqual(reloaded.slots[0]["classification"], _guard.EXECUTOR_REACHED)

    def test_the_budget_refuses_before_the_limit_is_reached(self):
        self.session()
        ledger = self.ledger()
        self.spend_slot(ledger, "impl-0")
        import _pricing
        real = _pricing.cost
        _pricing.cost = lambda usage, **kw: {"amount": _guard.AGGREGATE_LIMIT - 0.01,
                                             "currency": "USD"}
        self.addCleanup(setattr, _pricing, "cost", real)
        verdict = ledger.admit(phase="build", task="RQ-impl", role="reviewer",
                               run_root=self.run_root, db=self.db)
        self.assertFalse(verdict["admit"])
        self.assertTrue(any("exceeds" in why for why in verdict["why"]), verdict["why"])

    def test_launches_and_model_calls_are_different_quantities(self):
        self.session(calls=7)
        ledger = self.ledger()
        self.spend_slot(ledger, "impl-0")
        account = _guard.spend(self.run_root, self.db, event_dirs=ledger.own_event_dirs())
        self.assertEqual(account["launched_attempts"], 1)
        self.assertEqual(account["model_calls"]["started"], 7)

    def test_seeded_attempts_are_excluded_from_live_attribution(self):
        """The upstream state is seeded by a fake; charging the budget for it would be wrong."""
        self.session()
        ledger = self.ledger()
        self.spend_slot(ledger, "impl-0")
        self.attempt("seeded-author-1")           # in the run tree, not in this ledger
        everything = _guard.spend(self.run_root, self.db)
        live_only = _guard.spend(self.run_root, self.db, event_dirs=ledger.own_event_dirs())
        self.assertEqual(everything["launched_attempts"], 2)
        self.assertEqual(live_only["launched_attempts"], 1)
        self.assertIn("seeded attempts are excluded", live_only["scope"])


class ContinuationRehearsalTest(unittest.TestCase):
    """The whole continuation, through the entry points the live run uses.

    One path here; all four (`clean`, `repair`, `blocked`, `interrupted`) are run on demand with
    `pb_slice.py rehearse-live`, which takes about forty seconds. This one is in the suite because
    it is the integration most likely to rot silently when a shipped script changes.
    """

    def test_the_clean_path_reaches_acceptance_with_the_guard_and_the_check_in_it(self):
        import _live
        into = Path(tempfile.mkdtemp(prefix="pb-rehearse-"))
        self.addCleanup(shutil.rmtree, into, True)
        result = _live.rehearse(into / "run", path="clean")

        self.assertEqual(result["outcome"], "accepted", result["steps"])
        self.assertTrue(result["accepted"])
        self.assertEqual(result["artifact_check"], _checker.PASS)

        steps = {s["step"]: s for s in result["steps"]}
        self.assertTrue(steps["authorization"]["authorized"])
        self.assertEqual(steps["implementer launched"]["classification"],
                         _guard.EXECUTOR_REACHED)
        self.assertTrue(steps["implementation gated"]["integrity_ok"])
        self.assertFalse(steps["review reported"]["blocking_finding"])
        self.assertTrue(steps["external artifact check"]["artifact_sha256"],
                        "the check must record which bytes it graded")

        account = result["account"]
        self.assertTrue(account["spend"]["complete"])
        self.assertEqual(account["launches"]["slots_spent"], 2)
        self.assertLessEqual(account["spend"]["derived"], _guard.AGGREGATE_LIMIT)
        self.assertIn("the coordinator's judgement", " ".join(result["simulated"]))


class AcceptedAuthorityTest(unittest.TestCase):
    """The external check must grade against the requirements the project actually accepted."""

    def test_the_check_follows_the_projects_requirements_not_the_fixture_copy(self):
        import _live
        into = Path(tempfile.mkdtemp(prefix="pb-authority-"))
        self.addCleanup(shutil.rmtree, into, True)
        prepared = _live.prepare(into / "run", mode=_live.REHEARSAL)
        config = _live.load_config(prepared["workdir"])
        project = Path(config["paths"]["project"])

        # A delivery that satisfies the fixture's obligations but not the project's, once the
        # project's accepted requirements say something different. If the checker read the fixture
        # copy it would pass this; reading the accepted authority, it must not.
        accepted = project / "requirements.md"
        accepted.write_text(accepted.read_text(encoding="utf-8").replace(
            '"R2": "fifo-per-key"', '"R2": "fifo-global"'), encoding="utf-8")
        (project / "dispatch.py").write_text(
            "def _items(arrivals):\n"
            "    seen, out = {}, []\n"
            "    for key in arrivals:\n"
            "        seen[key] = seen.get(key, 0) + 1\n"
            "        out.append((key, seen[key]))\n"
            "    return out\n\n\n"
            "def dispatch(arrivals):\n"
            "    keys, queues = [], {}\n"
            "    for item in _items(arrivals):\n"
            "        if item[0] not in queues:\n"
            "            queues[item[0]] = []\n"
            "            keys.append(item[0])\n"
            "        queues[item[0]].append(item)\n"
            "    out = []\n"
            "    while any(queues[k] for k in keys):\n"
            "        for key in keys:\n"
            "            if queues[key]:\n"
            "                out.append(queues[key].pop(0))\n"
            "    return out\n", encoding="utf-8")

        report = _live.check_artifact(prepared["workdir"], timeout=20)
        self.assertEqual(report["artifact_check"]["authority"]["path"], str(accepted))
        self.assertEqual(report["artifact_check"]["authority"]["sha256"],
                         _checker.digest(accepted))
        self.assertEqual(report["verdict"], _checker.FAIL,
                         "round-robin satisfies the fixture's obligations, not the project's")
        self.assertIn("obligation", {f["code"] for f in report["artifact_check"]["findings"]})


class FreezeDisciplineTest(unittest.TestCase):
    """A live run may not be prepared from a tree nobody can identify afterwards."""

    def test_live_preparation_refuses_an_uncommitted_harness(self):
        import _live
        into = Path(tempfile.mkdtemp(prefix="pb-freeze-"))
        self.addCleanup(shutil.rmtree, into, True)
        real = _live.harness_revision
        _live.harness_revision = lambda: {"commit": "deadbeef", "clean": False,
                                          "dirty_paths": ["evals/authority_slice/_live.py"]}
        self.addCleanup(setattr, _live, "harness_revision", real)
        with self.assertRaises(SystemExit) as caught:
            _live.prepare(into / "run", mode=_live.LIVE)
        self.assertIn("uncommitted harness", str(caught.exception))


class RuntimeAllowlistTest(unittest.TestCase):
    """What the runtime stages decides what a subject can read. It is an allowlist for a reason."""

    def test_the_evaluators_answers_are_never_in_the_allowlist(self):
        staged = set(_runtime.HARNESS_ALLOWLIST) | set(_runtime.SLICE_ALLOWLIST)
        for withheld in _runtime.WITHHELD:
            self.assertNotIn(withheld, staged)
        self.assertIn("_implementations.py", _runtime.WITHHELD)
        self.assertIn("_checker_corpus.py", _runtime.WITHHELD)

    def test_the_withheld_material_exists_and_is_recognised_by_content(self):
        paths = _runtime.sensitive_paths()
        self.assertTrue(paths, "nothing to withhold means the probe proves nothing")
        kinds = _runtime.sensitive()
        for path in paths:
            with self.subTest(path=path.name):
                self.assertTrue(any(k.confirms(path) for k in kinds),
                                "a copy must be recognised by its bytes, not by its name")

    def test_the_checker_carries_criteria_but_not_implementations(self):
        """Its acceptance criteria are the contract's and may be read; its corpus may not."""
        text = (SLICE / "_checker.py").read_text(encoding="utf-8")
        self.assertIn("AC-001", text)
        self.assertNotIn("_round_robin", text)
        self.assertIn("_round_robin", (SLICE / "_checker_corpus.py").read_text(encoding="utf-8"))

    def test_the_operational_cli_imports_nothing_that_is_withheld(self):
        """A subject runtime has no `_implementations`; the commands it runs must not need one."""
        source = (SLICE / "pb_slice.py").read_text(encoding="utf-8")
        module_level = source.split("def ", 1)[0]
        self.assertNotIn("import _implementations", module_level)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

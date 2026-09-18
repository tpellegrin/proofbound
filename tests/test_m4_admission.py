"""Admission: the transition at which a candidate-bound implementation becomes launchable.

Before this milestone the launch path trusted the coordinator. `pb_execution.py authorize` answered
a question correctly and conferred nothing, `dsd_state.py bind-contract` bound whatever it was
given, and `dsd_attempt.py launch` ran whatever was bound — so a refused authorization and an
honoured one produced identical state, and only the coordinator's judgement separated them. The
`pb-handoff-1` control condition refused correctly *because the coordinator chose to*.

What the repair adds is one fact in one place: a task carries an `admission` record, written by
`pb_execution.py admit` in the same atomic state update that binds the contract, and candidate-bound
execution will not launch without one that matches this contract revision, this candidate and this
project. These cases are the boundary's behaviour, not its implementation:

* which contracts the rule governs at all — new-task admission against continuation, upstream
  review work, and contracts predating the whole notion (`AdmissionScope`);
* what disqualifies a record that exists (`AdmissionRecordFindings`);
* and what the shipped entry points actually do, end to end, against a fake executor
  (`AdmissionLifecycle`) — including the routes by which the bypass was reproduced.

Nothing here reaches a provider. `AdmissionLifecycle` drives the slice's rehearsal fixture, whose
executor is a local fake, and asserts that the executor was reached or not reached from the run tree
it leaves behind rather than from an exit code — the same evidence standard the reproduction used,
because an exit code is exactly what the defect made unreliable.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SLICE = ROOT / "evals" / "authority_slice"
PYTHON = sys.executable
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SLICE))

from _contract import requires_admission                    # noqa: E402
from _execution import ADMISSION_FORMAT, admission_findings  # noqa: E402


def codes(findings) -> list[str]:
    return [f["code"] for f in findings]


class AdmissionScope(unittest.TestCase):
    """Which contracts the rule governs — and, as importantly, which it leaves alone.

    A rule that caught every contract would break every review task in the repository; a rule that
    caught none would be the defect. The discriminator is the contract's own content: it names a
    Proofbound candidate *and* permits project writes.
    """

    def test_the_repositorys_implementation_contracts_require_admission(self):
        for rel in ("evals/authority_slice/contracts/RQ-impl.md",
                    "demo/pb-authority-demo-1/contracts/RG-impl.md",
                    "demo/pb-authority-demo-2/contracts/RG-impl.md"):
            with self.subTest(contract=rel):
                self.assertTrue(requires_admission((ROOT / rel).read_text(encoding="utf-8")))

    def test_upstream_review_work_under_a_candidate_is_not_execution(self):
        """A consistency task names a candidate and writes nothing. It is not implementation.

        This is the distinction that keeps the rule narrow. Consistency reflection happens *under*
        a candidate — naming one is how it says which candidate it is reflecting on — but it
        produces a judgement, not a change, so it binds exactly as it always has.
        """
        for rel in ("evals/authority_slice/contracts/RQ-consistency.md",
                    "demo/pb-authority-demo-1/contracts/RG-consistency.md",
                    "demo/pb-authority-demo-2/contracts/RG-consistency.md"):
            with self.subTest(contract=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIn("Proofbound candidate", text)
                self.assertFalse(requires_admission(text))

    def test_candidate_free_work_is_untouched(self):
        for rel in ("evals/authority_slice/contracts/RQ-intent.md",
                    "demo/pb-authority-demo-1/contracts/RG-spec.md"):
            with self.subTest(contract=rel):
                self.assertFalse(requires_admission((ROOT / rel).read_text(encoding="utf-8")))

    def test_a_contract_predating_candidates_binds_as_before(self):
        """Compatibility: a run recorded before Proofbound existed must still bind and launch.

        The rule is keyed on a section such a contract cannot contain, so it is not merely
        tolerated — it is outside the rule's subject entirely.
        """
        legacy = ("# Task U1 — widen the retry window\nContract revision: r0001\n\n"
                  "## Objective\nWiden it.\n\n## Allowed source changes\n- `widget.py`\n\n"
                  "## Acceptance criteria\n- AC-001 it is wider\n")
        self.assertFalse(requires_admission(legacy))

    def test_omitting_the_candidate_does_not_smuggle_execution_through(self):
        """Dropping the candidate section evades the rule and forfeits what it was for.

        Such a contract launches freely — and carries no candidate, so `pb_execution.py report`
        attributes it to none and no acceptance can claim it implemented one. The escape is
        available and self-defeating, which is the correct shape for a mechanism that cannot read
        intent. It is recorded here so the next reader does not mistake it for an oversight.
        """
        text = (SLICE / "contracts" / "RQ-impl.md").read_text(encoding="utf-8")
        stripped = text.split("## Proofbound candidate")[0]
        self.assertTrue(requires_admission(text))
        self.assertFalse(requires_admission(stripped))

        from _contract import declared_candidate
        self.assertIsNone(declared_candidate(stripped))


class AdmissionRecordFindings(unittest.TestCase):
    """An admission record is a fact about one task, one revision, one candidate, one project."""

    CANDIDATE = "a" * 64
    DIGEST = "b" * 64

    def record(self, **overrides):
        base = {"format": ADMISSION_FORMAT, "candidate": self.CANDIDATE,
                "contract_path": "/p/contracts/RQ-impl.md", "contract_sha256": self.DIGEST,
                "project_root": "/p", "admitted_at": "2026-09-18T00:00:00+00:00",
                "authority": {}, "authorization": {"provenance": "verified"}}
        unknown = set(overrides) - set(base)
        if unknown:                       # a typo'd override silently weakens the case it states
            raise AssertionError(f"not admission fields: {sorted(unknown)}")
        base.update(overrides)
        return base

    def findings(self, admission, *, candidate=None, digest=None, project="/p"):
        return codes(admission_findings(
            admission, candidate=candidate or self.CANDIDATE,
            contract_sha256=digest or self.DIGEST, project_root=Path(project)))

    def test_a_matching_record_qualifies(self):
        self.assertEqual(self.findings(self.record()), [])

    def test_no_record_at_all(self):
        self.assertEqual(self.findings(None), ["not-admitted"])

    def test_a_record_of_the_wrong_shape_is_not_read_field_by_field(self):
        """A foreign object must be rejected wholesale, not mined for fields that happen to match."""
        self.assertEqual(self.findings("admitted"), ["not-admitted"])
        self.assertEqual(self.findings(self.record(format="something-else")),
                         ["malformed-admission"])

    def test_a_different_candidate(self):
        self.assertEqual(self.findings(self.record(candidate="c" * 64)),
                         ["admission-candidate-mismatch"])

    def test_a_revised_contract_needs_a_new_admission(self):
        self.assertEqual(self.findings(self.record(), digest="d" * 64),
                         ["admission-contract-mismatch"])

    def test_a_record_does_not_travel_to_another_project(self):
        self.assertEqual(self.findings(self.record(), project="/elsewhere"),
                         ["admission-project-mismatch"])

    def test_every_mismatch_is_reported_not_just_the_first(self):
        """A coordinator repairing one of three problems should learn about the other two."""
        self.assertEqual(
            sorted(self.findings(self.record(candidate="c" * 64),
                                 digest="d" * 64, project="/elsewhere")),
            ["admission-candidate-mismatch", "admission-contract-mismatch",
             "admission-project-mismatch"])

    def test_currentness_is_deliberately_not_rechecked(self):
        """A6.4: authority is fixed at admission.

        A task admitted under `C1` continues through review, repair and acceptance after the
        project has moved to `C2`. Rechecking here would make a long task fail halfway for a reason
        that has nothing to do with it, and would silently convert immutable task authority into
        whatever the project happens to be now.
        """
        stale = self.record(authorization={"provenance": "verified", "current": "z" * 64})
        self.assertEqual(self.findings(stale), [])


class AdmissionLifecycle(unittest.TestCase):
    """The shipped entry points, end to end, against the slice's fake executor.

    Each case prepares its own authority state. `prepare` seeds a project, a change graph, a
    ledger record, a freeze and a consistency acceptance with a stand-in, exactly as the live
    experiment's upstream state was seeded, then the real `pb_execution.py`, `dsd_state.py` and
    `dsd_attempt.py` do the rest.
    """

    @classmethod
    def setUpClass(cls) -> None:
        import _live
        cls.live = _live

    def prepare(self, *, drop_consistency: bool = False):
        work = Path(tempfile.mkdtemp(prefix="pb-m4-"))
        self.addCleanup(shutil.rmtree, work, True)
        prepared = self.live.prepare(work, mode=self.live.REHEARSAL)
        config = self.live.load_config(prepared["workdir"])
        if drop_consistency:
            for record in Path(config["paths"]["consistency"]).glob("*.json"):
                record.unlink()
        return work, config, prepared["candidate"]

    # -- evidence, not exit codes ----------------------------------------------------------------
    def executor_reached(self, config) -> bool:
        """Did a worker actually run? Answered from the run tree, never from a return code.

        The defect this milestone repairs was invisible in return codes: the launcher exited 0 on a
        launch that should never have happened.
        """
        run_root = Path(config["paths"]["run_root"])
        event = run_root / "attempts" / "implementer-1"
        return any([(event / "launch-reservation.json").is_file(),
                    (event / "terminal.json").is_file(),
                    (Path(config["paths"]["project"]) / "dispatch.py").is_file()])

    def task_state(self, config, task="RQ-impl"):
        state = json.loads((Path(config["paths"]["run_root"]) / "state.json").read_text())
        return state["phases"]["build"]["tasks"].get(task, {})

    def admit(self, config, contract, *, task="RQ-impl"):
        return subprocess.run(
            [PYTHON, str(SCRIPTS / "pb_execution.py"), "admit",
             "--run-root", config["paths"]["run_root"], "--phase-id", "build", "--task-id", task,
             "--contract", str(contract), "--graph", config["paths"]["graph"],
             "--ledger", config["paths"]["ledger"], "--project-root", config["paths"]["project"],
             "--consistency", config["paths"]["consistency"]],
            text=True, capture_output=True)

    def bind(self, config, contract, *, task="RQ-impl"):
        return subprocess.run(
            [PYTHON, str(SCRIPTS / "dsd_state.py"), "bind-contract",
             "--run-root", config["paths"]["run_root"], "--phase-id", "build", "--task-id", task,
             "--contract", str(contract)], text=True, capture_output=True)

    def hand_bind(self, config, contract, *, task="RQ-impl", admission=None):
        """Write the task's state entry directly, as a coordinator with file access could.

        The point of the repair is that this is not enough. Binding is a transition, and a state
        entry that merely looks like a bound task carries no evidence that the transition happened.
        """
        path = Path(config["paths"]["run_root"]) / "state.json"
        state = json.loads(path.read_text())
        entry = {"status": "prepared",
                 "current_contract": {
                     "revision": 1, "path": str(contract),
                     "sha256": hashlib.sha256(Path(contract).read_bytes()).hexdigest()}}
        if admission is not None:
            entry["admission"] = admission
        state["phases"].setdefault("build", {"status": "in-progress", "tasks": {}})
        state["phases"]["build"]["tasks"][task] = entry
        path.write_text(json.dumps(state, indent=2, sort_keys=True))

    # -- the matrix ------------------------------------------------------------------------------
    def test_valid_fresh_task_is_admitted_and_the_executor_receives_the_contract(self):
        work, config, candidate = self.prepare()
        contract = self.live.place_contract(config, "RQ-impl", candidate)

        admitted = self.admit(config, contract)
        self.assertEqual(admitted.returncode, 0, admitted.stderr)
        payload = json.loads(admitted.stdout)
        self.assertTrue(payload["admitted"])
        self.assertEqual(payload["provenance"], "verified")

        record = self.task_state(config)["admission"]
        self.assertEqual(record["candidate"], candidate)
        self.assertEqual(record["format"], ADMISSION_FORMAT)

        launched = self.live.launch(work, phase="build", task="RQ-impl", role="implementer")
        self.assertEqual(launched["returncode"], 0, launched.get("stderr"))
        self.assertTrue(self.executor_reached(config))

    def test_a_blocked_task_refuses_and_binds_nothing(self):
        """The `pb-handoff-1` control condition, now decided by the mechanism.

        A refused admission must leave no state at all: a task bound but unadmitted would be
        indistinguishable from a crash midway, and a later resume could read it as permission.
        """
        _work, config, candidate = self.prepare(drop_consistency=True)
        contract = self.live.place_contract(config, "RQ-impl", candidate)

        admitted = self.admit(config, contract)
        self.assertEqual(admitted.returncode, 1)
        payload = json.loads(admitted.stdout)
        self.assertFalse(payload["admitted"])
        self.assertEqual(codes(payload["findings"]), ["no-consistency-acceptance"])

        self.assertNotIn("current_contract", self.task_state(config))
        self.assertNotIn("admission", self.task_state(config))
        self.assertFalse(self.executor_reached(config))

    def test_binding_candidate_bound_execution_directly_is_refused(self):
        """Route B of the reproduction: the command that used to bind anything it was given."""
        _work, config, candidate = self.prepare(drop_consistency=True)
        contract = self.live.place_contract(config, "RQ-impl", candidate)

        bound = self.bind(config, contract)
        self.assertNotEqual(bound.returncode, 0)
        self.assertIn("admit", bound.stderr)
        self.assertNotIn("current_contract", self.task_state(config))

    def test_binding_is_still_refused_when_the_candidate_would_have_been_authorized(self):
        """The route closes on the contract's kind, not on whether the check would have passed.

        Otherwise `bind-contract` would have to run the authorization itself, and there would be
        two places that decide admission.
        """
        _work, config, candidate = self.prepare()
        contract = self.live.place_contract(config, "RQ-impl", candidate)
        bound = self.bind(config, contract)
        self.assertNotEqual(bound.returncode, 0)
        self.assertNotIn("current_contract", self.task_state(config))

    def test_a_hand_bound_task_does_not_launch(self):
        """Route C: the state entry is forged, so the launch must refuse before any worker starts.

        This is the case that decides whether the repair is enforcement or decoration. Every other
        route could be closed and this one would still leave the defect intact.
        """
        work, config, candidate = self.prepare(drop_consistency=True)
        contract = self.live.place_contract(config, "RQ-impl", candidate)
        self.hand_bind(config, contract)

        launched = self.live.launch(work, phase="build", task="RQ-impl", role="implementer")
        self.assertNotEqual(launched["returncode"], 0)
        self.assertIn("not-admitted", launched["stderr"])
        self.assertFalse(self.executor_reached(config))

    def test_an_admission_from_another_task_does_not_transfer(self):
        """A real record, correctly produced — for a different task — is still not this task's."""
        work, config, candidate = self.prepare()
        contract = self.live.place_contract(config, "RQ-impl", candidate)
        self.assertEqual(self.admit(config, contract, task="RQ-impl").returncode, 0)
        borrowed = self.task_state(config, "RQ-impl")["admission"]

        other = Path(config["paths"]["run_root"]) / "contracts" / "RQ-impl-2.md"
        other.write_text(contract.read_text(encoding="utf-8") + "\n<!-- a second revision -->\n",
                         encoding="utf-8")
        self.hand_bind(config, other, task="RQ-impl-2", admission=borrowed)

        launched = self.live.launch(work, phase="build", task="RQ-impl-2", role="implementer")
        self.assertNotEqual(launched["returncode"], 0)
        self.assertIn("admission-contract-mismatch", launched["stderr"])
        self.assertFalse(self.executor_reached(config))

    def test_rebinding_a_new_revision_drops_the_admission(self):
        """A revised contract is a new task authority and needs its own admission.

        Carrying the old record forward would let a contract be admitted in one form and executed
        in another — the same substitution the contract digest already prevents at launch, closed
        here at the point where the substitution would be made.
        """
        _work, config, candidate = self.prepare()
        contract = self.live.place_contract(config, "RQ-impl", candidate)
        self.assertEqual(self.admit(config, contract).returncode, 0)
        self.assertIn("admission", self.task_state(config))

        contract.write_text(contract.read_text(encoding="utf-8") + "\n<!-- revised -->\n",
                            encoding="utf-8")
        readmitted = self.admit(config, contract)
        self.assertEqual(readmitted.returncode, 0, readmitted.stderr)
        fresh = self.task_state(config)["admission"]
        self.assertEqual(fresh["contract_sha256"],
                         hashlib.sha256(contract.read_bytes()).hexdigest())

    def test_a_task_admitted_under_one_candidate_continues_after_the_project_moves(self):
        """A6.4, mechanically: a C1 task stays a C1 task when the project becomes C2.

        The project is mutated after admission so that it no longer derives the admitted candidate
        — `pb_execution.py authorize` would now refuse — and the already-admitted task still
        launches. This is the case where enforcing more would be wrong.
        """
        work, config, candidate = self.prepare()
        contract = self.live.place_contract(config, "RQ-impl", candidate)
        self.assertEqual(self.admit(config, contract).returncode, 0)

        # The project moves. A ledgered artifact changes, so the freeze no longer compares equal.
        member = Path(config["paths"]["project"]) / "requirements.md"
        member.write_text(member.read_text(encoding="utf-8") + "\n- a later requirement\n",
                          encoding="utf-8")

        reauthorize = subprocess.run(
            [PYTHON, str(SCRIPTS / "pb_execution.py"), "authorize",
             "--graph", config["paths"]["graph"], "--ledger", config["paths"]["ledger"],
             "--project-root", config["paths"]["project"],
             "--consistency", config["paths"]["consistency"],
             "--run-root", config["paths"]["run_root"], "--candidate", candidate],
            text=True, capture_output=True)
        self.assertNotEqual(reauthorize.returncode, 0,
                            "the fixture no longer demonstrates a moved project")

        launched = self.live.launch(work, phase="build", task="RQ-impl", role="implementer")
        self.assertEqual(launched["returncode"], 0, launched.get("stderr"))
        self.assertTrue(self.executor_reached(config))

    def test_review_and_repair_continue_under_the_one_admission(self):
        """Implementation, independent review, repair, re-review and acceptance: one admission.

        Re-admitting per attempt would consult the *current* graph at each step and make a long
        task's authority drift under it. The rehearsal drives the whole cycle through the shipped
        entry points; what is asserted here is that it completes with exactly one admission.
        """
        work = Path(tempfile.mkdtemp(prefix="pb-m4-repair-"))
        self.addCleanup(shutil.rmtree, work, True)
        result = self.live.rehearse(work, path="repair")
        self.assertEqual(result["outcome"], "accepted", result["steps"])
        admissions = [s for s in result["steps"] if s.get("step") == "admission"]
        self.assertEqual(len(admissions), 1, result["steps"])
        self.assertTrue(admissions[0]["admitted"])
        self.assertIn("repair launched", [s.get("step") for s in result["steps"]])

    def test_admit_refuses_what_it_is_not_for(self):
        """The two contracts `admit` must send elsewhere rather than quietly handle.

        Both refusals matter for the same reason: if `admit` silently accepted a contract outside
        its subject, the record it wrote would assert an authorization that was never the question.
        """
        _work, config, candidate = self.prepare()

        inherited = Path(config["paths"]["run_root"]) / "contracts" / "legacy.md"
        inherited.write_text("# Task L1\nContract revision: r0001\n\n## Objective\nX\n\n"
                             "## Allowed source changes\n- `dispatch.py`\n\n"
                             "## Acceptance criteria\n- AC-001 x\n", encoding="utf-8")
        refused = self.admit(config, inherited, task="L1")
        self.assertEqual(codes(json.loads(refused.stdout)["findings"]), ["no-candidate-declared"])

        upstream = self.live.place_contract(config, "RQ-consistency", candidate)
        refused = self.admit(config, upstream, task="RQ-consistency")
        self.assertEqual(codes(json.loads(refused.stdout)["findings"]),
                         ["not-candidate-bound-execution"])

        # Neither refusal may leave a binding behind.
        self.assertEqual(self.task_state(config, "L1"), {})
        self.assertEqual(self.task_state(config, "RQ-consistency"), {})

    def test_admitting_against_another_project_is_refused_where_the_mistake_was_made(self):
        """A record about the wrong project would be internally consistent and about nothing here."""
        _work, config, candidate = self.prepare()
        contract = self.live.place_contract(config, "RQ-impl", candidate)
        elsewhere = Path(config["paths"]["project"]).parent / "not-this-project"
        elsewhere.mkdir(exist_ok=True)

        refused = subprocess.run(
            [PYTHON, str(SCRIPTS / "pb_execution.py"), "admit",
             "--run-root", config["paths"]["run_root"], "--phase-id", "build",
             "--task-id", "RQ-impl", "--contract", str(contract),
             "--graph", config["paths"]["graph"], "--ledger", config["paths"]["ledger"],
             "--project-root", str(elsewhere), "--consistency", config["paths"]["consistency"]],
            text=True, capture_output=True)
        self.assertEqual(refused.returncode, 1)
        self.assertEqual(codes(json.loads(refused.stdout)["findings"]), ["project-not-this-run"])
        self.assertNotIn("admission", self.task_state(config))

    def test_a_refused_admission_leaves_the_state_file_byte_identical(self):
        """There is no instant in which a task is bound and unadmitted.

        This is what makes the boundary safe across an interruption. If admission were two writes,
        a process killed between them would leave a bound, unadmitted task — and a resuming
        coordinator could not tell that from a bypass, because the two would look the same. One
        atomic write means a crash either leaves the task untouched or leaves it fully admitted.
        """
        _work, config, candidate = self.prepare(drop_consistency=True)
        contract = self.live.place_contract(config, "RQ-impl", candidate)
        state_path = Path(config["paths"]["run_root"]) / "state.json"
        before = state_path.read_bytes()

        self.assertEqual(self.admit(config, contract).returncode, 1)
        self.assertEqual(state_path.read_bytes(), before)

    def test_a_resumed_coordinator_launches_from_the_recorded_admission_alone(self):
        """Admission survives the coordinator that granted it.

        Nothing is held in memory between admitting and launching: the launch reads the record from
        `state.json` in a process that never saw the admission, which is the resume case and also
        the reason the record has to name the contract and project rather than merely exist.
        """
        work, config, candidate = self.prepare()
        contract = self.live.place_contract(config, "RQ-impl", candidate)
        self.assertEqual(self.admit(config, contract).returncode, 0)

        # The contract is admitted; simulate the coordinator vanishing by discarding every handle
        # to it and driving the launch purely from what is on disk.
        recorded = json.loads(Path(config["paths"]["run_root"]).joinpath("state.json").read_text())
        self.assertIn("admission", recorded["phases"]["build"]["tasks"]["RQ-impl"])

        launched = self.live.launch(work, phase="build", task="RQ-impl", role="implementer")
        self.assertEqual(launched["returncode"], 0, launched.get("stderr"))
        self.assertTrue(self.executor_reached(config))

    def test_a_missing_authority_input_is_an_error_not_an_admission(self):
        """A guard that cannot run must not resolve to permission.

        The failure mode worth naming: an unreadable graph producing an empty finding list and an
        `admitted: true`. It must be an error, and it must bind nothing.
        """
        _work, config, candidate = self.prepare()
        contract = self.live.place_contract(config, "RQ-impl", candidate)
        Path(config["paths"]["graph"]).unlink()

        attempted = self.admit(config, contract)
        self.assertNotEqual(attempted.returncode, 0)
        self.assertNotIn('"admitted": true', attempted.stdout)
        self.assertNotIn("admission", self.task_state(config))
        self.assertFalse(self.executor_reached(config))


if __name__ == "__main__":
    unittest.main()

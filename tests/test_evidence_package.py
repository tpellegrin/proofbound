"""Try to make an evidence package say something it should not.

`pb-handoff-1` produced real observations and then lost the data they were computed from. Its
aggregate arithmetic can still be checked from retained totals; its per-call attribution cannot be
checked at all. This module is the falsification pass on the fix: the package exists so that the
mechanical observations survive the run, and the way to find out whether it does is to try to break
it rather than to watch it agree with itself.

**Expectations here are computed by hand, not by the exporter.** A test whose expected value comes
from the code under test is a round trip: the exporter and the reader can agree perfectly while both
misread the session. So the usage fixtures below carry token counts chosen to make their sums
obvious, and the assertions state those sums as literals.

The four kinds never collapse. Every case below asserts a *kind* as well as a status, because
"integrity holds and usage is unavailable" must never round to "verified".
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLICE = ROOT / "evals" / "authority_slice"
sys.path.insert(0, str(SLICE))
sys.path.insert(0, str(ROOT / "evals"))

import _package                                                        # noqa: E402


def write_session(db: Path, calls: list[dict], *, session: str = "ses_fixture",
                  title: str = "fixture") -> None:
    """A minimal OpenCode session in the shape the profiler reads.

    Each entry describes one model call: `tokens` present means it finished, absent means it
    started and did not. `duplicate` repeats the part row verbatim, which is what a retried write
    leaves behind.
    """
    conn = sqlite3.connect(db)
    conn.execute("create table if not exists session (id text, title text)")
    conn.execute("create table if not exists message "
                 "(id text, session_id text, time_created integer, data text)")
    conn.execute("create table if not exists part (id text, message_id text, data text)")
    conn.execute("insert into session values (?, ?)", (session, title))
    for n, call in enumerate(calls):
        mid = f"{session}_m{n}"
        conn.execute("insert into message values (?, ?, ?, ?)", (
            mid, call.get("session", session), 1000 + n,
            json.dumps({"role": "assistant", "modelID": call.get("model", "deepseek-v4-flash"),
                        "providerID": "deepseek"})))
        conn.execute("insert into part values (?, ?, ?)",
                     (f"{mid}_s", mid, json.dumps({"type": "step-start"})))
        if "tokens" in call:
            part = {"type": "step-finish", "tokens": call["tokens"]}
            if "cost" in call:
                part["cost"] = call["cost"]
            conn.execute("insert into part values (?, ?, ?)", (f"{mid}_f", mid, json.dumps(part)))
            if call.get("duplicate"):
                conn.execute("insert into part values (?, ?, ?)",
                             (f"{mid}_f", mid, json.dumps(part)))
        if call.get("unparseable"):
            conn.execute("insert into part values (?, ?, ?)", (f"{mid}_x", mid, "{not json"))
    conn.commit()
    conn.close()


class UsageEventsTest(unittest.TestCase):
    """The accounting layer, against sessions whose totals are obvious by inspection."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-events-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.db = self.tmp / "session.db"

    def test_totals_match_a_hand_computed_sum(self):
        write_session(self.db, [
            {"tokens": {"input": 100, "output": 10, "reasoning": 1,
                        "cache": {"read": 1000, "write": 0}}, "cost": 0.001},
            {"tokens": {"input": 200, "output": 20, "reasoning": 2,
                        "cache": {"read": 2000, "write": 5}}, "cost": 0.002},
        ])
        events = _package.events_from_db(self.db)
        self.assertTrue(events["available"])
        self.assertEqual(events["anomalies"], [])
        usage = _package.usage_from_rows(events["rows"])
        # Hand-computed: two calls, 100+200 input, 10+20 output, 1+2 reasoning, 1000+2000 read.
        self.assertEqual(usage["calls_started"], 2)
        self.assertEqual(usage["calls_finished"], 2)
        self.assertEqual(usage["input"], 300)
        self.assertEqual(usage["output"], 30)
        self.assertEqual(usage["reasoning"], 3)
        self.assertEqual(usage["cache_read"], 3000)
        self.assertEqual(usage["cache_write"], 5)
        self.assertAlmostEqual(usage["executor_cost"], 0.003, places=8)

    def test_a_started_call_that_never_finished_stays_incomplete(self):
        write_session(self.db, [
            {"tokens": {"input": 100, "output": 10, "cache": {"read": 0, "write": 0}}},
            {},                                       # started, no step-finish
        ])
        usage = _package.usage_from_rows(_package.events_from_db(self.db)["rows"])
        self.assertEqual(usage["calls_started"], 2)
        self.assertEqual(usage["calls_finished"], 1)
        self.assertEqual(usage["input"], 100, "an unfinished call must not contribute zeros")

    def test_a_malformed_row_is_recorded_not_dropped(self):
        write_session(self.db, [
            {"tokens": {"input": "lots", "output": 10, "cache": {"read": 0, "write": 0}}},
        ])
        events = _package.events_from_db(self.db)
        kinds = {a["kind"] for a in events["anomalies"]}
        self.assertIn("non-numeric-token-count", kinds)
        usage = _package.usage_from_rows(events["rows"])
        self.assertEqual(usage["output"], 10)
        self.assertEqual(usage["input"], 0,
                         "a token count that could not be read contributes nothing and is "
                         "reported; it must not be invented")

    def test_a_finished_call_with_no_tokens_is_an_anomaly(self):
        write_session(self.db, [{"tokens": None}])
        events = _package.events_from_db(self.db)
        self.assertIn("step-finish-without-tokens", {a["kind"] for a in events["anomalies"]})

    def test_a_duplicated_row_is_reported(self):
        write_session(self.db, [
            {"tokens": {"input": 100, "output": 10, "cache": {"read": 0, "write": 0}},
             "duplicate": True},
        ])
        events = _package.events_from_db(self.db)
        self.assertIn("duplicate-part-id", {a["kind"] for a in events["anomalies"]})

    def test_an_unparseable_row_is_reported(self):
        write_session(self.db, [
            {"tokens": {"input": 1, "output": 1, "cache": {"read": 0, "write": 0}},
             "unparseable": True},
        ])
        events = _package.events_from_db(self.db)
        self.assertIn("unparseable-row", {a["kind"] for a in events["anomalies"]})

    def test_a_missing_database_is_unavailable_not_empty(self):
        events = _package.events_from_db(self.tmp / "absent.db")
        self.assertFalse(events["available"])
        self.assertIn("no session database", events["reason"])

    def test_equal_call_counts_do_not_establish_per_attempt_attribution(self):
        """The inference `pb-authority-demo-2`'s audit already caught being made once."""
        write_session(self.db, [
            {"tokens": {"input": 1, "output": 1, "cache": {"read": 0, "write": 0}}}])
        rows = _package.events_from_db(self.db)["rows"]
        attempts = [{"event_dir": "implementer-1", "session_id": None},
                    {"event_dir": "reviewer-1", "session_id": None}]
        verdict = _package.attribution(rows, attempts)
        self.assertFalse(verdict["per_attempt_attribution_established"])
        self.assertEqual([u["event_dir"] for u in verdict["unresolved"]],
                         ["implementer-1", "reviewer-1"])

        named = [{"event_dir": "implementer-1", "session_id": "ses_fixture"}]
        self.assertTrue(
            _package.attribution(rows, named)["per_attempt_attribution_established"])


class CheckKindsTest(unittest.TestCase):
    def test_a_reported_check_can_never_claim_ok(self):
        """The single most important property: a semantic judgment is not a verification."""
        entry = _package.check("review.findings", _package.REPORTED, _package.OK, "the agent said so")
        self.assertEqual(entry["status"], _package.REPORTED)

    def test_the_other_kinds_keep_the_status_they_are_given(self):
        for kind in (_package.INTEGRITY, _package.RECOMPUTE, _package.UNAVAILABLE):
            self.assertEqual(
                _package.check("x", kind, _package.MISMATCH, "")["status"], _package.MISMATCH)


if __name__ == "__main__":
    unittest.main()


class PackageLifecycleTest(unittest.TestCase):
    """Whole packages, from a real rehearsal, then attacked.

    One rehearsal is driven for the class and each case works on its own copy: a package is meant
    to be relocatable, so copying it is not a workaround here, it is the property under test.
    """

    valid: Path
    blocked: Path
    workdir: Path

    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(SLICE))
        import _live

        cls.workdir = Path(tempfile.mkdtemp(prefix="pb-pkg-"))
        cls.clean_result = _live.rehearse(cls.workdir / "clean", path="clean")
        cls.blocked_result = _live.rehearse(cls.workdir / "blocked", path="blocked")
        cls.valid = cls.workdir / "clean" / "evidence-package"
        cls.blocked = cls.workdir / "blocked" / "evidence-package"

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.workdir, ignore_errors=True)

    def copy(self, source: Path) -> Path:
        target = Path(tempfile.mkdtemp(prefix="pb-relocated-")) / "package"
        self.addCleanup(shutil.rmtree, target.parent, True)
        shutil.copytree(source, target)
        return target

    def status(self, report: dict, check_id: str) -> tuple[str, str]:
        entry = next(c for c in report["checks"] if c["id"] == check_id)
        return entry["kind"], entry["status"]

    # -- the workflow collects evidence at all ----------------------------------------------
    def test_every_rehearsal_path_preserves_its_evidence(self):
        for result in (self.clean_result, self.blocked_result):
            with self.subTest(path=result["path"]):
                self.assertTrue(result["evidence"]["preserved"], result["evidence"])
                self.assertTrue((Path(result["evidence"]["package"]) / "manifest.json").is_file())

    def test_a_complete_rehearsal_agrees_within_its_declared_scope(self):
        report = _package.verify(self.valid, recheck_artifact=True, timeout=10)
        for check_id in ("files.integrity", "launch.attempts", "usage.recompute",
                         "price.recompute", "artifact.retained", "artifact.recheck",
                         "authority.binding", "authority.admission"):
            with self.subTest(check=check_id):
                self.assertEqual(self.status(report, check_id)[1], _package.OK)
        self.assertEqual(report["counts"].get(_package.MISMATCH), None)

    def test_a_refusal_is_supported_without_inventing_a_provider_session(self):
        report = _package.verify(self.blocked)
        kind, status = self.status(report, "launch.attempts")
        self.assertEqual((kind, status), (_package.RECOMPUTE, _package.OK))
        entry = next(c for c in report["checks"] if c["id"] == "launch.attempts")
        self.assertEqual(entry["own"], [], "the blocked condition launched no worker of its own")
        self.assertTrue(entry["seeded"], "the seeded upstream attempts must still be retained")
        # And the accounting it cannot support stays unavailable rather than reading as zero spend.
        self.assertEqual(self.status(report, "usage.recompute"),
                         (_package.UNAVAILABLE, _package.UNAVAILABLE))

    # -- relocation --------------------------------------------------------------------------
    def test_a_relocated_package_checks_without_its_original_paths(self):
        """The case `pb-handoff-1` could not satisfy: the workdir and databases are gone."""
        relocated = self.copy(self.valid)
        manifest = json.loads((relocated / "manifest.json").read_text())
        original = Path(manifest["subject"]["run_root"])
        self.assertFalse(str(relocated).startswith(str(original.parents[3])),
                         "the copy must not sit inside the original tree")

        report = _package.verify(relocated, recheck_artifact=True, timeout=10)
        self.assertEqual(report["counts"].get(_package.MISMATCH), None, report["counts"])
        for check_id in ("files.integrity", "usage.recompute", "price.recompute",
                         "artifact.recheck"):
            with self.subTest(check=check_id):
                self.assertEqual(self.status(report, check_id)[1], _package.OK)

    def test_relocation_does_not_rewrite_recorded_subject_identities(self):
        """Evidence that has been edited to satisfy a checker has stopped being evidence."""
        relocated = self.copy(self.valid)
        before = json.loads((self.valid / "manifest.json").read_text())["subject"]
        after = json.loads((relocated / "manifest.json").read_text())["subject"]
        self.assertEqual(before, after)
        _package.verify(relocated)
        again = json.loads((relocated / "manifest.json").read_text())["subject"]
        self.assertEqual(after, again, "verification must not write to the package")

    def test_verification_makes_no_change_to_the_package(self):
        relocated = self.copy(self.valid)
        before = {p.relative_to(relocated).as_posix(): _package.sha256_file(p)
                  for p in sorted(relocated.rglob("*")) if p.is_file()}
        _package.verify(relocated, recheck_artifact=True, timeout=10)
        after = {p.relative_to(relocated).as_posix(): _package.sha256_file(p)
                 for p in sorted(relocated.rglob("*")) if p.is_file()}
        self.assertEqual(before, after)

    # -- tampering ---------------------------------------------------------------------------
    def test_a_changed_artifact_is_reported(self):
        relocated = self.copy(self.valid)
        artifact = relocated / _package.FILES_DIR / "delivered" / "dispatch.py"
        artifact.write_text(artifact.read_text() + "\n# a later edit\n", encoding="utf-8")
        report = _package.verify(relocated)
        self.assertEqual(self.status(report, "files.integrity")[1], _package.MISMATCH)
        self.assertEqual(self.status(report, "artifact.retained")[1], _package.MISMATCH)

    def test_a_contract_that_no_longer_matches_its_binding_is_reported(self):
        relocated = self.copy(self.valid)
        contract = next((relocated / _package.FILES_DIR / "run" / "contracts").glob("RQ-impl.md"))
        contract.write_text(contract.read_text() + "\n<!-- edited -->\n", encoding="utf-8")
        report = _package.verify(relocated)
        self.assertEqual(self.status(report, "authority.binding")[1], _package.MISMATCH)

    def test_an_admission_naming_another_contract_is_reported(self):
        relocated = self.copy(self.valid)
        state_path = relocated / _package.FILES_DIR / "run" / "state.json"
        state = json.loads(state_path.read_text())
        task = state["phases"]["build"]["tasks"]["RQ-impl"]
        task["admission"]["contract_sha256"] = "f" * 64
        state_path.write_text(json.dumps(state, indent=2, sort_keys=True))
        report = _package.verify(relocated)
        self.assertEqual(self.status(report, "authority.admission")[1], _package.MISMATCH)
        self.assertIn("different contract revision",
                      next(c for c in report["checks"]
                           if c["id"] == "authority.admission")["detail"])

    def test_requirements_that_do_not_match_their_digest_block_the_recheck(self):
        """Grading retained bytes against a different authority is not a recheck."""
        relocated = self.copy(self.valid)
        req = relocated / _package.FILES_DIR / "delivered" / "accepted-requirements.md"
        req.write_text(req.read_text() + "\n- a later requirement\n", encoding="utf-8")
        report = _package.verify(relocated, recheck_artifact=True, timeout=10)
        kind, status = self.status(report, "artifact.recheck")
        self.assertEqual((kind, status), (_package.INTEGRITY, _package.MISMATCH))

    def test_usage_events_edited_after_export_are_reported(self):
        relocated = self.copy(self.valid)
        events = relocated / _package.EVENTS
        payload = json.loads(events.read_text())
        for row in payload["rows"]:
            if row.get("type") == "step-finish" and row.get("input"):
                row["input"] = int(row["input"]) * 2
                break
        events.write_text(json.dumps(payload, indent=2, sort_keys=True))
        report = _package.verify(relocated)
        self.assertEqual(self.status(report, "usage.recompute")[1], _package.MISMATCH)

    # -- partial evidence ---------------------------------------------------------------------
    def test_a_trace_lost_after_export_is_reported_and_blocks_only_its_own_checks(self):
        """Losing a declared file is not the same as never having collected it.

        A package that promised a trace and no longer has one has an integrity problem, and saying
        so is the point — the alternative is a reader who cannot tell a deletion from a run that
        was always this thin. The checks that did not need the trace stay usable either way.
        """
        relocated = self.copy(self.valid)
        (relocated / _package.EVENTS).unlink()
        report = _package.verify(relocated, recheck_artifact=True, timeout=10)

        integrity = next(c for c in report["checks"] if c["id"] == "files.integrity")
        self.assertEqual(integrity["status"], _package.MISMATCH)
        self.assertEqual(integrity["missing"], [_package.EVENTS],
                         "integrity must name exactly what went missing")

        for blocked_check in ("usage.recompute", "price.recompute", "coverage.tool-exposure"):
            with self.subTest(check=blocked_check):
                self.assertEqual(self.status(report, blocked_check)[1], _package.UNAVAILABLE)
        for still_usable in ("launch.attempts", "authority.binding", "artifact.recheck",
                             "artifact.retained"):
            with self.subTest(check=still_usable):
                self.assertEqual(self.status(report, still_usable)[1], _package.OK)

    def test_a_trace_never_collected_is_declared_rather_than_missing(self):
        """The other half: the blocked condition never had a live session to record."""
        report = _package.verify(self.blocked)
        self.assertEqual(self.status(report, "files.integrity")[1], _package.OK)
        self.assertEqual(self.status(report, "usage.recompute"),
                         (_package.UNAVAILABLE, _package.UNAVAILABLE))
        manifest = json.loads((self.blocked / "manifest.json").read_text())
        blocks = [o for o in manifest["omitted"] if "usage.recompute" in o.get("blocks", [])]
        self.assertTrue(blocks, "an omission must say which checks it prevents")

    def test_coverage_claims_never_become_evidence_of_absence(self):
        report = _package.verify(self.valid)
        entry = next(c for c in report["checks"] if c["id"] == "coverage.tool-exposure")
        self.assertIn(entry["status"], (_package.OK, _package.UNAVAILABLE))
        if entry["status"] == _package.UNAVAILABLE:
            # However the message is worded, it must refuse the inference from silence.
            self.assertRegex(entry["detail"],
                             "not evidence that nothing was read|not absence of reading")
        else:
            self.assertIn("exposure", entry["detail"])
            self.assertIn("neither complete reading nor understanding", entry["detail"])

    def test_no_aggregate_verdict_is_offered(self):
        report = _package.verify(self.valid)
        self.assertNotIn("verified", report)
        self.assertNotIn("valid", report)
        kinds = {c["kind"] for c in report["checks"]}
        self.assertTrue({_package.INTEGRITY, _package.RECOMPUTE} <= kinds)


class InterruptedAndReadOnlyTest(unittest.TestCase):
    """An attempt that never finished, and the promise that reading a package is inert."""

    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(SLICE))
        import _live

        cls.workdir = Path(tempfile.mkdtemp(prefix="pb-interrupted-"))
        cls.result = _live.rehearse(cls.workdir / "run", path="interrupted")
        cls.package = Path(cls.result["evidence"]["package"])

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.workdir, ignore_errors=True)

    def test_the_interrupted_path_still_preserves_its_evidence(self):
        self.assertEqual(self.result["outcome"], "terminal-unknown-spend")
        self.assertTrue(self.result["evidence"]["preserved"], self.result["evidence"])

    def test_an_unfinished_call_stays_unknown_after_export_and_replay(self):
        """The figure a run could not settle must not settle itself in the archive."""
        report = _package.verify(self.package)
        kind, status = self.status(report, "usage.completeness")
        self.assertEqual(kind, _package.RECOMPUTE)
        self.assertEqual(status, _package.UNAVAILABLE)
        detail = next(c for c in report["checks"]
                      if c["id"] == "usage.completeness")["detail"]
        self.assertRegex(detail, "did not finish|lower bound")

        manifest = json.loads((self.package / "manifest.json").read_text())
        spend = manifest.get("spend") or {}
        self.assertIs(spend.get("complete"), False,
                      "the run's own accounting recorded this as incomplete")
        self.assertGreater(manifest["usage"]["calls_started"],
                           manifest["usage"]["calls_finished"])

    def test_reading_a_package_starts_no_process(self):
        """`verify` is read-only and offline. Nothing it does may launch a model.

        Asserted by making any subprocess launch fail: if the reader shells out at all — to an
        executor, a checker it was not asked for, or anything else — this raises.
        """
        import subprocess as sp

        def refuse(*args, **kwargs):
            raise AssertionError(f"verify started a process: {args!r}")

        original = sp.run
        sp.run = refuse
        try:
            report = _package.verify(self.package)
        finally:
            sp.run = original
        self.assertTrue(report["checks"])

    def status(self, report: dict, check_id: str) -> tuple[str, str]:
        entry = next(c for c in report["checks"] if c["id"] == check_id)
        return entry["kind"], entry["status"]


class HandoffOneCompatibilityTest(unittest.TestCase):
    """Reading `pb-handoff-1`, which was collected before packages existed.

    The point is not that it passes. It is that it reports precisely what that run's retained
    files support and precisely what they do not, without reconstructing the missing records and
    without downgrading the checks that still work.
    """

    RUNS = ROOT / "evals" / "authority_slice" / "runs" / "pb-handoff-1"

    def build(self, condition: str) -> Path:
        target = Path(tempfile.mkdtemp(prefix=f"pb-h1-{condition}-")) / "package"
        self.addCleanup(shutil.rmtree, target.parent, True)
        _package.adapt_handoff_1(self.RUNS / condition, target)
        return target

    def status(self, report: dict, check_id: str) -> tuple[str, str]:
        entry = next(c for c in report["checks"] if c["id"] == check_id)
        return entry["kind"], entry["status"]

    def test_the_valid_condition_retains_what_it_retained(self):
        report = _package.verify(self.build("valid"))
        self.assertEqual(self.status(report, "files.integrity")[1], _package.OK)
        self.assertEqual(self.status(report, "authority.binding")[1], _package.OK)
        self.assertEqual(self.status(report, "artifact.retained")[1], _package.OK)
        entry = next(c for c in report["checks"] if c["id"] == "launch.attempts")
        self.assertEqual(len(entry["own"]), 2, "two live launches, per the retained ledger")
        self.assertEqual(len(entry["seeded"]), 3, "three seeded upstream attempts")

    def test_the_aggregate_price_is_re_derived_and_the_per_call_detail_is_not(self):
        """The precise boundary: arithmetic survives, attribution does not."""
        package = self.build("valid")
        report = _package.verify(package)

        kind, status = self.status(report, "price.recompute")
        self.assertEqual((kind, status), (_package.RECOMPUTE, _package.OK))
        entry = next(c for c in report["checks"] if c["id"] == "price.recompute")
        self.assertIn("0.020516", entry["detail"])
        self.assertEqual(entry["recomputed_from"], "retained aggregate totals")

        for gone in ("usage.recompute", "usage.attribution", "coverage.tool-exposure"):
            with self.subTest(check=gone):
                self.assertEqual(self.status(report, gone)[1], _package.UNAVAILABLE)

    def test_the_price_check_is_arithmetic_and_not_an_echo(self):
        """Perturb the token totals: a check that only repeated the stored figure would agree."""
        package = self.build("valid")
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        recorded = manifest["spend"]["derived"]
        manifest["usage"]["output"] += 10_000
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

        entry = next(c for c in _package.verify(package)["checks"]
                     if c["id"] == "price.recompute")
        self.assertEqual(entry["status"], _package.MISMATCH)
        self.assertIn(str(recorded), entry["detail"])

    def test_the_historical_controls_refusal_is_reported_not_mechanically_recorded(self):
        """A correction to this reader's own first assessment.

        `pb-handoff-1`'s control launched nothing, and the earlier version of this reader read that
        absence as a refusal. It is not: an untouched run and a refused one leave the same empty
        tree. That run's coordinator did state the refusal, in prose, and its `no-consistency-
        acceptance` finding is real — but the retained evidence carries no refusal *record*, so the
        claim is `reported`, and the absence of launches is `not-observed`.
        """
        report = _package.verify(self.build("control"))
        entry = next(c for c in report["checks"] if c["id"] == "launch.attempts")
        self.assertEqual(entry["own"], [], "the control launched no worker of its own")
        self.assertEqual(self.status(report, "launch.lifecycle")[1], _package.NOT_OBSERVED)
        self.assertEqual(self.status(report, "control.refusal")[1], _package.NOT_OBSERVED)
        self.assertEqual(self.status(report, "usage.recompute")[1], _package.UNAVAILABLE)
        # The coordinator's own account survives and remains attributable.
        self.assertEqual(self.status(report, "decision.coordinator")[1], _package.REPORTED)

    def test_a_run_predating_admission_is_not_reported_as_failing_it(self):
        """Absent machinery is unavailable, never a mismatch. That distinction is the whole file."""
        for condition in ("valid", "control"):
            with self.subTest(condition=condition):
                report = _package.verify(self.build(condition))
                kind, status = self.status(report, "authority.admission")
                self.assertEqual(status, _package.UNAVAILABLE)
                self.assertNotEqual(status, _package.MISMATCH)

    def test_the_historical_check_result_is_reported_not_reproduced(self):
        report = _package.verify(self.build("valid"))
        kind, status = self.status(report, "artifact.historical-result")
        self.assertEqual((kind, status), (_package.REPORTED, _package.REPORTED))

    def test_the_recheck_is_blocked_because_the_requirements_were_not_retained(self):
        """Not a failure of the artifact: a missing subject makes the question unanswerable."""
        report = _package.verify(self.build("valid"), recheck_artifact=True, timeout=10)
        kind, status = self.status(report, "artifact.recheck")
        self.assertEqual(status, _package.UNAVAILABLE)
        entry = next(c for c in report["checks"] if c["id"] == "artifact.recheck")
        self.assertIn("requirements", entry["detail"])

    def test_the_original_evidence_is_never_modified(self):
        before = {p.relative_to(self.RUNS).as_posix(): _package.sha256_file(p)
                  for p in sorted(self.RUNS.rglob("*")) if p.is_file()}
        for condition in ("valid", "control"):
            package = self.build(condition)
            _package.verify(package, recheck_artifact=True, timeout=10)
        after = {p.relative_to(self.RUNS).as_posix(): _package.sha256_file(p)
                 for p in sorted(self.RUNS.rglob("*")) if p.is_file()}
        self.assertEqual(before, after, "retained run evidence must be immutable")


class AttributionAndReconciliationTest(unittest.TestCase):
    """The counterexamples that passed at `4133e70`, and the positives that must still pass.

    Each expected outcome is stated from the fixture's own construction, not from what the code
    returns. A checker that rejected everything would satisfy the negatives alone, so the positive
    cases are kept beside them.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-attrib-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_tree(self, attempts: dict, *, name: str = "run") -> Path:
        """A run tree with one directory per attempt, each naming whatever session it claims."""
        run = self.tmp / name
        for event, session in attempts.items():
            directory = run / "attempts" / event
            directory.mkdir(parents=True)
            (directory / "attempt.json").write_text(
                json.dumps({"started_at": "2026-09-21T12:00:00+00:00"}))
            terminal = {"status": "completed"}
            if session is not None:
                terminal["session_id"] = session
            (directory / "terminal.json").write_text(json.dumps(terminal))
        return run

    def package(self, run: Path, db: Path | None, *, own: list[str]) -> Path:
        import _guard

        into = self.tmp / f"pkg-{run.name}-{len(list(self.tmp.iterdir()))}"
        _package.export(run_root=run, into=into, experiment="probe", condition="c",
                        session_db=db, event_dirs=own,
                        config={"model": _guard.MODEL, "paths": {"run_root": str(run)}})
        return into

    def status(self, report: dict, check_id: str) -> str:
        return next(c for c in report["checks"] if c["id"] == check_id)["status"]

    # -- a session the database does not contain -------------------------------------------
    def test_a_named_session_absent_from_the_database_is_not_attribution(self):
        import _guard

        run = self.run_tree({"implementer-1": "ses_missing"})
        db = self.tmp / "a.db"
        write_session(db, [{"tokens": {"input": 100, "output": 10,
                                       "cache": {"read": 0, "write": 0}}}], session="ses_actual")
        spend = _guard.spend(run, db)
        self.assertFalse(spend["complete"], "an unresolvable attempt cannot settle the figure")
        self.assertIn("ses_missing", spend["claim"])

        report = _package.verify(self.package(run, db, own=["implementer-1"]))
        self.assertEqual(self.status(report, "usage.attribution"), _package.UNAVAILABLE)

    def test_a_resolvable_session_still_attributes(self):
        """The positive case, so the repair is a discrimination and not a refusal to answer."""
        import _guard

        run = self.run_tree({"implementer-1": "ses_actual"})
        db = self.tmp / "b.db"
        write_session(db, [{"tokens": {"input": 100, "output": 10,
                                       "cache": {"read": 0, "write": 0}}}], session="ses_actual")
        self.assertTrue(_guard.spend(run, db)["complete"], _guard.spend(run, db)["claim"])
        report = _package.verify(self.package(run, db, own=["implementer-1"]))
        self.assertEqual(self.status(report, "usage.attribution"), _package.OK)

    def test_a_session_no_attempt_claims_is_unexplained(self):
        import _guard

        run = self.run_tree({"implementer-1": "ses_one"})
        db = self.tmp / "c.db"
        write_session(db, [{"tokens": {"input": 1, "output": 1,
                                       "cache": {"read": 0, "write": 0}}}], session="ses_one")
        write_session(db, [{"tokens": {"input": 1, "output": 1,
                                       "cache": {"read": 0, "write": 0}}}], session="ses_two")
        spend = _guard.spend(run, db)
        self.assertFalse(spend["complete"])
        self.assertIn("ses_two", spend["claim"])

    def test_one_session_claimed_by_two_attempts_blocks_the_split_not_the_total(self):
        """A split problem and a total problem are different, and conflating them is expensive.

        Both attempts are this run's and so is the session, so the aggregate is whole: refusing
        the next launch over it would stop a run for a division nobody needed. What is genuinely
        unavailable is *which* attempt spent what.
        """
        import _guard

        run = self.run_tree({"implementer-1": "ses_one", "reviewer-1": "ses_one"})
        db = self.tmp / "d.db"
        write_session(db, [{"tokens": {"input": 1, "output": 1,
                                       "cache": {"read": 0, "write": 0}}}], session="ses_one")
        spend = _guard.spend(run, db)
        self.assertTrue(spend["complete"], spend["claim"])
        self.assertEqual(spend["session_attribution"]["reused"],
                         {"ses_one": ["implementer-1", "reviewer-1"]})
        self.assertFalse(spend["session_attribution"]["per_attempt_attribution_established"])

        report = _package.verify(self.package(run, db, own=["implementer-1", "reviewer-1"]))
        self.assertEqual(self.status(report, "usage.attribution"), _package.UNAVAILABLE)
        self.assertEqual(self.status(report, "price.recompute"), _package.OK)

    def test_an_attempt_with_no_identifier_at_all_is_unattributed(self):
        import _guard

        run = self.run_tree({"implementer-1": None})
        db = self.tmp / "e.db"
        write_session(db, [{"tokens": {"input": 1, "output": 1,
                                       "cache": {"read": 0, "write": 0}}}], session="ses_one")
        self.assertFalse(_guard.spend(run, db)["complete"])

    # -- balanced totals that do not reconcile ---------------------------------------------
    def test_balanced_totals_with_unpaired_calls_do_not_settle(self):
        """A start in one message and a finish in another: one of each, no call known to finish."""
        import _guard

        run = self.run_tree({"implementer-1": "ses_split"})
        db = self.tmp / "f.db"
        conn = sqlite3.connect(db)
        conn.execute("create table session (id text, title text)")
        conn.execute("create table message "
                     "(id text, session_id text, time_created integer, data text)")
        conn.execute("create table part (id text, message_id text, data text)")
        conn.execute("insert into session values ('ses_split','t')")
        meta = json.dumps({"role": "assistant", "modelID": "deepseek-v4-flash"})
        conn.execute("insert into message values ('m1','ses_split',1,?)", (meta,))
        conn.execute("insert into message values ('m2','ses_split',2,?)", (meta,))
        conn.execute("insert into part values ('p1','m1',?)",
                     (json.dumps({"type": "step-start"}),))
        conn.execute("insert into part values ('p2','m2',?)", (json.dumps(
            {"type": "step-finish",
             "tokens": {"input": 10, "output": 1, "cache": {"read": 0, "write": 0}}}),))
        conn.commit()
        conn.close()

        spend = _guard.spend(run, db)
        self.assertEqual(spend["usage"]["calls_started"], spend["usage"]["calls_finished"])
        self.assertFalse(spend["complete"], "balanced is not reconciled")

        report = _package.verify(self.package(run, db, own=["implementer-1"]))
        self.assertEqual(self.status(report, "usage.completeness"), _package.UNAVAILABLE)
        # The partial total is still useful and is reported separately from whether spend is
        # established — losing it would be its own kind of dishonesty.
        self.assertEqual(self.status(report, "price.recompute"), _package.OK)

    # -- the manifest's own conclusion is not evidence --------------------------------------
    def test_editing_the_manifests_attribution_conclusion_is_caught(self):
        run = self.run_tree({"implementer-1": "ses_actual"})
        db = self.tmp / "g.db"
        write_session(db, [{"tokens": {"input": 1, "output": 1,
                                       "cache": {"read": 0, "write": 0}}}], session="ses_actual")
        package = self.package(run, db, own=["implementer-1"])
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        self.assertTrue(manifest["attribution"]["per_attempt_attribution_established"])

        # Flip the conclusion without touching the records it was drawn from.
        manifest["attribution"]["per_attempt_attribution_established"] = False
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        report = _package.verify(package)
        self.assertEqual(self.status(report, "usage.attribution"), _package.MISMATCH)

    def test_claiming_attribution_the_records_do_not_support_is_caught(self):
        """The same edit in the other direction, which is the one worth worrying about."""
        run = self.run_tree({"implementer-1": "ses_missing"})
        db = self.tmp / "h.db"
        write_session(db, [{"tokens": {"input": 1, "output": 1,
                                       "cache": {"read": 0, "write": 0}}}], session="ses_actual")
        package = self.package(run, db, own=["implementer-1"])
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["attribution"]["per_attempt_attribution_established"] = True
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        report = _package.verify(package)
        self.assertEqual(self.status(report, "usage.attribution"), _package.MISMATCH)

    # -- ledger and tree must agree ---------------------------------------------------------
    def test_a_ledger_reserving_an_attempt_the_tree_lacks_is_caught(self):
        run = self.run_tree({"implementer-1": "ses_actual"})
        (run.parent / "launch-ledger.json").write_text(json.dumps({
            "format": "proofbound-launch-ledger-v1",
            "slots": [{"slot": 1, "event_dir": str(run / "attempts" / "implementer-1"),
                       "classification": "executor-reached"},
                      {"slot": 2, "event_dir": str(run / "attempts" / "reviewer-1"),
                       "classification": "executor-reached"}]}))
        package = self.package(run, None, own=["implementer-1"])
        report = _package.verify(package)
        entry = next(c for c in report["checks"] if c["id"] == "launch.ledger-agreement")
        self.assertEqual(entry["status"], _package.MISMATCH)
        self.assertIn("reviewer-1", entry["detail"])

    def test_an_unclassified_slot_is_caught(self):
        run = self.run_tree({"implementer-1": "ses_actual"})
        (run.parent / "launch-ledger.json").write_text(json.dumps({
            "format": "proofbound-launch-ledger-v1",
            "slots": [{"slot": 1, "event_dir": str(run / "attempts" / "implementer-1"),
                       "classification": "unresolved"}]}))
        report = _package.verify(self.package(run, None, own=["implementer-1"]))
        entry = next(c for c in report["checks"] if c["id"] == "launch.ledger-agreement")
        self.assertEqual(entry["status"], _package.MISMATCH)
        self.assertIn("never classified", entry["detail"])

    # -- a refusal, and a run in which nothing happened --------------------------------------
    def test_an_untouched_run_is_not_observed_rather_than_a_refusal(self):
        run = self.run_tree({}, name="empty")
        (run / "attempts").mkdir(parents=True, exist_ok=True)
        (run / "state.json").write_text(json.dumps({"phases": {}}))
        report = _package.verify(self.package(run, None, own=[]))
        self.assertEqual(self.status(report, "control.refusal"), _package.NOT_OBSERVED)
        self.assertEqual(self.status(report, "launch.lifecycle"), _package.NOT_OBSERVED)

    def test_a_recorded_refusal_with_no_execution_supports_the_claim(self):
        import _guard

        run = self.run_tree({}, name="refused")
        (run / "attempts").mkdir(parents=True, exist_ok=True)
        (run / "state.json").write_text(json.dumps({"phases": {}}))
        refusal = self.tmp / "authorization-refusal.json"
        refusal.write_text(json.dumps({
            "admitted": False, "candidate": "a" * 64,
            "findings": [{"code": "no-consistency-acceptance", "reason": "none recorded"}]}))
        into = self.tmp / "pkg-refused"
        _package.export(run_root=run, into=into, experiment="probe", condition="control",
                        event_dirs=[], refusal=refusal,
                        config={"model": _guard.MODEL, "paths": {"run_root": str(run)}})
        report = _package.verify(into)
        entry = next(c for c in report["checks"] if c["id"] == "control.refusal")
        self.assertEqual(entry["status"], _package.OK)
        self.assertEqual(entry["findings"], ["no-consistency-acceptance"])

    def test_a_refusal_claimed_alongside_launches_is_caught(self):
        """Both halves are required: a record *and* the absence of execution."""
        import _guard

        run = self.run_tree({"implementer-1": "ses_actual"}, name="refused-but-ran")
        refusal = self.tmp / "refusal2.json"
        refusal.write_text(json.dumps({
            "admitted": False, "candidate": "a" * 64,
            "findings": [{"code": "no-consistency-acceptance"}]}))
        into = self.tmp / "pkg-contradictory"
        _package.export(run_root=run, into=into, experiment="probe", condition="control",
                        event_dirs=["implementer-1"], refusal=refusal,
                        config={"model": _guard.MODEL, "paths": {"run_root": str(run)}})
        entry = next(c for c in _package.verify(into)["checks"] if c["id"] == "control.refusal")
        self.assertEqual(entry["status"], _package.MISMATCH)
        self.assertIn("execution was not withheld", entry["detail"])

    # -- required metadata --------------------------------------------------------------------
    def test_missing_required_metadata_becomes_a_named_omission(self):
        run = self.run_tree({}, name="bare")
        (run / "attempts").mkdir(parents=True, exist_ok=True)
        (run / "state.json").write_text(json.dumps({"phases": {}}))
        manifest = json.loads((self.package(run, None, own=[]) / "manifest.json").read_text())
        missing = {o["what"] for o in manifest["omitted"]}
        self.assertIn("launch-ledger.json", missing)
        self.assertIn("run-config.json", missing)
        for entry in manifest["omitted"]:
            if entry["what"] == "launch-ledger.json":
                self.assertIn("launch.ledger-agreement", entry["blocks"])

    def test_a_credential_is_refused_rather_than_packaged(self):
        home = self.tmp / "home" / ".local" / "share" / "opencode"
        home.mkdir(parents=True)
        credential = home / "auth.json"
        credential.write_text('{"key": "secret"}')
        with self.assertRaises(_package.PreservationFailure):
            _package._copy(credential, self.tmp / "pkg-cred", "run/auth.json", "x", [])


class QualificationPredicateTest(unittest.TestCase):
    """Outcome and evidence are separate predicates, and neither is `verify`'s exit code.

    The case worth guarding is a run that finishes cleanly and should still fail: a completed
    trajectory is not a correct one, and a criterion that cannot say so is decoration.
    """

    @classmethod
    def setUpClass(cls) -> None:
        sys.path.insert(0, str(SLICE))
        import _live

        cls.work = Path(tempfile.mkdtemp(prefix="pb-qual-"))
        _live.rehearse(cls.work / "valid", path="clean")
        cls.valid = Path(_live.finalize(cls.work / "valid", condition="valid",
                                        into=cls.work / "pkg-valid")["evidence"]["package"])
        _live.rehearse(cls.work / "control", path="blocked")
        cls.control = Path(_live.finalize(cls.work / "control", condition="control",
                                          into=cls.work / "pkg-control")["evidence"]["package"])

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.work, ignore_errors=True)

    def copy(self, source: Path) -> Path:
        target = Path(tempfile.mkdtemp(prefix="pb-qual-copy-")) / "package"
        self.addCleanup(shutil.rmtree, target.parent, True)
        shutil.copytree(source, target)
        return target

    def test_the_valid_condition_qualifies(self):
        report = _package.qualify(self.valid)
        self.assertTrue(report["outcome_success"]["passed"], report["outcome_success"]["why"])
        self.assertTrue(report["evidence_success"]["passed"], report["evidence_success"]["why"])
        self.assertTrue(report["qualified"])

    def test_the_control_qualifies_on_a_recorded_refusal(self):
        report = _package.qualify(self.control, recheck_artifact=False)
        self.assertTrue(report["outcome_success"]["passed"], report["outcome_success"]["why"])
        self.assertTrue(report["qualified"])

    def test_a_completed_run_that_delivered_the_wrong_thing_does_not_qualify(self):
        """The adversarial alternative: every step ran, and the result is wrong."""
        package = self.copy(self.valid)
        artifact = package / _package.FILES_DIR / "delivered" / "dispatch.py"
        artifact.write_text("def dispatch(arrivals):\n    return []\n", encoding="utf-8")
        # The manifest's digest is updated too, so this is not merely an integrity failure: the
        # package is internally consistent and describes a delivery that does not work.
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        for entry in manifest["files"]:
            if entry["role"] == "delivered-artifact":
                entry["sha256"] = _package.sha256_file(artifact)
                entry["bytes"] = artifact.stat().st_size
        manifest["extra"].pop("artifact_check", None)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

        report = _package.qualify(package)
        self.assertEqual(self.status(report, "artifact.recheck"), _package.MISMATCH)
        self.assertFalse(report["outcome_success"]["passed"])
        self.assertIn("artifact.recheck", report["outcome_success"]["why"])
        self.assertFalse(report["qualified"])

    def test_a_control_that_merely_did_nothing_does_not_qualify(self):
        package = self.copy(self.control)
        (package / _package.FILES_DIR / "run" / "authorization-refusal.json").unlink()
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"] = [f for f in manifest["files"]
                             if f["role"] != "authorization-refusal"]
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

        report = _package.qualify(package, recheck_artifact=False)
        self.assertFalse(report["outcome_success"]["passed"])
        self.assertIn("control.refusal", report["outcome_success"]["why"])
        self.assertIn("control.refusal", report["evidence_success"]["missing"])

    def test_unavailable_required_evidence_fails_the_evidence_predicate(self):
        package = self.copy(self.valid)
        (package / _package.EVENTS).unlink()
        manifest_path = package / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"] = [f for f in manifest["files"] if f["path"] != _package.EVENTS]
        manifest["omitted"].append({"what": "per-call usage events", "why": "removed",
                                    "blocks": ["usage.recompute"]})
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

        report = _package.qualify(package)
        self.assertFalse(report["evidence_success"]["passed"])
        self.assertIn("usage.recompute", report["evidence_success"]["missing"])

    def test_expected_omissions_are_labelled_and_do_not_fail_evidence(self):
        report = _package.qualify(self.valid)
        self.assertIn("coverage.tool-exposure", report["evidence_success"]["expected_omissions"])
        self.assertTrue(report["evidence_success"]["passed"])

    def test_verify_exiting_zero_does_not_satisfy_qualification(self):
        """A package of nothing but `unavailable` reports no mismatch and establishes nothing."""
        package = self.copy(self.control)
        report = _package.verify(package)
        self.assertIsNone(report["counts"].get(_package.MISMATCH))
        stripped = self.copy(self.control)
        shutil.rmtree(stripped / _package.FILES_DIR)
        (stripped / _package.FILES_DIR).mkdir()
        empty = _package.qualify(stripped, recheck_artifact=False)
        self.assertFalse(empty["qualified"])
        self.assertTrue(empty["evidence_success"]["missing"])

    def status(self, report: dict, check_id: str) -> str:
        detail = _package.verify(Path(report["package"]), recheck_artifact=True, timeout=10)
        return next(c for c in detail["checks"] if c["id"] == check_id)["status"]

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
        self.assertEqual(verdict["attempts_without_a_session"], ["implementer-1", "reviewer-1"])

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

    def test_the_control_supports_its_refusal_without_a_provider_session(self):
        report = _package.verify(self.build("control"))
        entry = next(c for c in report["checks"] if c["id"] == "launch.attempts")
        self.assertEqual(entry["own"], [])
        self.assertEqual(self.status(report, "launch.lifecycle")[1], _package.OK)
        self.assertEqual(self.status(report, "usage.recompute")[1], _package.UNAVAILABLE)

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

"""Regressions for `pb-authority-demo-2`'s spend accounting.

The predecessor's version had three defects, each reproduced before being repaired and each given a
case here:

* it priced whatever totals a session held and declared the figure `complete`, so a session with
  two model calls started and one finished read as settled;
* it treated an absent session database as proof that nothing had been spent;
* it priced at the moment the report ran rather than at the moment the work executed.

The point of each test is the *reconciliation*: a spend figure is complete only when the run tree's
launch facts and the session's usage agree. Usage alone cannot say whether a launch is missing from
it.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo" / "pb-authority-demo-2"
sys.path.insert(0, str(DEMO))
sys.path.insert(0, str(ROOT / "evals"))

import scaffold  # noqa: E402


class AccountingTest(unittest.TestCase):
    """`scaffold.spend` and `scaffold.admit`, over synthetic run trees."""

    maxDiff = None

    def setUp(self) -> None:
        self.into = Path(tempfile.mkdtemp(prefix="pb-demo2-accounting-"))
        self.addCleanup(__import__("shutil").rmtree, self.into, True)
        self.run = self.into / "project" / scaffold.RUN_RELATIVE
        self.run.mkdir(parents=True)

    def attempt(self, name: str, *, started_at: str = "2026-09-17T10:00:00+00:00",
                terminal: "dict | None" = None, session_id: str = "ses_x") -> None:
        """One recorded attempt in the run tree, as the launcher would leave it."""
        event = self.run / "attempts" / name
        event.mkdir(parents=True)
        (event / "attempt.json").write_text(json.dumps({
            "format": "dsd-worker-attempt-v3", "started_at": started_at,
            "worker_pid": 1, "launcher_pid": 2}), encoding="utf-8")
        if terminal is not None:
            payload = {"format": "dsd-worker-terminal-v3", "session_id": session_id,
                       "started_at": started_at, **terminal}
            (event / "terminal.json").write_text(json.dumps(payload), encoding="utf-8")

    def session(self, usage: "dict[str, int]") -> None:
        """A session database whose usage is whatever this test wants it to be."""
        db = self.into / "session" / "worker.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        db.write_bytes(b"not a real database; usage is supplied by the stub")
        stub_usage = dict(usage)

        def fake_profile(_db, **_kw):
            return {"usage": stub_usage}

        def fake_cost(seen, **kw):
            self.priced_when = kw.get("when")
            self.priced_usage = dict(seen)
            return {"amount": 0.0123, "currency": "USD"}

        import _pricing
        import _profile
        real_profile, real_cost = _profile.profile, _pricing.cost
        _profile.profile, _pricing.cost = fake_profile, fake_cost
        self.addCleanup(setattr, _profile, "profile", real_profile)
        self.addCleanup(setattr, _pricing, "cost", real_cost)

    # -- the reported defect ---------------------------------------------------------------------
    def test_a_started_call_that_did_not_finish_is_not_a_settled_figure(self):
        """Two started, one finished. The predecessor called this `complete: true`."""
        self.attempt("spec-author-1", terminal={"status": "completed"})
        self.session({"input": 100, "output": 50, "calls_started": 2, "calls_finished": 1})

        account = scaffold.spend(self.into)
        self.assertFalse(account["complete"], account)
        self.assertIn("did not finish", account["claim"])
        self.assertEqual(account["derived"], 0.0123, "the derived part is still reported")
        self.assertFalse(scaffold.admit(self.into)["admit"],
                         "unestablished spend must refuse a further launch")

    def test_an_absent_database_is_not_proof_of_no_expenditure(self):
        """The predecessor returned `complete: true, derived 0.0` for exactly this state."""
        self.attempt("spec-author-1", terminal={"status": "completed"})
        account = scaffold.spend(self.into)
        self.assertFalse(account["complete"], account)
        self.assertIn("unknown, not zero", account["claim"])
        self.assertEqual(account["launched_attempts"], 1)
        self.assertFalse(scaffold.admit(self.into)["admit"])

    def test_an_absent_database_with_nothing_launched_is_genuinely_zero(self):
        """The other half of the same question, so the fix is not merely pessimistic."""
        account = scaffold.spend(self.into)
        self.assertTrue(account["complete"], account)
        self.assertEqual(account["derived"], 0.0)
        self.assertEqual(account["launched_attempts"], 0)
        self.assertTrue(scaffold.admit(self.into)["admit"])

    def test_pricing_uses_the_execution_instant_not_the_reporting_instant(self):
        self.attempt("spec-author-1", started_at="2026-01-02T03:04:05+00:00",
                     terminal={"status": "completed"})
        self.attempt("spec-reflector-1", started_at="2026-01-02T04:00:00+00:00",
                     terminal={"status": "completed"})
        self.session({"input": 10, "output": 5, "calls_started": 3, "calls_finished": 3})
        scaffold.spend(self.into)
        self.assertEqual(self.priced_when.isoformat(), "2026-01-02T03:04:05+00:00",
                         "prices must be derived at the earliest execution instant")

    # -- the rest of the reconciliation ----------------------------------------------------------
    def test_an_attempt_without_a_terminal_record_is_unaccounted(self):
        self.attempt("spec-author-1", terminal={"status": "completed"})
        self.attempt("spec-reflector-1")          # launched, never reported terminal
        self.session({"input": 10, "output": 5, "calls_started": 4, "calls_finished": 4})
        account = scaffold.spend(self.into)
        self.assertFalse(account["complete"], account)
        self.assertIn("without a terminal record", account["claim"])

    def test_an_interrupted_attempt_is_unaccounted(self):
        self.attempt("spec-author-1", terminal={"status": "timeout"})
        self.session({"input": 10, "output": 5, "calls_started": 2, "calls_finished": 2})
        account = scaffold.spend(self.into)
        self.assertFalse(account["complete"], account)
        self.assertIn("did not complete", account["claim"])

    def test_usage_that_cannot_be_attributed_to_a_launch_is_unaccounted(self):
        self.attempt("spec-author-1", terminal={"status": "completed"}, session_id="")
        self.session({"input": 10, "output": 5, "calls_started": 2, "calls_finished": 2})
        account = scaffold.spend(self.into)
        self.assertFalse(account["complete"], account)
        self.assertIn("session id", account["claim"])

    def test_a_reconciled_run_is_complete_and_admits(self):
        self.attempt("spec-author-1", terminal={"status": "completed"})
        self.attempt("spec-reflector-1", terminal={"status": "completed"})
        self.session({"input": 100, "output": 50, "calls_started": 7, "calls_finished": 7})
        account = scaffold.spend(self.into)
        self.assertTrue(account["complete"], account)
        self.assertEqual(account["derived"], 0.0123)
        self.assertAlmostEqual(account["headroom"],
                               scaffold.AGGREGATE_LIMIT - scaffold.RESERVE - 0.0123, places=6)
        self.assertTrue(scaffold.admit(self.into)["admit"])

    def test_the_reserve_refuses_a_launch_near_the_limit(self):
        self.attempt("spec-author-1", terminal={"status": "completed"})
        self.session({"input": 1, "output": 1, "calls_started": 1, "calls_finished": 1})
        import _pricing
        _pricing.cost = lambda seen, **kw: {"amount": 0.35, "currency": "USD"}
        verdict = scaffold.admit(self.into)
        self.assertFalse(verdict["admit"])
        self.assertIn("exceeds", verdict["why"])


class WithholdingHonestyTest(unittest.TestCase):
    """The holdout measure must describe itself accurately."""

    def test_it_reports_withholding_rather_than_isolation(self):
        record = scaffold.check_withholding(expect_withheld=False)
        self.assertTrue(record["owner_can_restore_mode_without_privilege"])
        self.assertIn("withholding, not isolation", record["therefore"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

"""Model as an experimental condition: identity, pricing, provider gating, discoverability.

The Nemotron paired run lost five of eight pairs to a provider outage, and the repair for that is
not a bigger retry loop — it is refusing to spend a semantic slot on discovering that the provider is
down. The DeepSeek rebase adds the other half: a model whose alias moves, whose sampling parameters
are silently ignored in thinking mode, and whose calls cost real money. Each of those is something an
experiment can get quietly wrong, so each has a test.

Nothing here invokes a model.
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

import _pricing    # noqa: E402
import _profile    # noqa: E402
import _provider   # noqa: E402

MODELS_INDEX = ROOT / "evals" / "models" / "README.md"


class PriceTableTest(unittest.TestCase):
    """A cost figure without a price identity is an assertion, not evidence."""

    maxDiff = None

    def test_the_table_carries_its_own_provenance(self):
        table = _pricing.DEEPSEEK_2026_09_09
        self.assertTrue(table["source"].startswith("https://"))
        self.assertRegex(table["retrieved"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(table["currency"], "USD")
        self.assertEqual(table["per_tokens"], 1_000_000)

    def test_peak_windows_match_the_published_schedule(self):
        """01:00-04:00 and 06:00-10:00 UTC, weekdays only."""
        wednesday = lambda h, m=0: datetime(2026, 9, 9, h, m, tzinfo=timezone.utc)  # noqa: E731
        for hour in (1, 2, 3, 6, 8, 9):
            with self.subTest(hour=hour):
                self.assertEqual(_pricing.price_class(wednesday(hour)), _pricing.PEAK)
        for hour in (0, 4, 5, 10, 12, 23):
            with self.subTest(hour=hour):
                self.assertEqual(_pricing.price_class(wednesday(hour)), _pricing.OFF_PEAK)

    def test_weekends_are_never_peak(self):
        saturday = datetime(2026, 9, 12, 2, 0, tzinfo=timezone.utc)
        sunday = datetime(2026, 9, 13, 8, 0, tzinfo=timezone.utc)
        self.assertEqual(_pricing.price_class(saturday), _pricing.OFF_PEAK)
        self.assertEqual(_pricing.price_class(sunday), _pricing.OFF_PEAK)

    def test_peak_costs_exactly_twice_off_peak(self):
        usage = {"input": 100_000, "cache_read": 50_000, "output": 10_000}
        off = _pricing.cost(usage, model="deepseek-v4-flash", window=_pricing.OFF_PEAK)
        peak = _pricing.cost(usage, model="deepseek-v4-flash", window=_pricing.PEAK)
        self.assertAlmostEqual(peak["amount"], off["amount"] * 2, places=6)

    def test_cache_is_billed_on_top_of_input_not_inside_it(self):
        """Measured against the provider: reported input excludes cached tokens."""
        base = {"input": 100_000, "cache_read": 0, "output": 0}
        cached = {"input": 100_000, "cache_read": 100_000, "output": 0}
        a = _pricing.cost(base, model="deepseek-v4-flash", window=_pricing.OFF_PEAK)["amount"]
        b = _pricing.cost(cached, model="deepseek-v4-flash", window=_pricing.OFF_PEAK)["amount"]
        self.assertGreater(b, a, "cached tokens must add cost, never be subtracted from input")
        self.assertAlmostEqual(b - a, 100_000 * 0.007 / 1e6, places=8)

    def test_an_unpriced_model_reports_unknown_rather_than_free(self):
        """A free model and an unpriced one are different facts."""
        got = _pricing.cost({"input": 1, "cache_read": 0, "output": 1},
                            model="opencode/nemotron-3-ultra-free")
        self.assertIsNone(got["amount"])
        self.assertIn("no price", got["reason"])

    def test_missing_usage_fields_report_unknown_rather_than_zero(self):
        got = _pricing.cost({"cache_read": 5}, model="deepseek-v4-flash")
        self.assertIsNone(got["amount"])

    def test_a_cost_figure_names_the_table_it_came_from(self):
        got = _pricing.cost({"input": 10, "cache_read": 0, "output": 10},
                            model="deepseek-v4-flash", window=_pricing.OFF_PEAK)
        self.assertEqual(got["price_id"], _pricing.DEEPSEEK_2026_09_09["id"])
        self.assertIn("retrieved", got)
        self.assertIn("basis", got)

    def test_a_forecast_reports_the_worst_run_not_only_the_middle_one(self):
        samples = [{"input": 100_000, "cache_read": 0, "output": 1_000},
                   {"input": 200_000, "cache_read": 0, "output": 2_000},
                   {"input": 900_000, "cache_read": 0, "output": 9_000}]
        got = _pricing.forecast(samples, model="deepseek-v4-flash", window=_pricing.OFF_PEAK)
        self.assertGreater(got["per_run_max"], got["per_run_median"])
        self.assertEqual(got["runs_observed"], 3)


SCHEMA = """
CREATE TABLE message (id text PRIMARY KEY, session_id text NOT NULL,
                      time_created integer NOT NULL, time_updated integer NOT NULL,
                      data text NOT NULL);
CREATE TABLE part (id text PRIMARY KEY, message_id text NOT NULL, session_id text NOT NULL,
                   time_created integer NOT NULL, time_updated integer NOT NULL,
                   data text NOT NULL);
"""


def session(path: Path, messages: list[dict]) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    for i, data in enumerate(messages, 1):
        conn.execute("INSERT INTO message VALUES (?,?,?,?,?)",
                     (f"m{i}", "s", i * 100, i * 100, json.dumps(data)))
        conn.execute("INSERT INTO part VALUES (?,?,?,?,?,?)",
                     (f"p{i}a", f"m{i}", "s", i * 100, i * 100,
                      json.dumps({"type": "step-start"})))
        conn.execute("INSERT INTO part VALUES (?,?,?,?,?,?)",
                     (f"p{i}b", f"m{i}", "s", i * 100 + 1, i * 100 + 1,
                      json.dumps({"type": "step-finish", "cost": 0.001, "tokens": {
                          "input": 10, "output": 1, "reasoning": 0,
                          "cache": {"read": 2, "write": 0}}})))
    conn.commit()
    conn.close()
    return path


class ObservedIdentityTest(unittest.TestCase):
    """A requested alias and the identity a provider returned are two different facts."""

    maxDiff = None

    def test_it_records_what_the_provider_returned(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            db = session(tmp / "s.db", [
                {"role": "assistant", "modelID": "deepseek-v4-flash",
                 "providerID": "deepseek", "variant": "high"}])
            got = _profile.profile(db, stage="s", model="deepseek/deepseek-v4-flash",
                                   variant="high")
            self.assertEqual(got["identity"]["observed_models"], ["deepseek-v4-flash"])
            self.assertEqual(got["identity"]["observed_providers"], ["deepseek"])
            self.assertEqual(got["identity"]["observed_variants"], ["high"])
            self.assertEqual(got["model"], "deepseek/deepseek-v4-flash")
            self.assertTrue(got["complete"])
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_two_models_in_one_run_make_it_incomplete(self):
        """A run that used two models is not one measurement of either."""
        tmp = Path(tempfile.mkdtemp())
        try:
            db = session(tmp / "s.db", [
                {"role": "assistant", "modelID": "deepseek-v4-flash", "providerID": "deepseek"},
                {"role": "assistant", "modelID": "deepseek-v4-pro", "providerID": "deepseek"}])
            got = _profile.profile(db, stage="s", model="deepseek/deepseek-v4-flash")
            self.assertFalse(got["identity"]["single_model"])
            self.assertIn("single-model-identity", got["missing"])
            self.assertFalse(got["complete"])
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_structured_model_field_does_not_become_an_identity(self):
        """DeepSeek puts an object in `model` on some messages; an identity must be comparable."""
        tmp = Path(tempfile.mkdtemp())
        try:
            db = session(tmp / "s.db", [
                {"role": "user", "model": {"name": "x", "provider": "y"}},
                {"role": "assistant", "modelID": "deepseek-v4-flash", "providerID": "deepseek"}])
            got = _profile.profile(db, stage="s", model="deepseek/deepseek-v4-flash")
            self.assertEqual(got["identity"]["observed_models"], ["deepseek-v4-flash"])
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_executor_cost_is_kept_apart_from_derived_cost(self):
        """OpenCode's own figure disagreed with the published rates; both are retained."""
        tmp = Path(tempfile.mkdtemp())
        try:
            db = session(tmp / "s.db", [
                {"role": "assistant", "modelID": "deepseek-v4-flash", "providerID": "deepseek"}])
            usage = _profile.profile(db, stage="s", model="deepseek/deepseek-v4-flash")["usage"]
            self.assertIn("executor_cost", usage)
            self.assertNotIn("cost", usage)
            derived = _pricing.cost(usage, model="deepseek-v4-flash",
                                    window=_pricing.OFF_PEAK)
            self.assertIsNotNone(derived["amount"])
            self.assertNotEqual(derived["amount"], usage["executor_cost"])
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


class ProviderGateTest(unittest.TestCase):
    """A semantic slot must not be spent discovering that the provider is unavailable."""

    maxDiff = None

    def test_a_missing_executable_is_reported_rather_than_raised(self):
        got = _provider.health("any/model", executable="definitely-not-on-path-xyz")
        self.assertEqual(got["status"], _provider.NO_EXECUTABLE)

    def test_require_refuses_to_authorise_spend_when_unavailable(self):
        got = _provider.require("any/model", executable="definitely-not-on-path-xyz")
        self.assertFalse(got["may_spend"])

    def test_the_probe_never_touches_the_experiment_fixture(self):
        source = (ROOT / "evals" / "_provider.py").read_text(encoding="utf-8")
        for token in ("objectstore", "FIXTURE", "external.md", "_mlr"):
            with self.subTest(token=token):
                self.assertNotIn(token, source)


class ModelIndexTest(unittest.TestCase):
    """Discoverability by model, without becoming a ranking."""

    maxDiff = None

    def setUp(self):
        self.text = MODELS_INDEX.read_text(encoding="utf-8")

    def test_every_link_resolves(self):
        for target in re.findall(r"\]\((?!https?:)([^)#]+)", self.text):
            with self.subTest(target=target):
                self.assertTrue((MODELS_INDEX.parent / target).exists(),
                                f"broken model-index link: {target}")

    def test_both_model_configurations_are_listed(self):
        self.assertIn("deepseek-v4-flash", self.text)
        self.assertIn("nemotron-3-ultra-free", self.text)

    def test_the_alias_and_the_documented_version_are_distinguished(self):
        """An alias that moves must not silently reinterpret older evidence."""
        self.assertIn("DeepSeek-V4-Flash-0731", self.text)
        self.assertIn("provider-observed identity", self.text)

    def test_reasoning_effort_is_part_of_the_configuration_name(self):
        self.assertRegex(self.text, r"DeepSeek V4 Flash.*effort `high`")

    def test_it_does_not_read_as_a_leaderboard(self):
        """Affirmative ranking, not the words. A disclaimer must be allowed to say them."""
        lowered = self.text.lower()
        for pattern in (r"\bbest model\b(?!.*\bnot\b)", r"\brank(?:ed|ing)?\s*[:#]?\s*\d",
                        r"\|\s*score\s*\|", r"\bwinner\s*[:=]", r"\brecommended:\s"):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, lowered),
                                  f"the index reads as a ranking: {pattern}")
        self.assertIn("not a leaderboard", lowered)
        self.assertIn("never *worse*", self.text)

    def test_it_links_rather_than_duplicating_results(self):
        """`P3`: the model view routes to records; it never restates their numbers."""
        self.assertNotIn("median", self.text.lower())
        self.assertIn("links and never duplicates", self.text)


if __name__ == "__main__":
    unittest.main()


class ModelSeparationTest(unittest.TestCase):
    """Two models are two experiments, and the substrate must make pooling them impossible."""

    maxDiff = None

    def setUp(self):
        sys.path.insert(0, str(ROOT / "evals"))
        import pb_mlr, _mlr, _repeat
        self.pb, self.mlr, self.repeat = pb_mlr, _mlr, _repeat

    def config(self, model, variant=None, arms=None, samples=5):
        return self.pb.configuration(model=model, samples=samples,
                                     arms=arms or [self.mlr.FULL], variant=variant)

    def test_the_experiment_name_carries_the_model_configuration(self):
        deepseek = self.config("deepseek/deepseek-v4-flash", "high")
        nemotron = self.config("opencode/nemotron-3-ultra-free")
        self.assertIn("deepseek-v4-flash-high", deepseek["experiment"])
        self.assertIn("nemotron", nemotron["experiment"])
        self.assertNotEqual(deepseek["experiment"], nemotron["experiment"])

    def test_reasoning_effort_makes_a_different_experiment(self):
        """V4 Flash at `high` and at `max` are different configurations, never pooled."""
        high = self.config("deepseek/deepseek-v4-flash", "high")
        mx = self.config("deepseek/deepseek-v4-flash", "max")
        self.assertNotEqual(high["experiment"], mx["experiment"])
        self.assertNotEqual(self.repeat.frozen_identity(high), self.repeat.frozen_identity(mx))

    def test_a_series_refuses_to_resume_across_a_changed_model(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            out = tmp / "series.json"
            deepseek = self.config("deepseek/deepseek-v4-flash", "high")
            self.repeat.write_series(out, deepseek, [])
            self.repeat.load_series(out, deepseek)          # same config resumes
            with self.assertRaises(self.repeat.RepeatConfigError):
                self.repeat.load_series(out, self.config("opencode/nemotron-3-ultra-free"))
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_configuration_binds_the_model_controls(self):
        got = self.config("deepseek/deepseek-v4-flash", "high")
        self.assertEqual(got["variant"], "high")
        self.assertEqual(got["thinking"], "enabled")
        self.assertEqual(got["price_id"], _pricing.DEEPSEEK_2026_09_09["id"])


class BudgetGateTest(unittest.TestCase):
    """A ceiling is checked before a slot starts, never by cutting one short."""

    maxDiff = None

    def setUp(self):
        sys.path.insert(0, str(ROOT / "evals"))
        import pb_mlr
        self.pb = pb_mlr

    def test_spend_sums_only_priced_attempts(self):
        rows = [{"cost": {"amount": 0.05}}, {"cost": {"amount": None}}, {}, {"cost": {}}]
        self.assertAlmostEqual(self.pb._spent(rows), 0.05)

    def test_a_slot_is_refused_when_the_ceiling_would_be_crossed(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            import _mlr, _mlr_run
            launched = []

            def fake(arm, **kw):
                launched.append(arm)
                return {"validity": _mlr_run.VALID, "outcome": {"correct": True},
                        "profile": {"complete": True, "stages": [{}]},
                        "cost": {"amount": 0.50}}

            original = _mlr_run.run_attempt
            _mlr_run.run_attempt = fake
            try:
                record = self.pb.run_series(tmp / "s.json", model="deepseek/deepseek-v4-flash",
                                            samples=5, arms=[_mlr.FULL], keep=None,
                                            variant="high", budget=1.0)
            finally:
                _mlr_run.run_attempt = original
            # 0.50 a run against a 1.00 ceiling with a 0.20 reserve: the third is refused.
            self.assertEqual(len(launched), 2)
            self.assertEqual(record.get("stopped"), "budget-ceiling")
            refused = [m for m in record["measurements"] if "budget ceiling" in (m.get("reason") or "")]
            self.assertTrue(refused, "the refusal must be recorded, not silent")
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_reserve_is_larger_than_the_costliest_observed_run(self):
        """A ceiling checked against an average is exceeded half the time."""
        biggest = {"input": 325_000, "cache_read": 440_000, "output": 9_000}
        worst = _pricing.cost(biggest, model="deepseek-v4-flash",
                              window=_pricing.OFF_PEAK)["amount"]
        self.assertGreaterEqual(self.pb._RESERVE, worst)

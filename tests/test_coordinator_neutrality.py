"""The workflow must not depend on which frontier host coordinates it.

Proofbound has no default frontier orchestrator. That is only true if a run can be handed from one
coordinator to another without the accepted candidate, the worker backend or the remaining
allowances changing — and if resuming needs nothing more than reading files and running a command.

Everything here uses the credential-free stand-in worker. **A stand-in establishes mechanics and
never agent quality**, so nothing in this file is evidence that any coordinator does the job well.
It is evidence that the run format does not care who is asking.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/pb_workflow.py"
sys.path.insert(0, str(ROOT / "tests"))

from test_operator_workflow import OperatorWorkflow


class CoordinatorNeutrality(OperatorWorkflow):
    """Reuses the operator fixture: same production path, same stand-in, no second harness.

    The parent's own tests are not re-collected here — inheriting the fixture should not mean
    running its suite twice, which doubled the wall time for no extra coverage.
    """

    for _inherited in [n for n in dir(OperatorWorkflow) if n.startswith("test_")]:
        locals()[_inherited] = None
    del _inherited

    def governing_facts(self):
        """What any coordinator must be able to recover from the run alone."""
        state = self.action()
        config = json.loads((self.runroot / "run-config.json").read_text())
        ledger = json.loads((self.runroot / "launch-ledger.json").read_text()) \
            if (self.runroot / "launch-ledger.json").is_file() else {"slots": []}
        admission = json.loads((self.runroot / "state.json").read_text())[
            "phases"]["build"]["tasks"].get("implementation", {}).get("admission")
        return {"action": state["action"], "task": state.get("task"), "goal": state["goal"],
                "model": config["model"], "executor": config["executor"]["sha256"],
                "ceiling": config["policy"]["launch_ceiling"],
                "slots_used": len(ledger.get("slots", [])),
                "candidate": (admission or {}).get("candidate")}

    def test_a_fresh_process_recovers_the_next_action_from_one_command(self):
        """The resume path every coordinator adapter points at, with nothing else available."""
        self.reach("consistency")
        expected = self.governing_facts()
        # A genuinely separate process, no inherited state, no hooks, no memory feature.
        cp = subprocess.run([sys.executable, str(CLI), "status", "--run", str(self.runroot)],
                            capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(cp.returncode, 0, cp.stderr)
        fresh = json.loads(cp.stdout)
        self.assertEqual(fresh["action"], expected["action"])
        self.assertEqual(fresh["task"], expected["task"])
        self.assertTrue(fresh["next"], "status must name the next command")

    def test_handing_the_run_to_another_coordinator_changes_nothing_that_governs_it(self):
        """The property that makes 'no default orchestrator' more than a slogan."""
        self.reach("consistency")
        before = self.governing_facts()

        first = self.action("coordinator", "--requested", "codex/gpt-6",
                            "--self-reported", "codex-cli 0.155.1")
        self.assertEqual(first["recorded"]["requested"], "codex/gpt-6")

        # A different capable coordinator picks the same run up.
        second = self.action("coordinator", "--requested", "claude-code/opus")
        self.assertEqual(second["coordinators_recorded"], 2)

        after = self.governing_facts()
        self.assertEqual(before, after,
                         "changing coordinator must not move candidate, backend or budget")
        self.assertTrue(second["recorded"]["worker_backend_unchanged"])

    def test_coordinator_identity_keeps_requested_self_reported_and_observed_apart(self):
        recorded = self.action("coordinator", "--requested", "claude-code/opus",
                               "--self-reported", "I am Opus")["recorded"]
        self.assertEqual(recorded["requested"], "claude-code/opus")
        self.assertEqual(recorded["self_reported"], "I am Opus")
        self.assertIsNone(recorded["observed"], "nothing may be invented for an absent field")
        self.assertIn("exposes no coordinator identity", recorded["evidence"])

    def test_the_worker_backend_is_the_configured_one_whoever_coordinates(self):
        self.action("coordinator", "--requested", "some/other-frontier-host")
        config = json.loads((self.runroot / "run-config.json").read_text())
        self.assertEqual(config["model"], "deepseek/deepseek-v4-flash")
        self.assertEqual(config["variant"], "high")

    def test_resuming_needs_only_file_access_and_one_command(self):
        """The documented host contract, checked against what the CLI actually requires."""
        self.reach("consistency")
        # No hook is installed, no adapter, no environment variable is set by us.
        env_free = subprocess.run(
            [sys.executable, str(CLI), "status", "--run", str(self.runroot)],
            capture_output=True, text=True,
            env={"PATH": "/usr/bin:/bin", "HOME": str(self.tmp)})
        self.assertEqual(env_free.returncode, 0, env_free.stderr[-400:])
        self.assertTrue(json.loads(env_free.stdout)["next"])


class CoordinatorDocumentation(unittest.TestCase):
    """Both adapters must lead to the same protocol, and neither may claim untested support."""

    def test_both_adapters_point_at_the_shared_protocol_and_front_door(self):
        for adapter in ("CLAUDE.md", "CODEX.md"):
            text = (ROOT / adapter).read_text()
            with self.subTest(adapter=adapter):
                self.assertIn("docs/coordinator-protocol.md", text)
                self.assertIn("pb_workflow.py", text)
                self.assertIn("no default frontier orchestrator", text)
                # Neither may present native frontier delegation as the normal path.
                self.assertRegex(text, r"Delegation is `continue`")

    def test_neither_adapter_requires_the_other_hosts_tooling(self):
        claude = (ROOT / "CLAUDE.md").read_text().lower()
        codex = (ROOT / "CODEX.md").read_text().lower()
        self.assertNotIn("install codex", claude)
        self.assertNotIn("install claude", codex)

    def test_the_support_matrix_does_not_claim_untested_live_support(self):
        readme = (ROOT / "README.md").read_text()
        self.assertIn("Support matrix", readme)
        row = next(l for l in readme.splitlines() if l.startswith("| Another host"))
        self.assertIn("**no**", row, "generic host support must not be claimed as live-observed")
        for coordinator in ("| Codex as coordinator", "| Claude Code/Opus as coordinator"):
            line = next(l for l in readme.splitlines() if l.startswith(coordinator))
            self.assertTrue(line.rstrip().endswith("**no** |"),
                            f"{coordinator} must not claim live observation")

    def test_adapter_commands_are_copy_pasteable(self):
        """A fresh reader could not run them: `<skill>` was defined nowhere, and `--change` was
        missing from the only `start` line those files showed."""
        for adapter in ("CLAUDE.md", "CODEX.md"):
            text = (ROOT / adapter).read_text()
            with self.subTest(adapter=adapter):
                self.assertNotIn("<skill>", text, "undefined placeholder in a command block")
                start = next(l for l in text.splitlines()
                             if "pb_workflow.py" in l and " start " in l)
                self.assertIn("--change", start, "`start` without --change does not match any other doc")
                self.assertIn("PB=", text, "the command block must define what $PB is")

    def test_no_copyable_example_carries_the_escaped_path(self):
        for doc in list(ROOT.glob("*.md")) + list((ROOT / "docs").rglob("*.md")):
            with self.subTest(doc=doc.name):
                self.assertNotIn("pb_workflow\\.py", doc.read_text())


if __name__ == "__main__":
    unittest.main()

"""The documented public commands, driven through the actual constructed runtime.

`_live.rehearse` calls the same machinery in-process and proves that the machinery works. It does
not prove that the **commands a coordinator is told to run** work: at the inspected revision the
successor protocol passed `--workdir` to three commands that take `--into`, `--root` and `--root`,
and every one of them failed to parse. A protocol whose first three lines do not run is not a
frozen protocol.

So this drives the CLI surface a fresh coordinator actually receives — `build-runtime`,
`probe-runtime`, `live-input`, `place-contract`, `launch`, `check-artifact`, plus the shipped
`pb_execution admit`, `dsd_attempt gate` and `dsd_state accept-task` — against the credential-free
fake executor inside the real `sandbox-exec` boundary, and then collects and verifies the evidence.

macOS only: the constructed runtime is built with `sandbox-exec`. The test skips elsewhere rather
than pretending to have measured a boundary it never built.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLICE = ROOT / "evals" / "authority_slice"
SCRIPTS = ROOT / "scripts"
PYTHON = sys.executable
sys.path.insert(0, str(SLICE))
sys.path.insert(0, str(ROOT / "evals"))

import _package                                                      # noqa: E402


def sh(argv: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(a) for a in argv], text=True, capture_output=True, check=False, **kw)


def payload(done: subprocess.CompletedProcess) -> dict:
    if done.returncode != 0 and not done.stdout.strip().startswith("{"):
        raise AssertionError(f"command failed ({done.returncode}): {done.stderr.strip()[-600:]}")
    return json.loads(done.stdout)


@unittest.skipUnless(sys.platform == "darwin", "the constructed runtime needs macOS sandbox-exec")
class DocumentedLivePathTest(unittest.TestCase):
    """One condition, end to end, through the commands the protocol names."""

    EXPERIMENT = "pb-handoff-2"

    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = Path(tempfile.mkdtemp(prefix="pb-livepath-"))
        cls.root = cls.parent / "rt"
        built = payload(sh([PYTHON, SLICE / "pb_slice.py", "build-runtime",
                            "--root", cls.root, "--mode", "rehearsal",
                            "--experiment", cls.EXPERIMENT]))
        cls.built = built
        # Every path comes from the builder's own record. Preparing a second workspace by hand is
        # how a run ends up collecting evidence from a tree the coordinator never touched.
        cls.workdir = Path(built["workdir"])
        cls.harness = Path(built["harness_root"])
        cls.wrapper = Path(built["wrapper"])
        cls.config = json.loads((cls.workdir / "run-config.json").read_text())
        cls.paths = cls.config["paths"]
        cls.identities = json.loads(Path(cls.config["identities"]).read_text())

    @classmethod
    def tearDownClass(cls) -> None:
        for path in (cls.root, Path(f"{cls.root}-tools"), Path(f"{cls.root}-run"),
                     Path(f"{cls.root}.identities.json"), cls.parent):
            shutil.rmtree(path, ignore_errors=True) if path.is_dir() else path.unlink(
                missing_ok=True)

    # -- identity ------------------------------------------------------------------------------
    def test_one_experiment_identity_across_every_artifact(self):
        """Configuration, ledger and runtime record must agree, without a caller retyping it."""
        self.assertEqual(self.config["experiment"], self.EXPERIMENT)
        self.assertEqual(self.built["experiment"], self.EXPERIMENT)
        self.assertEqual(self.identities["experiment"], self.EXPERIMENT)
        ledger = json.loads((self.workdir / "launch-ledger.json").read_text())
        self.assertEqual(ledger["experiment"], self.EXPERIMENT)

    def test_the_protocol_and_coordinator_input_are_digested_before_execution(self):
        protocol = self.identities["protocol"]
        self.assertEqual(protocol["document"], "pb-handoff-2-protocol.md")
        self.assertEqual(protocol["sha256"],
                         _package.sha256_file(SLICE / "pb-handoff-2-protocol.md"),
                         "the frozen digest must match the document in the checkout")

        rendered = sh([PYTHON, SLICE / "pb_slice.py", "live-input", "--workdir", self.workdir,
                       "--harness", self.harness, "--wrapper", self.wrapper])
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        recorded = json.loads(Path(self.config["identities"]).read_text())
        self.assertEqual(recorded["coordinator_input_sha256"],
                         _package.sha256_file(self.workdir / "coordinator-input.md"))

    def test_the_documented_commands_parse(self):
        """The three that did not, at the inspected revision."""
        for argv in ([SLICE / "pb_slice.py", "build-runtime", "--help"],
                     [SLICE / "pb_slice.py", "probe-runtime", "--root", self.root],
                     [SLICE / "pb_slice.py", "live-input", "--workdir", self.workdir]):
            with self.subTest(command=str(argv[1])):
                done = sh([PYTHON, *argv])
                self.assertEqual(done.returncode, 0, done.stderr[-400:])

    def test_the_boundary_holds_and_the_experiment_plan_is_withheld(self):
        probe = payload(sh([PYTHON, SLICE / "pb_slice.py", "probe-runtime", "--root", self.root]))
        self.assertTrue(probe["boundary_holds"], probe)
        for withheld in ("experiment_plan_readable", "answer_key_readable",
                         "checker_corpus_readable"):
            with self.subTest(file=withheld):
                self.assertIn("cat:", probe["checks"][withheld]["stdout"],
                              "evaluator material must not be readable from inside")
        self.assertIn("pb-handoff-2-protocol.md", _import_runtime().WITHHELD,
                      "the successor's own plan must be withheld like its predecessor's")


def _import_runtime():
    import _runtime
    return _runtime


@unittest.skipUnless(sys.platform == "darwin", "the constructed runtime needs macOS sandbox-exec")
class ValidConditionThroughPublicCommandsTest(unittest.TestCase):
    """Recover, admit, implement, review, check, accept — then collect and relocate.

    This is the valid condition's shape, run with the fake executor. It is not a qualification: no
    fresh coordinator decided anything here, and every semantic judgment is the harness's.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = Path(tempfile.mkdtemp(prefix="pb-validpath-"))
        cls.root = cls.parent / "rt"
        cls.built = payload(sh([PYTHON, SLICE / "pb_slice.py", "build-runtime",
                                "--root", cls.root, "--mode", "rehearsal",
                                "--experiment", "pb-handoff-2"]))
        cls.workdir = Path(cls.built["workdir"])
        cls.config = json.loads((cls.workdir / "run-config.json").read_text())
        cls.paths = cls.config["paths"]
        cls.candidate = json.loads(
            Path(cls.config["identities"]).read_text())["seeded_candidate"]
        cls.steps = cls._drive()

    @classmethod
    def tearDownClass(cls) -> None:
        for path in (cls.root, Path(f"{cls.root}-tools"), Path(f"{cls.root}-run"),
                     Path(f"{cls.root}.identities.json"), cls.parent):
            shutil.rmtree(path, ignore_errors=True) if path.is_dir() else path.unlink(
                missing_ok=True)

    @classmethod
    def _attempt_dir(cls) -> Path:
        state = json.loads((Path(cls.paths["run_root"]) / "state.json").read_text())
        return Path(state["phases"]["build"]["tasks"]["RQ-impl"]["current_attempt"]["event_dir"])

    @classmethod
    def _drive(cls) -> dict:
        p, out = cls.paths, {}
        contract = payload(sh([PYTHON, SLICE / "pb_slice.py", "place-contract",
                               "--workdir", cls.workdir, "--task", "RQ-impl",
                               "--candidate", cls.candidate]))["contract"]
        out["admit"] = payload(sh([
            PYTHON, SCRIPTS / "pb_execution.py", "admit", "--run-root", p["run_root"],
            "--phase-id", "build", "--task-id", "RQ-impl", "--contract", contract,
            "--graph", p["graph"], "--ledger", p["ledger"], "--project-root", p["project"],
            "--consistency", p["consistency"]]))
        out["implementer"] = payload(sh([PYTHON, SLICE / "pb_slice.py", "launch",
                                         "--workdir", cls.workdir, "--phase", "build",
                                         "--task", "RQ-impl", "--role", "implementer"]))
        sh([PYTHON, SCRIPTS / "dsd_attempt.py", "gate", "--run-root", p["run_root"],
            "--phase-id", "build", "--task-id", "RQ-impl"])
        report = cls._attempt_dir() / "report.md"
        out["reviewer"] = payload(sh([PYTHON, SLICE / "pb_slice.py", "launch",
                                      "--workdir", cls.workdir, "--phase", "build",
                                      "--task", "RQ-impl", "--role", "reviewer",
                                      "--input", report]))
        sh([PYTHON, SCRIPTS / "dsd_attempt.py", "gate", "--run-root", p["run_root"],
            "--phase-id", "build", "--task-id", "RQ-impl"])
        out["check"] = payload(sh([PYTHON, SLICE / "pb_slice.py", "check-artifact",
                                   "--workdir", cls.workdir]))
        gate = cls._attempt_dir() / "evidence-gate.json"
        out["accept"] = payload(sh([PYTHON, SCRIPTS / "dsd_state.py", "accept-task",
                                    "--run-root", p["run_root"], "--phase-id", "build",
                                    "--task-id", "RQ-impl", "--evidence-gate", gate]))
        import _live
        out["final"] = _live.finalize(cls.workdir, condition="valid",
                                      into=cls.parent / "package")
        return out

    def test_the_workflow_completes_through_the_documented_commands(self):
        self.assertTrue(self.steps["admit"]["admitted"])
        self.assertEqual(self.steps["admit"]["provenance"], "verified")
        self.assertEqual(self.steps["implementer"]["slot"]["classification"], "executor-reached")
        self.assertEqual(self.steps["reviewer"]["slot"]["classification"], "executor-reached")
        self.assertEqual(self.steps["check"]["verdict"], "pass")
        self.assertEqual(self.steps["accept"]["status"], "accepted")

    def test_the_artifact_check_record_carries_the_runs_own_identity(self):
        self.assertEqual(self.steps["check"]["experiment"], "pb-handoff-2")

    def test_finalization_collects_without_being_told_which_attempts_were_its_own(self):
        final = self.steps["final"]
        self.assertEqual(final["disposition"], "completed")
        self.assertEqual(sorted(final["own_attempts"]), ["implementer-1", "reviewer-1"],
                         "the owned set comes from the ledger, not from a caller's list")
        self.assertTrue(final["evidence"]["preserved"], final["evidence"])
        self.assertTrue(final["safe_to_clean_up"])

    def test_the_package_carries_its_identities_and_ledger(self):
        manifest = json.loads(
            (Path(self.steps["final"]["evidence"]["package"]) / "manifest.json").read_text())
        roles = {f["role"] for f in manifest["files"]}
        for required in ("authority-state", "launch-ledger", "run-configuration",
                         "frozen-identities"):
            with self.subTest(role=required):
                self.assertIn(required, roles,
                              "collection must reach the workdir, where preparation writes these")

    def test_no_credential_reaches_the_package(self):
        package = Path(self.steps["final"]["evidence"]["package"])
        for path in package.rglob("*"):
            if path.is_file():
                self.assertNotIn("auth.json", path.name)
                self.assertNotIn(".local/share/opencode", path.as_posix())

    def test_the_package_verifies_after_the_runtime_is_gone(self):
        """The criterion: relocate, destroy the original, and check what survives."""
        relocated = self.parent / "relocated"
        shutil.copytree(self.steps["final"]["evidence"]["package"], relocated)
        shutil.rmtree(self.workdir, ignore_errors=True)
        self.assertFalse(self.workdir.exists())

        report = _package.verify(relocated, recheck_artifact=True, timeout=10)
        self.assertIsNone(report["counts"].get(_package.MISMATCH), report["counts"])
        for required in ("files.integrity", "launch.attempts", "launch.ledger-agreement",
                         "usage.recompute", "usage.completeness", "price.recompute",
                         "usage.attribution", "authority.binding", "authority.admission",
                         "artifact.retained", "artifact.recheck"):
            entry = next(c for c in report["checks"] if c["id"] == required)
            with self.subTest(check=required):
                self.assertEqual(entry["status"], _package.OK, entry["detail"])

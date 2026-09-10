"""The real modularity worker, run inside the constructed evidence surface.

R4-A proved the substrate with local commands. This proves the integration: the actual prepared arm,
the actual compiled dependency, the actual inherited launcher, the actual executor binary and the
ordinary subprocess tree beneath them, all inside one boundary — and the resulting workspace and
session still consumable by the oracle, the attribution ledger and the profile without changing any
of them.

Nothing here calls a model. The one layer that cannot be reached without buying a semantic sample —
a model-driven tool call issued by the executor — is left to the field qualification, and is named
rather than assumed.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

import _hermetic        # noqa: E402
import _mlr             # noqa: E402
import _mlr_boundary    # noqa: E402
import _mlr_context     # noqa: E402
import _mlr_run         # noqa: E402
import _profile         # noqa: E402
import _semantic_view   # noqa: E402

FIXTURE = _mlr.FIXTURE
EXECUTOR = Path("/Users/thiago/.nvm/versions/node/v22.13.1/bin/opencode")

macos_only = unittest.skipUnless(
    sys.platform == "darwin" and Path(_semantic_view.SANDBOX).exists(),
    "the macOS sandbox mechanism is not available on this platform")


def apply_candidate(candidate: Path, workspace: Path) -> None:
    """Put a deterministic solution into a workspace, control-side, as the oracle fixture."""
    for source in candidate.rglob("*.py"):
        target = workspace / source.relative_to(candidate)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


@macos_only
class StagingTest(unittest.TestCase):
    """The real arm enters the view, and the treatment survives the journey."""

    maxDiff = None

    def staged(self, arm):
        view_context = _semantic_view.semantic_view(_mlr_boundary.policy(network=False))
        view = view_context.__enter__()
        self.addCleanup(view_context.__exit__, None, None, None)
        return view, _mlr_boundary.stage(view, arm, model="provider/model")

    def test_the_full_arm_carries_its_source_and_the_contract_arm_does_not(self):
        view, _ = self.staged(_mlr.FULL)
        self.assertTrue((view.workspace / _mlr.VENDORED / "objectstore" / "_store.py").is_file())
        other, _ = self.staged(_mlr.CONTRACT)
        self.assertFalse((other.workspace / _mlr.VENDORED).exists())

    def test_both_arms_receive_the_same_compiled_dependency(self):
        first, one = self.staged(_mlr.FULL)
        second, two = self.staged(_mlr.CONTRACT)
        self.assertEqual(one["built"]["runtime_structure"], two["built"]["runtime_structure"])
        self.assertEqual(one["built"]["contract_sha256"], two["built"]["contract_sha256"])
        self.assertEqual(sorted(p.name for p in first.runtime.rglob("*.pyc")),
                         sorted(p.name for p in second.runtime.rglob("*.pyc")))

    def test_the_staged_runtime_carries_no_source_in_either_arm(self):
        for arm in (_mlr.FULL, _mlr.CONTRACT):
            with self.subTest(arm=arm):
                view, _ = self.staged(arm)
                self.assertEqual(list(view.runtime.rglob("*.py")), [])

    def test_the_view_path_does_not_name_the_arm(self):
        """§10. Nothing in a path the model can read should say which side of the treatment it is."""
        for arm in (_mlr.FULL, _mlr.CONTRACT):
            with self.subTest(arm=arm):
                view, staged = self.staged(arm)
                for path in (view.root, view.home, view.tmp, view.session, staged["db"]):
                    self.assertNotIn(arm, str(path).lower())

    def test_the_staged_harness_carries_no_controlled_evidence(self):
        """The launcher is orchestration and is staged as a declared input, having been checked."""
        self.assertEqual(_mlr_boundary.harness_is_clean()["status"], _hermetic.CLEAN)
        view, staged = self.staged(_mlr.CONTRACT)
        report = _hermetic.scan([staged["harness"]], _mlr_boundary.sensitive())
        self.assertEqual(report["status"], _hermetic.CLEAN)

    def test_the_workspace_matches_what_the_legacy_path_prepares(self):
        """§74. Same task, same tests, same contract; only the location differs."""
        holder = Path(tempfile.mkdtemp(prefix="pb-legacy-"))
        try:
            legacy = _mlr.materialise(_mlr.CONTRACT, holder / "arm")
            legacy_tree = {p.relative_to(legacy["workspace"]).as_posix(): _mlr.digest_file(p)
                           for p in Path(legacy["workspace"]).rglob("*")
                           if p.is_file() and ".git" not in p.parts}
        finally:
            shutil.rmtree(holder, ignore_errors=True)
        view, _ = self.staged(_mlr.CONTRACT)
        staged_tree = {p.relative_to(view.workspace).as_posix(): _mlr.digest_file(p)
                       for p in view.workspace.rglob("*")
                       if p.is_file() and ".git" not in p.parts
                       and "DeepSeekAndDestroy" not in p.parts and p.name != "PLAN.md"}
        for name, digest in legacy_tree.items():
            if "DeepSeekAndDestroy" in name or name == "PLAN.md":
                continue
            with self.subTest(path=name):
                self.assertEqual(staged_tree.get(name), digest)


@macos_only
class PreflightTest(unittest.TestCase):
    """The slot's evidence surface, validated before anything is launched."""

    maxDiff = None

    def test_the_contract_arm_is_clean_and_declares_nothing(self):
        with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
            _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
            report = _mlr_boundary.preflight(view, _mlr.CONTRACT)
            self.assertEqual(report["status"], _hermetic.CLEAN)
            self.assertEqual(report["declared"], [])

    def test_the_full_arm_declares_exactly_its_own_source(self):
        with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
            _mlr_boundary.stage(view, _mlr.FULL, model="provider/model")
            report = _mlr_boundary.preflight(view, _mlr.FULL)
            self.assertEqual(report["status"], _hermetic.CLEAN)
            self.assertEqual(len(report["declared_exposures"]),
                             len(list((FIXTURE / "runtime" / "objectstore").glob("*.py"))))

    def test_a_second_undeclared_copy_contaminates_either_arm(self):
        """§36, §60. A declared exposure covers one place and not a second."""
        for arm in (_mlr.FULL, _mlr.CONTRACT):
            for area in ("home", "tmp", "session"):
                with self.subTest(arm=arm, area=area):
                    with _semantic_view.semantic_view(
                            _mlr_boundary.policy(network=False)) as view:
                        _mlr_boundary.stage(view, arm, model="provider/model")
                        shutil.copy(FIXTURE / "runtime" / "objectstore" / "_store.py",
                                    getattr(view, area) / "_store.py")
                        report = _mlr_boundary.preflight(view, arm)
                        self.assertEqual(report["status"], _hermetic.CONTAMINATED)

    def test_a_copy_outside_the_view_does_not_contaminate_it(self):
        """§59. The failure mode that invalidated a paired run, now irrelevant by construction."""
        stale = Path(tempfile.mkdtemp(prefix="pb-stale-full-"))
        try:
            (stale / "workspace" / "third_party" / "objectstore").mkdir(parents=True)
            shutil.copy(FIXTURE / "runtime" / "objectstore" / "_store.py",
                        stale / "workspace" / "third_party" / "objectstore" / "_store.py")
            with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
                _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
                self.assertEqual(_mlr_boundary.preflight(view, _mlr.CONTRACT)["status"],
                                 _hermetic.CLEAN)
                denied = view.shell(
                    f"/bin/cat {stale}/workspace/third_party/objectstore/_store.py 2>&1")
                self.assertIn("not permitted", denied.stdout + denied.stderr)
        finally:
            shutil.rmtree(stale, ignore_errors=True)

    def test_nothing_is_launched_when_the_preflight_is_not_clean(self):
        """§61. An ordering invariant in control flow, not a flag stored on the view."""
        with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
            staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
            shutil.copy(FIXTURE / "runtime" / "objectstore" / "_store.py",
                        view.tmp / "_store.py")
            report = _mlr_boundary.preflight(view, _mlr.CONTRACT)
            with self.assertRaises(_mlr_boundary.PreflightRefused):
                _mlr_boundary.launch(view, staged, variant=None, cleared=report)


@macos_only
class ProcessTreeTest(unittest.TestCase):
    """One boundary, entered once, inherited by everything beneath it."""

    maxDiff = None

    PROBE = (
        "import json, os, subprocess, tempfile\n"
        "child = {'sentinel': os.environ.get('PROOFBOUND_HOST_SENTINEL', 'absent'),\n"
        "         'home': os.environ.get('HOME'), 'tmp': tempfile.gettempdir()}\n"
        "grand = subprocess.run(['/bin/sh', '-c', SCRIPT], capture_output=True, text=True)\n"
        "child['grandchild'] = grand.stdout\n"
        "print(json.dumps(child))\n"
    )

    def probe(self, view, staged, script):
        source = view.root / _mlr_boundary.HARNESS_AREA / "_probe.py"
        source.write_text("SCRIPT = %r\n" % script + self.PROBE, encoding="utf-8")
        done = view.run([str(staged["binaries"] / "python3"), str(source)],
                        env=_mlr_boundary.environment(view, staged), timeout=300)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def test_a_host_sentinel_does_not_reach_the_deepest_child(self):
        """§83. Stronger than the substrate's direct-child test: two levels down the real chain."""
        os.environ["PROOFBOUND_HOST_SENTINEL"] = "should-not-cross"
        try:
            with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
                staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
                seen = self.probe(view, staged,
                                  'echo SENTINEL=${PROOFBOUND_HOST_SENTINEL:-absent}')
                self.assertEqual(seen["sentinel"], "absent")
                self.assertIn("SENTINEL=absent", seen["grandchild"])
        finally:
            os.environ.pop("PROOFBOUND_HOST_SENTINEL", None)

    def test_the_deepest_child_sees_the_constructed_home_and_scratch(self):
        with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
            staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
            seen = self.probe(view, staged, 'echo HOME=$HOME; echo TMP=$TMPDIR')
            self.assertEqual(seen["home"], str(view.home))
            self.assertEqual(seen["tmp"], str(view.tmp))
            self.assertIn(f"HOME={view.home}", seen["grandchild"])
            self.assertIn(f"TMP={view.tmp}", seen["grandchild"])

    def test_the_deepest_child_cannot_read_the_control_plane(self):
        """§92. Knowing the exact path does not help."""
        with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
            staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
            seen = self.probe(view, staged,
                              f'/bin/cat {ROOT}/README.md 2>&1 | /usr/bin/head -1; '
                              f'/bin/ls {Path.home()} 2>&1 | /usr/bin/head -1; '
                              f'/bin/cat {FIXTURE}/hidden/external_test_v2.py 2>&1 '
                              f'| /usr/bin/head -1')
            self.assertEqual(seen["grandchild"].count("Operation not permitted"), 3,
                             seen["grandchild"])

    def test_the_historical_search_from_the_deepest_child_finds_only_the_slot(self):
        """§86. The exact command that defeated the treatment, two levels into the real chain."""
        with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
            staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
            seen = self.probe(
                view, staged,
                '/usr/bin/find / -maxdepth 8 -name "objectstore*" '
                '-not -path "*/.git/*" 2>/dev/null')
            hits = [line for line in seen["grandchild"].splitlines() if line.strip()]
            self.assertTrue(hits)
            for hit in hits:
                with self.subTest(hit=hit):
                    self.assertIn(str(view.root).lstrip("/"), hit)


@macos_only
class ExecutorTest(unittest.TestCase):
    """The real executor, in the view, on a home it has never seen before."""

    maxDiff = None

    @unittest.skipUnless(EXECUTOR.is_file(), "the executor is not installed on this machine")
    def test_the_executor_runs_inside_the_view(self):
        with _semantic_view.semantic_view(_mlr_boundary.policy(executor=EXECUTOR)) as view:
            staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
            done = view.run([str(view.tools_root / "opencode"), "--version"],
                            env=_mlr_boundary.environment(view, staged), timeout=300)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertTrue(done.stdout.strip())

    @unittest.skipUnless(EXECUTOR.is_file(), "the executor is not installed on this machine")
    def test_the_executor_builds_its_state_inside_the_constructed_home(self):
        """§19, §63, §64. No fallback to the store the evaluator has been using all along."""
        with _semantic_view.semantic_view(_mlr_boundary.policy(executor=EXECUTOR)) as view:
            staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
            before = set(view.root.rglob("*"))
            view.run([str(view.tools_root / "opencode"), "--version"],
                     env=_mlr_boundary.environment(view, staged), timeout=300)
            created = {p for p in set(view.root.rglob("*")) - before}
            self.assertTrue(created, "the executor created no state at all")
            for path in created:
                with self.subTest(path=str(path)):
                    self.assertTrue(str(path).startswith(str(view.root)))
            denied = view.shell(
                f"/bin/ls {Path.home() / '.local' / 'share' / 'opencode'} 2>&1")
            self.assertIn("not permitted", denied.stdout + denied.stderr)

    @unittest.skipUnless(EXECUTOR.is_file(), "the executor is not installed on this machine")
    def test_the_executor_sees_no_prior_session_and_no_host_configuration(self):
        """§66, §67. A frozen executor, not the evaluator's interactive environment."""
        with _semantic_view.semantic_view(_mlr_boundary.policy(executor=EXECUTOR)) as view:
            staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
            env = _mlr_boundary.environment(view, staged)
            executor = str(view.tools_root / "opencode")
            sessions = view.run([executor, "session", "list"], env=env, timeout=300)
            self.assertEqual(sessions.returncode, 0, sessions.stderr)
            self.assertEqual(sessions.stdout.strip(), "")
            servers = view.run([executor, "mcp", "list"], env=env, timeout=300)
            self.assertIn("No MCP servers configured", servers.stdout + servers.stderr)
            providers = view.run([executor, "providers", "list"], env=env, timeout=300)
            blob = providers.stdout + providers.stderr
            self.assertIn("0 credentials", blob)
            self.assertNotIn(str(Path.home() / ".local"), blob)

    @unittest.skipUnless(EXECUTOR.is_file(), "the executor is not installed on this machine")
    def test_the_executor_creates_its_session_store_inside_the_slot(self):
        """§21. The deepest model-free layer: the store the ledger will later be read from."""
        with _semantic_view.semantic_view(_mlr_boundary.policy(executor=EXECUTOR)) as view:
            staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
            self.assertFalse(staged["db"].exists())
            view.run([str(view.tools_root / "opencode"), "models"],
                     env=_mlr_boundary.environment(view, staged), timeout=300)
            self.assertTrue(staged["db"].is_file())
            self.assertTrue(str(staged["db"]).startswith(str(view.session)))

    @unittest.skipUnless(EXECUTOR.is_file(), "the executor is not installed on this machine")
    def test_the_executor_is_identified_by_its_bytes(self):
        identity = _mlr_boundary.executor_identity(EXECUTOR)
        self.assertEqual(identity["sha256"], _mlr.digest_file(EXECUTOR))
        self.assertNotIn("auth", json.dumps(identity))


@macos_only
class EquivalenceTest(unittest.TestCase):
    """The task the worker meets, and the judgement it meets afterwards, are unchanged."""

    maxDiff = None

    def test_the_visible_tests_pass_inside_the_boundary(self):
        with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
            staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
            done = view.run([str(staged["binaries"] / "python3"), "-m", "unittest",
                             "discover", "-s", "tests", "-t", "."],
                            cwd=view.workspace,
                            env=_mlr_boundary.environment(view, staged), timeout=300)
            self.assertEqual(done.returncode, 0, done.stderr[-400:])

    def test_the_oracle_decides_the_same_way_after_a_round_trip(self):
        """§77-§79. Known-valid and known-invalid candidates, graded both ways."""
        candidates = [("reference", FIXTURE / "reference" / "external", True)]
        for name in ("handler", "optional"):
            candidates.append((name, FIXTURE / "realizations" / "valid" / name, True))
        for name in ("always-created", "missing-as-empty"):
            candidates.append((name, FIXTURE / "realizations" / "invalid" / name, False))
        for label, candidate, expected in candidates:
            with self.subTest(candidate=label):
                self.assertEqual(self.grade_legacy(candidate), expected)
                self.assertEqual(self.grade_through_boundary(candidate), expected)

    def grade_legacy(self, candidate):
        holder = Path(tempfile.mkdtemp(prefix="pb-legacy-"))
        try:
            built = _mlr.materialise(_mlr.CONTRACT, holder / "arm")
            apply_candidate(candidate, Path(built["workspace"]))
            return _mlr_run.grade(built, holder)["correct"]
        finally:
            shutil.rmtree(holder, ignore_errors=True)

    def grade_through_boundary(self, candidate):
        out = Path(tempfile.mkdtemp(prefix="pb-out-"))
        graded = Path(tempfile.mkdtemp(prefix="pb-grade-"))
        try:
            with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
                staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
                apply_candidate(candidate, view.workspace)
                collected = _mlr_boundary.extract(view, out, staged)
            built = _mlr.materialise(_mlr.CONTRACT, graded / "arm")
            shutil.rmtree(built["workspace"])
            shutil.copytree(Path(collected["workspace"]), built["workspace"])
            return _mlr_run.grade(built, graded)["correct"]
        finally:
            shutil.rmtree(out, ignore_errors=True)
            shutil.rmtree(graded, ignore_errors=True)


@macos_only
class RoundTripTest(unittest.TestCase):
    """What comes back is what the unchanged analysis machinery already knows how to read."""

    maxDiff = None

    ARCHIVE = Path(os.path.expanduser(
        "~/proofbound-evidence/mlr-deepseek-v4-flash-high-paired"))

    def retained_session(self):
        found = sorted(self.ARCHIVE.glob("contract-*/worker.db")) if self.ARCHIVE.is_dir() else []
        if not found:
            self.skipTest("no retained session is available on this machine")
        return found[0]

    def test_a_session_survives_extraction_and_destruction(self):
        """The database is placed rather than produced here; a model would be needed to produce one."""
        session = self.retained_session()
        out = Path(tempfile.mkdtemp(prefix="pb-out-"))
        try:
            with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
                staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
                shutil.copyfile(session, staged["db"])
                collected = _mlr_boundary.extract(view, out, staged)
                root = view.root
            self.assertFalse(root.exists())
            extracted = Path(collected["session"])
            self.assertTrue(extracted.is_file())

            built = {"workspace": str(out / "workspace"), "runtime": str(out / "runtime"),
                     "arm": _mlr.CONTRACT}
            ledger = _mlr_context.consumed(extracted, built)
            self.assertGreater(ledger["model_calls"], 0)
            self.assertGreater(len(ledger["items"]), 0)
            self.assertEqual(ledger["uncovered_events"], [])

            profile = _profile.profile(extracted, stage=_mlr_run.ROLE, model="provider/model",
                                       variant="high", elapsed_seconds=1.0,
                                       verification_seconds=0.1)
            self.assertTrue(profile["complete"])
            self.assertGreater(profile["usage"]["calls_finished"], 0)
        finally:
            shutil.rmtree(out, ignore_errors=True)

    def test_the_extraction_destination_is_unreachable_from_inside(self):
        out = Path(tempfile.mkdtemp(prefix="pb-out-"))
        try:
            (out / "control-plane.txt").write_text("evaluator only\n", encoding="utf-8")
            with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
                _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
                done = view.shell(f"/bin/cat {out / 'control-plane.txt'} 2>&1")
                self.assertNotIn("evaluator only", done.stdout)
        finally:
            shutil.rmtree(out, ignore_errors=True)


@macos_only
class SequentialAttemptTest(unittest.TestCase):
    """Two integrated slots in a row, including the arm transition that broke the treatment."""

    maxDiff = None

    MARKER = "PB-R4B-MARKER"

    def sow(self, view, staged):
        for area in ("workspace", "home", "tmp", "session", "data"):
            (getattr(view, area) / f"{self.MARKER}.txt").write_text(self.MARKER, encoding="utf-8")
        view.shell(f"echo {self.MARKER} > $TMPDIR/from-a-shell.txt",
                   env=_mlr_boundary.environment(view, staged))

    def reap(self, view, staged):
        done = view.run(
            ["/bin/sh", "-c",
             f"/usr/bin/find / -maxdepth 8 -name '{self.MARKER}*' 2>/dev/null; "
             f"/usr/bin/grep -rl '{self.MARKER}' /private/tmp 2>/dev/null | /usr/bin/head -5"],
            env=_mlr_boundary.environment(view, staged), timeout=300)
        return done.stdout.strip()

    def run_pair(self, first_arm, second_arm):
        with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
            staged = _mlr_boundary.stage(view, first_arm, model="provider/model")
            self.sow(view, staged)
            first_root = view.root
        self.assertFalse(first_root.exists())
        with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
            staged = _mlr_boundary.stage(view, second_arm, model="provider/model")
            self.assertNotEqual(view.root, first_root)
            self.assertEqual(self.reap(view, staged), "")
            self.assertEqual(_mlr_boundary.preflight(view, second_arm)["status"],
                             _hermetic.CLEAN)
            source = view.run(
                ["/bin/sh", "-c",
                 '/usr/bin/find / -maxdepth 8 -name "_store.py" 2>/dev/null'],
                env=_mlr_boundary.environment(view, staged), timeout=300).stdout
            return [line for line in source.splitlines() if line.strip()], view.root

    def test_a_contract_slot_after_a_full_slot_finds_no_source(self):
        """§57. The historical failure, as a deterministic regression."""
        hits, root = self.run_pair(_mlr.FULL, _mlr.CONTRACT)
        self.assertEqual(hits, [], hits)

    def test_a_full_slot_after_a_contract_slot_exposes_only_its_own_source(self):
        """§58. Protection against integration code that remembers the last arm."""
        hits, root = self.run_pair(_mlr.CONTRACT, _mlr.FULL)
        self.assertTrue(hits)
        for hit in hits:
            with self.subTest(hit=hit):
                self.assertIn(str(root).lstrip("/"), hit)
                self.assertIn(_mlr.VENDORED.as_posix(), hit)


@macos_only
class IntegrationCleanupTest(unittest.TestCase):
    """A failure at any integration stage still destroys the slot. §53."""

    maxDiff = None

    def test_a_failure_after_staging_destroys_the_view(self):
        seen = {}
        with self.assertRaises(RuntimeError):
            with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
                _mlr_boundary.stage(view, _mlr.FULL, model="provider/model")
                seen["root"] = view.root
                raise RuntimeError("staging succeeded and the next stage failed")
        self.assertFalse(seen["root"].exists())

    def test_a_refused_preflight_destroys_the_view(self):
        seen = {}
        with self.assertRaises(_mlr_boundary.PreflightRefused):
            with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
                staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
                seen["root"] = view.root
                shutil.copy(FIXTURE / "runtime" / "objectstore" / "_store.py",
                            view.home / "_store.py")
                _mlr_boundary.launch(view, staged, variant=None,
                                     cleared=_mlr_boundary.preflight(view, _mlr.CONTRACT))
        self.assertFalse(seen["root"].exists())

    def test_staged_credentials_disappear_with_the_view(self):
        """§54. Staged with a fixture, never a real one."""
        holder = Path(tempfile.mkdtemp(prefix="pb-cred-"))
        try:
            dummy = holder / "auth.json"
            dummy.write_text('{"note": "not a credential"}\n', encoding="utf-8")
            with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
                _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model",
                                    home_files={".local/share/opencode/auth.json": dummy})
                staged_copy = view.home / ".local" / "share" / "opencode" / "auth.json"
                self.assertTrue(staged_copy.is_file())
                root = view.root
            self.assertFalse(root.exists())
            self.assertFalse(staged_copy.exists())
            self.assertTrue(dummy.is_file())
        finally:
            shutil.rmtree(holder, ignore_errors=True)


class EnvironmentPolicyTest(unittest.TestCase):
    """What the worker is given, and what it is not. §11, §13, §14."""

    maxDiff = None

    def test_no_layer_of_the_integration_copies_the_host_environment(self):
        for module in ("_mlr_boundary.py", "_semantic_view.py"):
            with self.subTest(module=module):
                text = (ROOT / "evals" / module).read_text(encoding="utf-8")
                self.assertNotIn("os.environ.copy()", text)

    def test_no_declared_variable_points_at_the_control_plane(self):
        with _semantic_view.semantic_view(_mlr_boundary.policy(network=False)) as view:
            staged = _mlr_boundary.stage(view, _mlr.CONTRACT, model="provider/model")
            env = view.environment(_mlr_boundary.environment(view, staged))
            self.assertEqual(set(env), {"PATH", "HOME", "TMPDIR", "PYTHONPATH",
                                        "OBJECTSTORE_ROOT", "OPENCODE_DB", "DSD_OC_RUN_DB"})
            for name, value in env.items():
                with self.subTest(variable=name):
                    self.assertNotIn(str(ROOT), value)
                    self.assertNotIn(str(Path.home() / "proofbound-evidence"), value)
                    if name != "PATH":
                        self.assertTrue(value.startswith(str(view.root)), value)


if __name__ == "__main__":                                  # pragma: no cover
    unittest.main()

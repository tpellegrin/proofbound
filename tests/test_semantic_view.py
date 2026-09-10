"""A per-slot execution environment built from declared inputs, and what it does not contain.

The measurement that motivated this: an arm whose prepared workspace deliberately contained no
implementation source ran one host-wide search, found a copy left by an earlier materialisation, and
read it. The workspace was exactly as designed. What the agent could *find* was never controlled.

These tests execute real commands inside the boundary rather than checking how paths are built. The
one that matters most runs two slots in sequence and asks whether the second can find anything the
first produced; if it can, the substrate is not doing its job whatever else passes.

Nothing here invokes a model, reaches the network, or uses a credential.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals"))

import _hermetic        # noqa: E402
import _lineage         # noqa: E402
import _mlr             # noqa: E402
import _semantic_view   # noqa: E402

MODULE = _mlr.FIXTURE / "runtime" / "objectstore"
GIT = "/Library/Developer/CommandLineTools/usr/bin/git"
PYTHON = "/Library/Developer/CommandLineTools/usr/bin/python3"

macos_only = unittest.skipUnless(
    sys.platform == "darwin" and Path(_semantic_view.SANDBOX).exists(),
    "the macOS sandbox mechanism is not available on this platform")


_RESIDUE_AT_START: set = set()


def setUpModule():
    global _RESIDUE_AT_START
    _RESIDUE_AT_START = set(_semantic_view.stale_views())


def tearDownModule():
    """No slot this process made may outlive it.

    Asserted over the whole module rather than inside one test, because a leak that happens on every
    slot is invisible to a before-and-after comparison inside a single one — which is exactly how a
    broken cleanup path went unnoticed until forty-five empty tool directories had accumulated. It
    asks the substrate what *it* failed to remove rather than sweeping a shared directory, so a
    second suite running beside this one is not mistaken for residue.
    """
    leaked = _semantic_view.unremoved()
    if leaked:                                              # pragma: no cover - failure path
        raise AssertionError(f"semantic views outlived the tests that made them: {list(leaked)}")


def interpreter_policy():
    """A policy exposing the interpreter this process is running, wherever it lives.

    Nothing about which interpreter is correct belongs in the substrate; the experiment declares one
    and the policy carries it. Here that is simply the one running the tests.
    """
    candidates = [Path(sys.executable), Path(sys.executable).resolve(),
                  Path(sys.base_prefix), Path(sys.base_prefix).resolve()]
    prefix = Path(os.path.commonpath([str(c) for c in candidates]))
    # An interpreter reached through symlinks lives in two places at once — the linked name and the
    # real one — and a policy that exposed only the resolved path would refuse to launch it.
    roots = sorted({str(prefix)})
    return _semantic_view.Policy(
        extra_reads=roots, system_execs=(*_semantic_view.SYSTEM_EXECS, *roots))


def controlled():
    """What this experiment says must not be reachable. Supplied by the caller, never hard-coded."""
    return _hermetic.Sensitive(
        _hermetic.CONTROLLED_EVIDENCE,
        stems=[p.name for p in sorted(MODULE.glob("*.py"))],
        digests=[_mlr.digest_file(p) for p in sorted(MODULE.glob("*.py"))],
        marks=_lineage.source_fingerprint(MODULE))


@macos_only
class ConstructionTest(unittest.TestCase):
    """The view is built, not inherited."""

    maxDiff = None

    def test_every_area_is_fresh_and_writable(self):
        with _semantic_view.semantic_view() as view:
            for area in view.AREAS:
                path = getattr(view, area)
                with self.subTest(area=area):
                    self.assertTrue(path.is_dir())
                    self.assertEqual(list(path.iterdir()), [])
                    (path / "probe").write_text("x", encoding="utf-8")

    def test_a_shell_runs_inside_the_view(self):
        with _semantic_view.semantic_view() as view:
            done = view.shell("echo running")
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stdout.strip(), "running")

    def test_the_working_directory_is_the_workspace(self):
        with _semantic_view.semantic_view() as view:
            self.assertEqual(view.shell("pwd").stdout.strip(), str(view.workspace))

    def test_ordinary_search_tools_work(self):
        """The point is never to forbid discovery. §56."""
        with _semantic_view.semantic_view() as view:
            (view.workspace / "a.txt").write_text("needle\n", encoding="utf-8")
            self.assertIn("a.txt", view.shell("/usr/bin/find . -name '*.txt'").stdout)
            self.assertIn("needle", view.shell("/usr/bin/grep -r needle .").stdout)

    def test_python_runs_and_is_the_pinned_interpreter(self):
        with _semantic_view.semantic_view() as view:
            done = view.run([PYTHON, "-c", "import sys; print(sys.version.split()[0])"])
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(done.stdout.strip(), "3.9.6")


@macos_only
class EnvironmentTest(unittest.TestCase):
    """Assembled from an allowlist, never copied from the host. §8, §9."""

    maxDiff = None

    def test_the_environment_is_exactly_what_was_declared(self):
        policy = _semantic_view.Policy(env={"EXPERIMENT_DECLARED": "yes"})
        with _semantic_view.semantic_view(policy) as view:
            self.assertEqual(set(view.environment()),
                             {"PATH", "HOME", "TMPDIR", "EXPERIMENT_DECLARED"})

    def test_a_host_only_variable_does_not_cross(self):
        """§96 B. The sentinel exists in this process and must not exist in the child."""
        os.environ["PROOFBOUND_HOST_SENTINEL"] = "must-not-cross"
        try:
            with _semantic_view.semantic_view() as view:
                done = view.shell("echo \"[${PROOFBOUND_HOST_SENTINEL:-absent}]\"")
                self.assertEqual(done.stdout.strip(), "[absent]")
                self.assertIn("must-not-cross", os.environ["PROOFBOUND_HOST_SENTINEL"])
        finally:
            os.environ.pop("PROOFBOUND_HOST_SENTINEL", None)

    def test_home_is_the_constructed_home(self):
        with _semantic_view.semantic_view() as view:
            self.assertEqual(view.shell("echo $HOME").stdout.strip(), str(view.home))

    def test_the_temporary_directory_resolves_inside_the_view(self):
        """§48. Both the shell's and the interpreter's idea of it."""
        with _semantic_view.semantic_view() as view:
            self.assertEqual(view.shell("echo $TMPDIR").stdout.strip(), str(view.tmp))
            done = view.run([PYTHON, "-c", "import tempfile; print(tempfile.gettempdir())"])
            self.assertEqual(done.stdout.strip(), str(view.tmp))

    def test_the_path_is_constructed_and_holds_no_personal_directories(self):
        with _semantic_view.semantic_view() as view:
            path = view.environment()["PATH"].split(os.pathsep)
            self.assertEqual(path[0], str(view.tools_root))
            for entry in path[1:]:
                with self.subTest(entry=entry):
                    self.assertIn(entry, _semantic_view.BASE_PATH)


@macos_only
class HostExclusionTest(unittest.TestCase):
    """What the subject cannot reach, tested by trying. §51-§55."""

    maxDiff = None

    def denied(self, view, command):
        done = view.shell(command)
        blob = (done.stdout + done.stderr).lower()
        self.assertTrue(done.returncode != 0 or "not permitted" in blob or not done.stdout.strip(),
                        f"expected denial, got: {done.stdout!r} {done.stderr!r}")

    def test_the_repository_is_unreadable(self):
        with _semantic_view.semantic_view() as view:
            self.denied(view, f"/bin/cat {ROOT / 'README.md'}")
            self.denied(view, f"/bin/ls {ROOT}")

    def test_the_host_home_is_unreadable(self):
        marker = Path.home() / ".pb-r4a-host-marker"
        marker.write_text("host-side marker\n", encoding="utf-8")
        try:
            with _semantic_view.semantic_view() as view:
                self.denied(view, f"/bin/cat {marker}")
                self.denied(view, f"/bin/ls {Path.home()}")
            self.assertEqual(marker.read_text(encoding="utf-8"), "host-side marker\n")
        finally:
            marker.unlink(missing_ok=True)

    def test_the_host_per_user_temporary_directory_is_unreadable(self):
        """Where twelve stale materialisations lived when the treatment failed."""
        host_tmp = Path(tempfile.gettempdir())
        marker = host_tmp / "pb-r4a-host-temp-marker.txt"
        marker.write_text("host temp marker\n", encoding="utf-8")
        try:
            with _semantic_view.semantic_view() as view:
                self.denied(view, f"/bin/cat {marker}")
                self.denied(view, f"/bin/ls {host_tmp}")
        finally:
            marker.unlink(missing_ok=True)

    def test_a_copy_of_the_controlled_source_outside_the_view_is_unreachable(self):
        """§32. A host copy outside the subject's surface is irrelevant to the treatment."""
        outside = Path(tempfile.mkdtemp(prefix="pb-r4a-outside-"))
        try:
            shutil.copy(MODULE / "_store.py", outside / "_store.py")
            with _semantic_view.semantic_view() as view:
                self.denied(view, f"/bin/cat {outside / '_store.py'}")
                found = view.shell("/usr/bin/find / -name '_store.py' 2>/dev/null").stdout
                self.assertNotIn(str(outside), found)
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_the_hidden_oracle_and_reference_are_unreachable(self):
        with _semantic_view.semantic_view() as view:
            self.denied(view, f"/bin/cat {_mlr.FIXTURE / 'hidden' / 'external_test_v2.py'}")
            found = view.shell("/usr/bin/find / -name 'external_test*' 2>/dev/null").stdout
            self.assertEqual(found.strip(), "")

    def test_the_historical_search_finds_only_the_view(self):
        """The exact command that defeated the treatment. §57."""
        with _semantic_view.semantic_view() as view:
            _mlr.compile_runtime(MODULE, view.runtime)
            done = view.shell('/usr/bin/find / -name "objectstore*" -not -path "*/.git/*" '
                              '2>/dev/null')
            hits = [line for line in done.stdout.splitlines() if line.strip()]
            self.assertTrue(hits, "the view's own runtime should be discoverable")
            for hit in hits:
                with self.subTest(hit=hit):
                    # A name outside the view may still be listed, because the parent must stay
                    # listable for the subject to reach its own workspace. Its contents may not be.
                    if "/runtime/objectstore" in hit:
                        continue
                    readable = view.shell(f"/bin/cat {hit} 2>&1 | /usr/bin/head -c 40")
                    self.assertNotIn("LOAD_", readable.stdout)
                    self.assertNotIn("def ", readable.stdout)

    def test_the_parent_of_the_views_holds_nothing_but_views(self):
        """§23. Sibling names are visible; the arrangement is measured, not assumed harmless."""
        report = _semantic_view.parent_is_clear([controlled()])
        self.assertTrue(report["clear"], report["named_artefacts"])

    def test_system_paths_hold_no_controlled_evidence(self):
        """§50. The exposure that remains is checked rather than assumed harmless."""
        report = _hermetic.scan([Path(p) for p in ("/usr/share", "/usr/lib")], [controlled()])
        self.assertEqual(report["findings"], [])


@macos_only
class HermeticityIntegrationTest(unittest.TestCase):
    """The R3 checker, pointed at the constructed surface instead of the host. §26-§32, §58."""

    maxDiff = None

    def scan(self, view):
        return _hermetic.scan(view.roots(), [controlled()])

    def test_a_clean_view_passes(self):
        with _semantic_view.semantic_view() as view:
            self.assertEqual(self.scan(view)["status"], _hermetic.CLEAN)

    def test_a_repository_full_of_source_outside_the_view_does_not_contaminate_it(self):
        """§58. The host holding the canonical source is now expected, not a failure."""
        with _semantic_view.semantic_view() as view:
            self.assertTrue((MODULE / "_store.py").is_file())
            self.assertEqual(self.scan(view)["status"], _hermetic.CLEAN)

    def test_a_planted_copy_inside_the_view_contaminates_it(self):
        """§31, §70. Isolation must not make the checker blind."""
        for area in ("tmp", "home", "workspace"):
            with self.subTest(area=area):
                with _semantic_view.semantic_view() as view:
                    shutil.copy(MODULE / "_store.py", getattr(view, area) / "_store.py")
                    report = self.scan(view)
                    self.assertEqual(report["status"], _hermetic.CONTAMINATED)
                    self.assertEqual(report["findings"][0]["category"],
                                     _hermetic.CONTROLLED_EVIDENCE)

    def test_removing_the_planted_copy_restores_a_clean_result(self):
        with _semantic_view.semantic_view() as view:
            planted = view.tmp / "_store.py"
            shutil.copy(MODULE / "_store.py", planted)
            self.assertEqual(self.scan(view)["status"], _hermetic.CONTAMINATED)
            planted.unlink()
            self.assertEqual(self.scan(view)["status"], _hermetic.CLEAN)

    def test_the_home_is_among_the_scanned_roots(self):
        """§29. The gap R4 found in the R3 root set, closed here."""
        with _semantic_view.semantic_view() as view:
            self.assertIn(view.home, view.roots())

    def test_a_declared_exposure_is_reported_without_failing(self):
        with _semantic_view.semantic_view() as view:
            exposure = view.workspace / "third_party"
            exposure.mkdir()
            shutil.copy(MODULE / "_store.py", exposure / "_store.py")
            report = _hermetic.scan(view.roots(), [controlled()], declared=[str(exposure)])
            self.assertEqual(report["status"], _hermetic.CLEAN)
            self.assertEqual(len(report["declared_exposures"]), 1)


@macos_only
class StagingTest(unittest.TestCase):
    """What crosses inward, and what it must not carry with it. §16-§18, §69."""

    maxDiff = None

    def test_a_staged_file_cannot_mutate_its_control_plane_original(self):
        """§17, mandatory. A shared inode would let the subject rewrite the evaluator's copy."""
        origin = Path(tempfile.mkdtemp(prefix="pb-r4a-origin-"))
        try:
            source = origin / "input.txt"
            source.write_text("ORIGINAL\n", encoding="utf-8")
            with _semantic_view.semantic_view() as view:
                staged = view.stage_file(source, "workspace/input.txt")
                done = view.shell(f"echo MODIFIED > {staged}")
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(staged.read_text(encoding="utf-8").strip(), "MODIFIED")
            self.assertEqual(source.read_text(encoding="utf-8"), "ORIGINAL\n")
        finally:
            shutil.rmtree(origin, ignore_errors=True)

    def test_a_staged_tree_is_copied_rather_than_shared(self):
        origin = Path(tempfile.mkdtemp(prefix="pb-r4a-tree-"))
        try:
            (origin / "pkg").mkdir()
            (origin / "pkg" / "mod.py").write_text("ORIGINAL\n", encoding="utf-8")
            with _semantic_view.semantic_view() as view:
                view.stage_tree(origin, "workspace/staged")
                view.shell("echo MODIFIED > workspace/staged/pkg/mod.py",
                           cwd=view.root)
            self.assertEqual((origin / "pkg" / "mod.py").read_text(encoding="utf-8"), "ORIGINAL\n")
        finally:
            shutil.rmtree(origin, ignore_errors=True)

    def test_a_staged_tool_runs_and_cannot_be_rewritten(self):
        """§18, §69. Hard-linked, outside the writable root, and refused for writing."""
        origin = Path(tempfile.mkdtemp(prefix="pb-r4a-tool-", dir=_semantic_view.DEFAULT_PARENT))
        try:
            source = origin / "hello"
            source.write_text("#!/bin/sh\necho works\n", encoding="utf-8")
            source.chmod(0o755)
            before = source.stat().st_mode
            tool = _semantic_view.Tool("hello", source)
            with _semantic_view.semantic_view(_semantic_view.Policy(tools=[tool])) as view:
                staged = view.tools_root / "hello"
                self.assertEqual(view.run([str(staged)]).stdout.strip(), "works")
                done = view.shell(f"echo broken > {staged}")
                self.assertNotEqual(done.returncode, 0)
                self.assertIn("not permitted", done.stderr.lower())
                # Staging shares an inode, so a mode change here would be a mode change there.
                self.assertEqual(source.stat().st_mode, before)
            self.assertEqual(source.read_text(encoding="utf-8"),
                             "#!/bin/sh\necho works\n")
        finally:
            shutil.rmtree(origin, ignore_errors=True)

    def test_a_tool_on_another_volume_is_refused_rather_than_copied(self):
        """A copied system binary loses its signature and is killed on exec — measured."""
        with self.assertRaises(_semantic_view.ViewError) as caught:
            with _semantic_view.semantic_view(
                    _semantic_view.Policy(tools=[_semantic_view.Tool("echo", "/bin/echo")])):
                pass
        self.assertIn("hard link", str(caught.exception))

    def test_a_tool_is_identified_by_its_bytes(self):
        tool = _semantic_view.Tool("git", GIT)
        self.assertEqual(tool.digest, _mlr.digest_file(Path(GIT)))


@macos_only
class RuntimeStagingTest(unittest.TestCase):
    """The compiled dependency, staged and executed inside the boundary. §42, §43."""

    maxDiff = None

    def test_the_compiled_runtime_imports_and_executes(self):
        """Compiled by the interpreter that will run it, which is what makes the boundary real.

        The interpreter running this suite is not always the one the fixture pins, so the policy is
        asked to expose whichever it is — the same mechanism the experiment will use to expose the
        one it pins, rather than a constant baked into the substrate.
        """
        with _semantic_view.semantic_view(interpreter_policy()) as view:
            _mlr.compile_runtime(MODULE, view.runtime)
            done = view.run(
                [sys.executable, "-c",
                 "import objectstore; objectstore.put('k', b'v'); print(objectstore.get('k'))"],
                env={"PYTHONPATH": str(view.runtime),
                     "OBJECTSTORE_ROOT": str(view.data)})
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIn("b'v'", done.stdout)

    def test_the_interpreter_identity_is_the_running_one(self):
        with _semantic_view.semantic_view(interpreter_policy()) as view:
            done = view.run([sys.executable, "-c",
                             "import sys; print(sys.version.split()[0])"])
            self.assertEqual(done.stdout.strip(), ".".join(map(str, sys.version_info[:3])))

    def test_a_staged_runtime_carries_no_source(self):
        """§43. A contract-shaped view must not acquire source through its own dependency."""
        with _semantic_view.semantic_view() as view:
            _mlr.compile_runtime(MODULE, view.runtime)
            self.assertEqual(list(view.runtime.rglob("*.py")), [])
            self.assertEqual(_hermetic.scan(view.roots(), [controlled()])["status"],
                             _hermetic.CLEAN)


@macos_only
class WorkspaceGitTest(unittest.TestCase):
    """A task-local repository, and no discovery of the one the evaluator is working in. §44, §45."""

    maxDiff = None

    def test_a_task_local_repository_works(self):
        with _semantic_view.semantic_view() as view:
            (view.workspace / "a.txt").write_text("one\n", encoding="utf-8")
            self.assertEqual(view.run([GIT, "init", "-q", "."]).returncode, 0)
            view.run([GIT, "-c", "user.email=eval@proofbound.invalid",
                      "-c", "user.name=Proofbound Eval", "add", "-A"])
            done = view.run([GIT, "-c", "user.email=eval@proofbound.invalid",
                             "-c", "user.name=Proofbound Eval", "commit", "-qm", "baseline"])
            self.assertEqual(done.returncode, 0, done.stderr)
            (view.workspace / "a.txt").write_text("one\ntwo\n", encoding="utf-8")
            self.assertIn("a.txt", view.run([GIT, "status", "--short"]).stdout)
            self.assertIn("1 insertion", view.run([GIT, "diff", "--stat"]).stdout)

    def test_git_does_not_discover_the_evaluator_repository(self):
        with _semantic_view.semantic_view() as view:
            done = view.run([GIT, "rev-parse", "--show-toplevel"])
            self.assertNotIn(str(ROOT), done.stdout)

    def test_the_real_binary_is_used_rather_than_the_shim(self):
        """The shim tries to write an xcrun cache into host temp; the real one does not."""
        with _semantic_view.semantic_view() as view:
            done = view.run([GIT, "--version"])
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertNotIn("xcrun", done.stderr)


@macos_only
class EgressTest(unittest.TestCase):
    """What comes back, and what the subject knows about where it goes. §38, §39."""

    maxDiff = None

    def test_a_product_is_recovered_and_survives_destruction(self):
        destination = Path(tempfile.mkdtemp(prefix="pb-r4a-out-"))
        try:
            with _semantic_view.semantic_view() as view:
                view.shell("echo produced > result.txt")
                view.collect("workspace/result.txt", destination / "result.txt")
                root = view.root
            self.assertFalse(root.exists())
            self.assertEqual((destination / "result.txt").read_text(encoding="utf-8").strip(),
                             "produced")
        finally:
            shutil.rmtree(destination, ignore_errors=True)

    def test_the_destination_is_not_reachable_from_inside(self):
        destination = Path(tempfile.mkdtemp(prefix="pb-r4a-out-"))
        try:
            (destination / "already-there.txt").write_text("control plane\n", encoding="utf-8")
            with _semantic_view.semantic_view() as view:
                done = view.shell(f"/bin/cat {destination / 'already-there.txt'}")
                self.assertNotIn("control plane", done.stdout)
        finally:
            shutil.rmtree(destination, ignore_errors=True)


@macos_only
class LifecycleTest(unittest.TestCase):
    """Destruction on every path out. §35-§37, §49-§52."""

    maxDiff = None

    def test_normal_exit_destroys_the_view(self):
        with _semantic_view.semantic_view() as view:
            root, tools = view.root, view.tools_root
            self.assertTrue(root.is_dir())
        self.assertFalse(root.exists())
        self.assertFalse(tools.exists())

    def test_an_exception_destroys_the_view(self):
        seen = {}
        with self.assertRaises(RuntimeError):
            with _semantic_view.semantic_view() as view:
                seen["root"] = view.root
                (view.workspace / "half-done.txt").write_text("x", encoding="utf-8")
                raise RuntimeError("something went wrong mid-slot")
        self.assertFalse(seen["root"].exists())

    def test_a_failing_child_command_still_leaves_a_clean_host(self):
        with _semantic_view.semantic_view() as view:
            root = view.root
            done = view.shell("exit 3")
            self.assertEqual(done.returncode, 3)
        self.assertFalse(root.exists())

    def test_a_construction_failure_leaves_nothing_behind(self):
        """§37. A tool that is not there fails the slot after directories exist."""
        before = set(_semantic_view.stale_views())
        with self.assertRaises(_semantic_view.ViewError):
            _semantic_view.Tool("absent", "/definitely/not/here")
        with self.assertRaises(RuntimeError):
            with _semantic_view.semantic_view() as view:
                self.assertTrue(view.root.is_dir())
                raise RuntimeError("construction aborted")
        self.assertEqual(set(_semantic_view.stale_views()), before)

    def test_no_slot_directory_survives_a_completed_run(self):
        before = set(_semantic_view.stale_views())
        with _semantic_view.semantic_view():
            pass
        self.assertEqual(set(_semantic_view.stale_views()), before)


@macos_only
class SequentialSlotTest(unittest.TestCase):
    """The acceptance test: can slot two find anything slot one produced? §33, §68, §97."""

    maxDiff = None

    MARKERS = {
        "workspace": "PB-R4A-MARKER-WORKSPACE",
        "home": "PB-R4A-MARKER-HOME",
        "tmp": "PB-R4A-MARKER-TMP",
        "session": "PB-R4A-MARKER-SESSION",
        "data": "PB-R4A-MARKER-DATA",
    }

    def test_the_second_slot_finds_nothing_the_first_produced(self):
        first = {}
        with _semantic_view.semantic_view() as slot_a:
            for area, marker in self.MARKERS.items():
                target = getattr(slot_a, area)
                (target / f"{marker}.txt").write_text(marker + "\n", encoding="utf-8")
                (target / "nested" / "deeper").mkdir(parents=True)
                (target / "nested" / "deeper" / "note.txt").write_text(marker, encoding="utf-8")
            slot_a.shell("echo shell-produced > $TMPDIR/from-the-shell.txt")
            first = {"root": slot_a.root, "areas": {a: getattr(slot_a, a)
                                                    for a in slot_a.AREAS}}
        self.assertFalse(first["root"].exists(), "slot A must be gone before slot B starts")

        with _semantic_view.semantic_view() as slot_b:
            self.assertNotEqual(slot_b.root, first["root"])
            for area, path in first["areas"].items():
                with self.subTest(area=area):
                    self.assertNotEqual(getattr(slot_b, area), path)
            # Depth-bounded so the test stays a few seconds rather than minutes: an unbounded
            # walk re-traverses the whole data volume through /System/Volumes and every refused
            # stat costs a policy check. Six levels reaches the view, the host temp directories,
            # the evaluator's home and the repository — every place a marker could be.
            search = slot_b.shell(
                "/usr/bin/find / -maxdepth 6 -name 'PB-R4A-MARKER-*' 2>/dev/null; "
                "/usr/bin/find / -maxdepth 6 -name 'from-the-shell.txt' 2>/dev/null",
                timeout=300)
            self.assertEqual(search.stdout.strip(), "", search.stdout)
            reachable = slot_b.shell(
                "/usr/bin/grep -rl 'PB-R4A-MARKER' /private/tmp 2>/dev/null | /usr/bin/head -5",
                timeout=300)
            self.assertEqual(reachable.stdout.strip(), "", reachable.stdout)
            for area, path in first["areas"].items():
                with self.subTest(read=area):
                    done = slot_b.shell(f"/bin/cat {path}/*.txt 2>&1")
                    self.assertNotIn("PB-R4A-MARKER", done.stdout)
            self.assertEqual(_hermetic.scan(slot_b.roots(), [controlled()])["status"],
                             _hermetic.CLEAN)


@macos_only
class PolicyIdentityTest(unittest.TestCase):
    """What kind of boundary this is, as against which instance is running. §60-§62."""

    maxDiff = None

    def test_two_slots_of_one_policy_share_an_identity(self):
        policy = _semantic_view.Policy(env={"A": "1"})
        with _semantic_view.semantic_view(policy) as first:
            with _semantic_view.semantic_view(policy) as second:
                self.assertNotEqual(first.root, second.root)
                self.assertEqual(first.describe()["policy_identity"],
                                 second.describe()["policy_identity"])

    def test_the_slot_path_is_not_part_of_the_identity(self):
        policy = _semantic_view.Policy()
        with _semantic_view.semantic_view(policy) as view:
            self.assertNotIn(str(view.root), policy.identity())
        self.assertEqual(policy.identity(), _semantic_view.Policy().identity())

    def test_exposing_another_root_changes_the_identity(self):
        base = _semantic_view.Policy()
        wider = _semantic_view.Policy(extra_reads=[str(Path.home())])
        self.assertNotEqual(base.identity(), wider.identity())

    def test_changing_the_environment_allowlist_changes_the_identity(self):
        self.assertNotEqual(_semantic_view.Policy().identity(),
                            _semantic_view.Policy(env={"NEW": "1"}).identity())

    def test_changing_a_staged_tool_changes_the_identity(self):
        one = _semantic_view.Policy(tools=[_semantic_view.Tool("t", "/bin/echo")])
        two = _semantic_view.Policy(tools=[_semantic_view.Tool("t", "/bin/cat")])
        self.assertNotEqual(one.identity(), two.identity())

    def test_opening_the_network_changes_the_identity(self):
        self.assertNotEqual(_semantic_view.Policy().identity(),
                            _semantic_view.Policy(network=True).identity())


class GenericityTest(unittest.TestCase):
    """The substrate must not know what it is isolating. §66."""

    maxDiff = None

    def test_the_substrate_names_no_experiment(self):
        text = (ROOT / "evals" / "_semantic_view.py").read_text(encoding="utf-8")
        for word in ("objectstore", "_store", "third_party", "DeepSeek", "external_test",
                     "MLR", "FULL", "CONTRACT", "opencode"):
            with self.subTest(word=word):
                self.assertNotIn(word, text)

    def test_the_experiment_supplies_what_is_sensitive(self):
        policy = _semantic_view.Policy(declared=["workspace/third_party"])
        self.assertEqual(policy.declared, ("workspace/third_party",))


if __name__ == "__main__":                                  # pragma: no cover
    unittest.main()

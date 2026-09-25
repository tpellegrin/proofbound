"""A declared project toolchain: prepared bytes the worker boundary runs and cannot change.

Reproduced first with BorrowDesk (Node 24.19.0, TypeScript 7), in the production boundary:
- the pinned Node and npm under the owner's home could not run;
- TypeScript 7's native compiler, executed from the project's `node_modules`, was refused;
- so a worker could not run the project's check.

These tests use a synthetic Node distribution, so they do not depend on the host's Node. Its
`node` and `npm` are shell scripts, and its "native" dependency is a copy of a system binary
installed under `node_modules`: a copy of the test interpreter, because a copied Apple platform
binary is killed on current macOS. What each group falsifies:
- **Preparation.** An unusable declaration is refused before anything is created. A usable one is
  copied into the run and recorded by content, with the project's dependencies.
- **The boundary.** The prepared `bin` is on the worker `PATH`; the installed dependencies execute
  and nothing else in the project does. Neither the toolchain nor `node_modules` can be written,
  replaced or renamed, and worker npm is offline.
- **Launch.** A changed toolchain, changed `node_modules` or changed dependency declaration is
  refused before a slot is reserved.
- **Readiness.** Project tooling is reported verified only after the check ran inside the boundary.
- **An undeclared run** keeps its behaviour: no toolchain, no new rule, no new `PATH` entry.
- **`verify-delivery`** uses the declared source only while it holds the prepared bytes, and
  prepares the fresh checkout as the run was prepared. A candidate that declares other
  dependencies than the run prepared is refused before `npm ci`, and a failed or incomplete
  preparation fails verification with its output retained. Reproduced at `a5d0ac2`: a delivery
  whose recorded lockfile digest differed reported `lockfile_matches_prepared: false` beside
  `verified: true`.
"""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/pb_workflow.py"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import _toolchain                                                          # noqa: E402
import _host_serial                                                        # noqa: E402

FAKE_EXECUTOR = r'''#!PYTHON
import sys
if sys.argv[1:3] == ['session', 'list']:
    print('[]'); sys.exit()
'''

NPM = r'''#!/bin/sh
case "$1" in
  --version) echo 11.0.0-test ;;
  ci) if [ -f fail-ci ]; then
        [ "$(cat fail-ci)" = partial ] && mkdir -p node_modules/.bin
        echo "npm error simulated preparation failure" >&2; exit 1
      fi
      echo "added 1 package"
      mkdir -p node_modules/.bin node_modules/native
      printf '#!/bin/sh\necho shim-ran\n' > node_modules/.bin/tool; chmod +x node_modules/.bin/tool
      cp NATIVE node_modules/native/tool
      if [ -f rewrite-lock ]; then printf '{"lockfileVersion": 3, "rewritten": true}\n' > package-lock.json; fi ;;
  run) [ "$2" = check ] && exec /bin/sh ./check.sh ;;
  install) echo "installing $2" ; exit 1 ;;
esac
'''

CHECK = '''set -e
node --version
node_modules/.bin/tool
node_modules/native/tool -c "print('native-ran')"
mkdir -p dist && echo built > dist/out.txt
'''


def setUpModule():
    _host_serial.serialise(__name__)


def tearDownModule():
    _host_serial.release()


def sandbox_available():
    return Path("/usr/bin/sandbox-exec").exists() and subprocess.run(
        ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)", "/usr/bin/true"],
        capture_output=True).returncode == 0


def distribution(root: Path, version="99.0.0-test") -> Path:
    dist = root / "node-dist"
    (dist / "bin").mkdir(parents=True)
    npm = dist / "lib/node_modules/npm/bin"
    npm.mkdir(parents=True)
    (dist / "bin/node").write_text(f'#!/bin/sh\n[ "$1" = --version ] && echo v{version}\n')
    (npm / "npm-cli.js").write_text(NPM.replace("NATIVE", str(Path(sys.executable).resolve())))
    (npm / "npx-cli.js").write_text("#!/bin/sh\nexit 0\n")
    for script in (dist / "bin/node", npm / "npm-cli.js", npm / "npx-cli.js"):
        script.chmod(0o755)
    os.symlink("../lib/node_modules/npm/bin/npm-cli.js", dist / "bin/npm")
    os.symlink("../lib/node_modules/npm/bin/npx-cli.js", dist / "bin/npx")
    return dist


def node_project(root: Path, dist: Path, *, install=True, version="99.0.0-test") -> Path:
    project = root / "project"
    project.mkdir()
    (project / ".gitignore").write_text("DeepSeekAndDestroy/\nnode_modules/\ndist/\n")
    (project / ".node-version").write_text(version + "\n")
    (project / "package.json").write_text(json.dumps(
        {"name": "p", "version": "1.0.0", "scripts": {"check": "sh ./check.sh"},
         "devDependencies": {"tool": "1.0.0"}}, indent=2) + "\n")
    (project / "package-lock.json").write_text('{"lockfileVersion": 3}\n')
    (project / "check.sh").write_text(CHECK)
    for argv in [("init", "-q"), ("config", "user.name", "T"),
                 ("config", "user.email", "t@e.invalid"), ("add", "."), ("commit", "-qm", "i")]:
        subprocess.run(["git", "-C", str(project), *argv], check=True)
    if install:
        subprocess.run([str(dist / "bin/npm"), "ci"], cwd=project, check=True, capture_output=True)
    return project


class Harness:
    def __init__(self, case, *, toolchain=True, install=True, version="99.0.0-test", executor=None):
        self.case = case
        # macOS resolves /tmp to /private/tmp, and the boundary matches real paths; elsewhere,
        # the platform default.
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-toolchain-",
                                         dir="/private/tmp" if sys.platform == "darwin" else None))
        case.addCleanup(shutil.rmtree, self.tmp, True)
        self.dist = distribution(self.tmp)
        self.project = node_project(self.tmp, self.dist, install=install, version=version)
        home = self.tmp / "fake-home"
        (home / ".local/share/opencode").mkdir(parents=True)
        (home / ".local/share/opencode/auth.json").write_text(json.dumps(
            {"deepseek": {"type": "api", "key": "sk-proofbound-dummy-not-a-key"}}))
        self.secret = home / "private.txt"
        self.secret.write_text("private\n")
        self.env = {**os.environ, "HOME": str(home)}
        fake = self.tmp / "bin/opencode"
        fake.parent.mkdir()
        fake.write_text(FAKE_EXECUTOR.replace("PYTHON", sys.executable))
        fake.chmod(0o755)
        self.executor = executor or fake
        self.toolchain = toolchain

    def cli(self, *args):
        cp = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True,
                            text=True, stdin=subprocess.DEVNULL, env=self.env, timeout=300)
        return json.loads(cp.stdout)

    def start(self):
        extra = ["--toolchain", self.dist] if self.toolchain else []
        out = self.cli("start", "--project", self.project, "--goal", "g", "--check",
                       "npm run check", "--executor", self.executor, *extra)
        if "run" in out:
            self.run = Path(out["run"])
            config = self.config()
            self.case.addCleanup(shutil.rmtree, Path(config["home"]).parent, True)
        return out

    def config(self):
        return json.loads((self.run / "run-config.json").read_text())

    def authorize(self):
        out = self.cli("authorize-spending", "--run", self.run, "--aggregate-limit", 1,
                       "--reserve", 0.05, "--launch-ceiling", 3, "--owner-authorization",
                       "TEST ONLY: throwaway run; dummy credential; no launch")
        self.case.assertTrue(out.get("configured"), out)
        # Should a refusal regress into a launch, the worker reaches a closed loopback port, never
        # the provider.
        config = self.config()
        redirect = Path(config["home"]).parent / "provider-redirect.json"
        redirect.write_text(json.dumps({"provider": {"deepseek": {
            "options": {"baseURL": "http://127.0.0.1:9/v1"}}}}))
        config["worker_env"] = {"OPENCODE_CONFIG": str(redirect)}
        (self.run / "run-config.json").write_text(json.dumps(config, indent=2))
        return out

    def slots(self):
        path = self.run / "launch-ledger.json"
        return json.loads(path.read_text())["slots"] if path.is_file() else []

    def inside(self, *argv):
        import _workflow_boundary
        config = self.config()
        cp = subprocess.run(["/usr/bin/sandbox-exec", "-f", config["boundary_profile"], *argv],
                            cwd=self.project, env=_workflow_boundary.worker_env(config),
                            capture_output=True, text=True, timeout=120)
        return cp.returncode, cp.stdout + cp.stderr


class Preparation(unittest.TestCase):
    def test_a_declared_toolchain_is_copied_and_recorded_by_content(self):
        h = Harness(self)
        h.start()
        record = h.config()["toolchain"]
        prepared = Path(record["prepared"])
        self.assertTrue(prepared.is_relative_to(Path(h.config()["home"]).parent))
        self.assertEqual((record["node_version"], record["npm_version"]),
                         ("v99.0.0-test", "11.0.0-test"))
        self.assertEqual(record["identity"], _toolchain.identity(h.dist))
        self.assertEqual(sorted(os.listdir(prepared / "bin")), ["node", "npm", "npx"])
        deps = record["dependencies"]
        self.assertEqual(deps["manifest"]["fields"], ["devDependencies"])
        self.assertIsNotNone(deps["node_modules"]["digest"])
        self.assertEqual(_toolchain.problems(h.config()), [])

    def test_an_unusable_declaration_creates_nothing(self):
        for words, kwargs in {"not installed": dict(install=False),
                              "pins 98.0.0": dict(version="98.0.0")}.items():
            with self.subTest(words):
                h = Harness(self, **kwargs)
                out = h.start()
                self.assertIn(words, out.get("error", ""), out)
                self.assertFalse((h.project / "DeepSeekAndDestroy").exists())

    def test_a_toolchain_whose_links_leave_it_is_refused(self):
        for label, text in {"absolute": None, "not copied": "../lib/node_modules/other/cli.js"}.items():
            with self.subTest(label):
                h = Harness(self)
                (h.dist / "lib/node_modules/other").mkdir()
                (h.dist / "lib/node_modules/other/cli.js").write_text("#!/bin/sh\n")
                link = h.dist / "bin/npx"
                link.unlink()
                os.symlink(text or str(h.dist / "lib/node_modules/npm/bin/npx-cli.js"), link)
                out = h.start()
                self.assertIn("symlinks that leave the copied toolchain", out.get("error", ""), out)
                self.assertFalse((h.project / "DeepSeekAndDestroy").exists())

    def test_a_repeated_start_names_a_changed_toolchain(self):
        h = Harness(self)
        h.start()
        h.toolchain = False
        out = h.start()
        self.assertIn("--toolchain", json.dumps(out))

    def test_acceptance_checks_use_the_prepared_bytes_and_refuse_changed_dependencies(self):
        import pb_workflow
        h = Harness(self)
        h.start()
        config = h.config()
        checked = json.loads(Path(pb_workflow.check_project(h.run, config)).read_text())["result"]
        self.assertIn("v99.0.0-test", checked["stdout"])            # the prepared node, not the host's
        self.assertIn("native-ran", checked["stdout"])
        package = json.loads((h.project / "package.json").read_text())
        package["dependencies"] = {"added": "1.0.0"}
        (h.project / "package.json").write_text(json.dumps(package))
        with self.assertRaisesRegex(ValueError, "refused.*dependency declarations"):
            pb_workflow.check_project(h.run, config)

    def test_project_tooling_is_verified_only_by_a_passing_check_inside_the_boundary(self):
        h = Harness(self)
        h.start()
        tooling = h.cli("status", "--run", h.run)["project_tooling"]
        self.assertEqual((tooling["verified"], tooling["why"][:15]), (False, "not checked yet"))
        config = h.config()
        config["toolchain"]["boundary_check"] = {"passed": False, "returncode": 3}
        (h.run / "run-config.json").write_text(json.dumps(config))
        tooling = h.cli("status", "--run", h.run)["project_tooling"]
        self.assertFalse(tooling["verified"])
        self.assertIn("did not pass", tooling["why"])


def boundary_harness(case, **kwargs):
    if not sandbox_available():
        case.skipTest("sandbox-exec cannot start inside this process")
    from test_supervision import pinned_executor
    executor = pinned_executor()
    if executor is None:
        case.skipTest("authorization needs the pinned OpenCode 1.18.29 build, not installed here")
    h = Harness(case, executor=executor, **kwargs)
    h.start()
    h.authorize()
    return h


@unittest.skipUnless(sys.platform == "darwin", "the worker boundary is macOS sandbox-exec")
class Boundary(unittest.TestCase):
    def test_authorization_verifies_the_project_check_inside_the_boundary(self):
        h = boundary_harness(self)
        tooling = h.cli("status", "--run", h.run)["project_tooling"]
        self.assertTrue(tooling["verified"], tooling)
        self.assertEqual(tooling["check"]["returncode"], 0)
        self.assertIn("native-ran", "\n".join(h.config()["toolchain"]["boundary_check"]["tail"]))

    def test_the_worker_runs_the_prepared_tooling_and_cannot_change_it(self):
        h = boundary_harness(self)
        prepared = h.config()["toolchain"]["prepared"]
        rc, out = h.inside("/bin/sh", "-c", "command -v node; npm run check")
        self.assertEqual(rc, 0, out)
        self.assertIn(f"{prepared}/bin/node", out)
        self.assertIn("native-ran", out)
        self.assertTrue((h.project / "dist/out.txt").is_file())
        refusals = {
            "write the toolchain": f"touch {prepared}/bin/evil",
            "rename the toolchain": f"mv {prepared} {prepared}-old",
            "replace npm": f"rm -f {prepared}/bin/npm",
            "write node_modules": "touch node_modules/evil",
            "rename node_modules": "mv node_modules nm-old",
            "replace a shim": "rm -f node_modules/.bin/tool",
            "read the owner's home": f"cat {h.secret}",
            "change a toolchain mode": f"chmod a-x {prepared}/bin/node",
            "change a dependency mode": "chmod a-x node_modules/native/tool",
            "hard-link a toolchain file": f"ln {prepared}/bin/node linked",
            "hard-link a dependency": "ln node_modules/native/tool linked",
            "rename the run's runtime": f"mv {Path(prepared).parent} {Path(prepared).parent}-old",
            "rename the project": f"mv {h.project} {h.project}-old",
        }
        for label, command in refusals.items():
            with self.subTest(label):
                rc, out = h.inside("/bin/sh", "-c", command)
                self.assertNotEqual(rc, 0, out)
                self.assertIn("Operation not permitted", out)
        # The same native bytes, outside node_modules, do not execute.
        shutil.copy(h.project / "node_modules/native/tool", h.project / "copied-tool")
        rc, out = h.inside("./copied-tool", "-c", "pass")
        self.assertNotEqual(rc, 0)
        self.assertIn("Operation not permitted", out)
        rc, out = h.inside("/bin/sh", "-c", "env | grep npm_config_offline")
        self.assertIn("npm_config_offline=true", out)
        self.assertEqual(_toolchain.problems(h.config()), [])

    def test_a_changed_or_missing_preparation_is_refused_before_a_slot_is_reserved(self):
        h = boundary_harness(self)
        h.cli("continue", "--run", h.run)                      # bind; nothing launched
        prepared = Path(h.config()["toolchain"]["prepared"])
        moved = prepared.with_name("moved-aside")
        package = h.project / "package.json"
        original = package.read_text()
        tampered = json.loads(original)
        tampered["devDependencies"]["other"] = "2.0.0"
        changes = {
            "dependency declarations": (lambda: package.write_text(json.dumps(tampered)),
                                        lambda: package.write_text(original)),
            "installed node_modules": (lambda: (h.project / "node_modules/extra").write_text("x"),
                                       lambda: (h.project / "node_modules/extra").unlink()),
            "missing toolchain": (lambda: prepared.rename(moved), lambda: moved.rename(prepared)),
            "added to the toolchain": (lambda: (prepared / "bin/extra").write_text("x"),
                                       lambda: (prepared / "bin/extra").unlink()),
            "changed toolchain": (lambda: (prepared / "bin/node").write_text("#!/bin/sh\n"), None),
        }
        for words, (change, undo) in changes.items():
            with self.subTest(words):
                change()
                launch = h.cli("continue", "--run", h.run)["launch"]
                self.assertFalse(launch["launched"])
                self.assertIn(words.split()[-1], " ".join(launch["why"]))
                self.assertEqual(h.slots(), [])
                if undo:
                    undo()


@unittest.skipUnless(sys.platform == "darwin", "the worker boundary is macOS sandbox-exec")
class Undeclared(unittest.TestCase):
    def test_an_undeclared_run_keeps_its_behaviour(self):
        h = boundary_harness(self, toolchain=False)
        config = h.config()
        self.assertNotIn("toolchain", config)
        profile = Path(config["boundary_profile"]).read_text()
        self.assertNotIn("node_modules", profile)
        self.assertNotIn(str(h.dist), profile)
        self.assertNotIn("project_tooling", h.cli("status", "--run", h.run))
        self.assertFalse((Path(config["home"]).parent / "toolchain").exists())
        rc, out = h.inside("/bin/sh", "-c", "node --version")
        self.assertEqual(rc, 127, out)
        rc, out = h.inside("node_modules/native/tool", "-c", "pass")
        self.assertIn("Operation not permitted", out)
        doctor = h.cli("doctor", "--executor", h.executor)
        self.assertIn("not checked by doctor", doctor["readiness"]["project_tooling"])


class VerifyDelivery(unittest.TestCase):
    """The toolchain path of `verify-delivery`, on a delivery built for the purpose."""

    def delivery(self, h, *, adds=("new.txt", "hello"), toolchain=True,
                 check="npm run check"):
        from dsd_state import atomic_json
        baseline = subprocess.check_output(["git", "-C", str(h.project), "rev-parse", "HEAD"],
                                           text=True).strip()
        out = h.tmp / "delivery"
        (out / "evidence").mkdir(parents=True)
        name, line = adds
        (out / "change.patch").write_text(f"diff --git a/{name} b/{name}\nnew file mode 100644\n"
                                          f"--- /dev/null\n+++ b/{name}\n@@ -0,0 +1 @@\n+{line}\n")
        atomic_json(out / "handoff.json", {"baseline": baseline, "outcome": "accepted"})
        config = {"check_command": check, "paths": {"project": str(h.project)}}
        if toolchain:
            config["toolchain"] = _toolchain.prepare(h.dist, h.tmp / "runtime", h.project)
        atomic_json(out / "evidence/run-config.json", config)
        self.seal(out)
        return out

    @staticmethod
    def seal(out):
        """Rewrite the synthetic delivery's manifest, as a consistent delivery would carry."""
        from dsd_state import atomic_json
        import hashlib
        atomic_json(out / "manifest.json", {
            str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in out.rglob("*") if p.is_file() and p.name != "manifest.json"})

    def verify(self, h, delivery):
        cp = subprocess.run([sys.executable, str(CLI), "verify-delivery", "--delivery", delivery,
                             "--into", h.tmp / f"verify-{len(list(h.tmp.glob('verify-*')))}"],
                            capture_output=True, text=True, env=h.env, timeout=300)
        return json.loads(cp.stdout)

    def test_the_checkout_is_prepared_like_the_run_and_checked_with_the_same_bytes(self):
        h = Harness(self)
        got = self.verify(h, self.delivery(h))
        self.assertTrue(got["verified"], got)
        deps = got["dependencies"]
        self.assertEqual(deps["returncode"], 0)
        self.assertTrue(deps["matches_prepared"])
        self.assertTrue(deps["before"]["lockfile_matches_prepared"])
        self.assertTrue(deps["lockfile_matches_prepared"])
        self.assertTrue(deps["manifest_matches_prepared"])
        self.assertTrue(deps["node_modules_present"])
        self.assertIn("added 1 package", deps["stdout"], "preparation output is retained")
        self.assertIn("registry", deps["note"])
        self.assertIn("native-ran", got["project_check"]["stdout"])

    def test_a_recorded_lockfile_identity_the_candidate_does_not_match_is_not_verified(self):
        """Reproduced at a5d0ac2: `lockfile_matches_prepared: false` beside `verified: true`."""
        h = Harness(self)
        delivery = self.delivery(h)
        path = delivery / "evidence/run-config.json"
        config = json.loads(path.read_text())
        config["toolchain"]["dependencies"]["lockfile"]["sha256"] = "0" * 64
        path.write_text(json.dumps(config))
        self.seal(delivery)
        got = self.verify(h, delivery)
        self.assertEqual(got["manifest_altered"], [])
        self.assertFalse(got["verified"], got)
        deps = got["dependencies"]
        self.assertFalse(deps["matches_prepared"])
        self.assertFalse(deps["before"]["lockfile_matches_prepared"])
        self.assertIsNone(deps["returncode"])
        self.assertIn("not run", deps["why"])
        self.assertFalse((Path(got["checkout"]) / "node_modules").exists(),
                         "a mismatch known before installation installs nothing")
        self.assertIsNone(got["project_check"]["passed"])

    def test_a_preparation_that_changes_the_declared_dependencies_is_not_verified(self):
        h = Harness(self)
        got = self.verify(h, self.delivery(h, adds=("rewrite-lock", "yes")))
        self.assertFalse(got["verified"], got)
        deps = got["dependencies"]
        self.assertEqual(deps["returncode"], 0)
        self.assertTrue(deps["before"]["lockfile_matches_prepared"])
        self.assertFalse(deps["lockfile_matches_prepared"])
        self.assertIn("no longer declares", deps["why"])
        self.assertIsNone(got["project_check"]["passed"])

    def test_a_failed_preparation_is_diagnosable_whether_nothing_or_part_was_installed(self):
        for content, present in (("nothing", False), ("partial", True)):
            with self.subTest(installed=content):
                h = Harness(self)
                got = self.verify(h, self.delivery(h, adds=("fail-ci", content)))
                self.assertFalse(got["verified"], got)
                deps = got["dependencies"]
                self.assertEqual(deps["returncode"], 1)
                self.assertFalse(deps["matches_prepared"])
                self.assertIn("did not succeed", deps["why"])
                self.assertIn("simulated preparation failure", deps["stderr"])
                self.assertEqual(deps["node_modules_present"], present)
                self.assertIsNone(got["project_check"]["passed"])
                self.assertIn("did not succeed", got["project_check"]["note"])
                written = json.loads((Path(got["checkout"]).parent / "verification.json").read_text())
                self.assertEqual(written["verified"], False)

    def test_a_preparation_command_that_cannot_start_is_reported_not_raised(self):
        h = Harness(self)
        delivery = self.delivery(h)
        path = delivery / "evidence/run-config.json"
        config = json.loads(path.read_text())
        config["toolchain"]["dependencies"]["prepare_command"] = ["pb-no-such-npm", "ci"]
        path.write_text(json.dumps(config))
        self.seal(delivery)
        got = self.verify(h, delivery)
        self.assertFalse(got["verified"], got)
        deps = got["dependencies"]
        self.assertIsNone(deps["returncode"])
        self.assertIn("could not be started", deps["why"])
        self.assertFalse(deps["node_modules_present"])
        self.assertIsNone(got["project_check"]["passed"])

    def test_a_delivery_without_a_declared_toolchain_is_unchanged(self):
        h = Harness(self)
        check = f"{shlex.quote(sys.executable)} -c pass"
        got = self.verify(h, self.delivery(h, toolchain=False, check=check))
        self.assertTrue(got["verified"], got)
        self.assertNotIn("dependencies", got)
        self.assertTrue(got["project_check"]["passed"])
        self.assertFalse((Path(got["checkout"]) / "node_modules").exists())

    def test_a_changed_source_is_not_used(self):
        h = Harness(self)
        delivery = self.delivery(h)
        (h.dist / "lib/node_modules/npm/bin/npm-cli.js").write_text(NPM + "# changed\n")
        got = self.verify(h, delivery)
        self.assertFalse(got["verified"])
        self.assertIn("no longer holds", got["project_check"]["note"])


if __name__ == "__main__":
    unittest.main()

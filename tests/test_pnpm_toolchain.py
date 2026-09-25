"""A pnpm project under a declared toolchain: prepared, pinned, protected and verified.

These use a synthetic Node distribution and a synthetic pnpm package, so they do not depend on the
host's Node or pnpm. The synthetic `node` runs a `.cjs` file as a shell script, so the prepared
`bin/pnpm` wrapper runs the synthetic `pnpm.cjs` exactly as it would run the real one. The
synthetic `pnpm install` builds pnpm's isolated layout (a `.pnpm` virtual store, relative symlinks,
`.modules.yaml`), and a file in the project steers it: fail, hard-link from an outside store, or
leave the project with a symlink.

What each group falsifies:
- **Preparation.** The pnpm package is copied and recorded, and bound to the lockfile, the
  manifest's installation fields and pnpm's configuration files. A wrong pin, a missing or double
  lockfile, a workspace, patches, local dependencies, credentials in `.npmrc`, a store hard link or
  an escaping symlink is refused before anything is created.
- **Drift.** A changed lockfile, `pnpm` field, `.npmrc`, installed tree or prepared pnpm is found
  before a launch slot is reserved, and refuses acceptance.
- **Verification.** A fresh checkout is installed by the declared pnpm with `--frozen-lockfile`,
  into a store inside the verification directory, and reported as a registry fetch, never as
  offline. A mismatch is refused before installation; a failed or store-linked install fails.
- **The boundary** runs `pnpm run` with the prepared pnpm and cannot write to it or to
  `node_modules`.
- **npm runs** keep their record shape.
"""
import json
import os
from pathlib import Path
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
import _package_manager as pm                                              # noqa: E402
import _host_serial                                                        # noqa: E402
import test_toolchain as npm_tests                                         # noqa: E402

VERSION = "9.15.9-test"
NODE = '#!/bin/sh\ncase "$1" in\n  --version) echo v99.0.0-test ;;\n  *.cjs) f="$1"; shift; exec /bin/sh "$f" "$@" ;;\nesac\n'
PNPM = r'''case "$1" in
  --version) echo VERSION ;;
  install)
    case " $* " in *" --frozen-lockfile "*) ;; *) echo "not frozen" >&2; exit 2 ;; esac
    if [ -f fail-install ]; then mkdir -p node_modules; echo "ERR_PNPM simulated failure" >&2; exit 1; fi
    echo "Packages: +1"
    mkdir -p node_modules/.pnpm/tool@1.0.0/node_modules/tool node_modules/.pnpm/native node_modules/.bin
    printf 'layoutVersion: 5\nnodeLinker: isolated\npackageManager: pnpm@VERSION\n' > node_modules/.modules.yaml
    printf '#!/bin/sh\necho shim-ran\n' > node_modules/.pnpm/tool@1.0.0/node_modules/tool/cli.sh
    chmod +x node_modules/.pnpm/tool@1.0.0/node_modules/tool/cli.sh
    ln -s .pnpm/tool@1.0.0/node_modules/tool node_modules/tool
    printf '#!/bin/sh\nexec "$(dirname "$0")/../tool/cli.sh"\n' > node_modules/.bin/tool; chmod +x node_modules/.bin/tool
    cp NATIVE node_modules/.pnpm/native/tool
    printf 'home = %s\n' "PYHOME" > node_modules/.pnpm/native/pyvenv.cfg
    if [ -f hardlink-store ]; then mkdir -p ../outside-store; echo x > ../outside-store/f; ln ../outside-store/f node_modules/.pnpm/linked; fi
    if [ -f escape-link ]; then ln -s /usr/bin node_modules/escape; fi ;;
  run) [ "$2" = check ] && exec /bin/sh ./check.sh ;;
esac
'''
CHECK = '''set -e
pnpm --version
echo "offline=$npm_config_offline"
node_modules/.bin/tool
node_modules/.pnpm/native/tool -c "print('native-ran')"
'''
LOCK = "lockfileVersion: '9.0'\n\nimporters:\n\n  .:\n    devDependencies:\n      tool:\n        specifier: 1.0.0\n        version: 1.0.0\n\npackages:\n\n  tool@1.0.0:\n    resolution: {integrity: sha512-x}\n"


def setUpModule():
    _host_serial.serialise(__name__)


def tearDownModule():
    _host_serial.release()


def run_git(project, *args):
    subprocess.run(["git", "-C", str(project), *args], check=True, capture_output=True)


class Harness(npm_tests.Harness):
    """The toolchain tests' harness, with a pnpm project and a declared pnpm package."""

    def __init__(self, case, *, install=True, pin=f"pnpm@{VERSION}", lock=LOCK, extra=None, triggers=()):
        self.case = case
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-pnpm-", dir="/private/tmp" if sys.platform == "darwin" else None))
        case.addCleanup(shutil.rmtree, self.tmp, True)
        self.dist = npm_tests.distribution(self.tmp)
        (self.dist / "bin/node").write_text(NODE)
        self.pnpm = self.tmp / "pnpm-package"
        (self.pnpm / "bin").mkdir(parents=True)
        (self.pnpm / "package.json").write_text(json.dumps({"name": "pnpm", "version": VERSION}))
        native = str(Path(sys.executable).resolve())
        (self.pnpm / "bin/pnpm.cjs").write_text(PNPM.replace("VERSION", VERSION).replace("NATIVE", native)
                                                .replace("PYHOME", str(Path(sys.base_prefix).resolve() / "bin")))
        self.project = self.tmp / "project"
        self.project.mkdir()
        manifest = {"name": "p", "version": "1.0.0", "packageManager": pin,
                    "scripts": {"check": "sh ./check.sh"}, "devDependencies": {"tool": "1.0.0"}}
        manifest.update(extra or {})
        (self.project / "package.json").write_text(json.dumps(manifest, indent=2) + "\n")
        if lock is not None:
            (self.project / "pnpm-lock.yaml").write_text(lock)
        (self.project / "check.sh").write_text(CHECK)
        (self.project / ".gitignore").write_text("DeepSeekAndDestroy/\nnode_modules/\n")
        for trigger in triggers:
            (self.project / trigger).write_text("x\n")
        for argv in [("init", "-q"), ("config", "user.name", "T"), ("config", "user.email", "t@e.invalid"),
                     ("add", "."), ("commit", "-qm", "i")]:
            run_git(self.project, *argv)
        if install:
            self.install(self.project)
        home = self.tmp / "fake-home"
        (home / ".local/share/opencode").mkdir(parents=True)
        (home / ".local/share/opencode/auth.json").write_text(json.dumps(
            {"deepseek": {"type": "api", "key": "sk-proofbound-dummy-not-a-key"}}))
        self.env = {**os.environ, "HOME": str(home)}
        fake = self.tmp / "bin/opencode"
        fake.parent.mkdir()
        fake.write_text(npm_tests.FAKE_EXECUTOR.replace("PYTHON", sys.executable))
        fake.chmod(0o755)
        self.executor = fake
        self.toolchain = True

    def install(self, where):
        env = {**os.environ, "PATH": f"{self.dist / 'bin'}:{os.environ['PATH']}"}
        return subprocess.run([str(self.dist / "bin/node"), str(self.pnpm / "bin/pnpm.cjs"), "install",
                               "--frozen-lockfile", "--package-import-method", "copy"],
                              cwd=where, env=env, capture_output=True, text=True)

    def start(self):
        out = self.cli("start", "--project", self.project, "--goal", "g", "--check", "pnpm run check",
                       "--executor", self.executor, "--toolchain", self.dist, "--pnpm", self.pnpm)
        if "run" in out:
            self.run = Path(out["run"])
            self.case.addCleanup(shutil.rmtree, Path(self.config()["home"]).parent, True)
        return out


class Preparation(unittest.TestCase):
    def test_pnpm_is_prepared_pinned_and_bound_to_its_installation_inputs(self):
        h = Harness(self)
        self.assertIn("run", h.start())
        record = h.config()["toolchain"]
        manager = record["package_manager"]
        self.assertEqual((manager["name"], manager["version"]), ("pnpm", VERSION))
        prepared = Path(record["prepared"])
        self.assertEqual(manager["identity"], _toolchain.tree(prepared / pm.PNPM_PACKAGE)["digest"])
        self.assertTrue((prepared / "bin/pnpm").is_file())
        self.assertIn("not an offline install", manager["network"])
        deps = record["dependencies"]
        self.assertTrue(deps["lockfile"]["path"].endswith("pnpm-lock.yaml"))
        self.assertIn("packageManager", deps["manifest"]["fields"])
        self.assertEqual(set(deps["config_files"]), set(pm.PNPM_CONFIG_FILES))
        self.assertEqual(_toolchain.problems(h.config()), [])

    def test_unusable_pnpm_projects_are_refused_before_anything_is_created(self):
        cases = {
            "pins pnpm@9.0.0": dict(pin="pnpm@9.0.0"),
            "no pnpm-lock.yaml": dict(lock=None),
            "workspace": dict(lock=LOCK.replace("\npackages:", "\n  packages/a:\n    dependencies: {}\n\npackages:")),
            "patchedDependencies": dict(lock=LOCK + "\npatchedDependencies:\n  tool@1.0.0: patches/tool.patch\n"),
            "file: or link:": dict(lock=LOCK.replace("version: 1.0.0\n\npackages", "version: link:../tool\n\npackages")),
            "hard-linked to files outside node_modules": dict(triggers=("hardlink-store",)),
            "leave the project": dict(triggers=("escape-link",)),
            "dependencies are not installed": dict(install=False),
        }
        for words, kwargs in cases.items():
            with self.subTest(words):
                h = Harness(self, **kwargs)
                out = h.start()
                self.assertIn(words, out.get("error", ""), out)
                self.assertFalse((h.project / "DeepSeekAndDestroy").exists())

    def test_credentials_in_npmrc_and_a_missing_pnpm_declaration_are_refused(self):
        h = Harness(self)
        (h.project / ".npmrc").write_text("//registry.example/:_authToken=secret\n")
        run_git(h.project, "add", "."); run_git(h.project, "commit", "-qm", "npmrc")
        self.assertIn("registry credentials", h.start().get("error", ""))
        h2 = Harness(self)
        out = h2.cli("start", "--project", h2.project, "--goal", "g", "--check", "pnpm run check",
                     "--executor", h2.executor, "--toolchain", h2.dist)
        self.assertIn("declare the pnpm package with --pnpm", out.get("error", ""))

    def test_npm_records_keep_their_shape(self):
        h = npm_tests.Harness(self)
        h.start()
        record = h.config()["toolchain"]
        self.assertNotIn("package_manager", record)
        self.assertNotIn("config_files", record["dependencies"])
        self.assertEqual(record["dependencies"]["prepare_command"], ["npm", "ci"])


class Drift(unittest.TestCase):
    def test_installation_inputs_and_prepared_bytes_are_rechecked_before_launch_and_acceptance(self):
        import pb_workflow
        changes = {
            "lockfile": lambda h: (h.project / "pnpm-lock.yaml").write_text(LOCK + "\n"),
            "pnpm field": lambda h: (h.project / "package.json").write_text(json.dumps(
                {**json.loads((h.project / "package.json").read_text()), "pnpm": {"overrides": {"x": "1"}}})),
            "npmrc": lambda h: (h.project / ".npmrc").write_text("registry=https://example.invalid/\n"),
            "node_modules": lambda h: (h.project / "node_modules/.pnpm/tool@1.0.0/node_modules/tool/cli.sh").write_text("#!/bin/sh\necho changed\n"),
            "prepared pnpm": lambda h: (Path(h.config()["toolchain"]["prepared"]) / pm.PNPM_PACKAGE / "bin/pnpm.cjs").write_text("echo changed\n"),
        }
        for label, change in changes.items():
            with self.subTest(label):
                h = Harness(self)
                h.start()
                checked = json.loads(Path(pb_workflow.check_project(h.run, h.config())).read_text())["result"]
                self.assertIn(VERSION, checked["stdout"])            # the prepared pnpm ran the check
                self.assertIn("offline=true", checked["stdout"])
                self.assertIn("native-ran", checked["stdout"])
                change(h)
                self.assertNotEqual(_toolchain.problems(h.config()), [], label)
                with self.assertRaisesRegex(ValueError, "refused"):
                    pb_workflow.check_project(h.run, h.config())


class VerifyDelivery(unittest.TestCase):
    def delivery(self, h, adds=("new.txt", "hello")):
        from dsd_state import atomic_json
        baseline = subprocess.check_output(["git", "-C", str(h.project), "rev-parse", "HEAD"], text=True).strip()
        out = h.tmp / "delivery"
        (out / "evidence").mkdir(parents=True)
        name, line = adds
        (out / "change.patch").write_text(f"diff --git a/{name} b/{name}\nnew file mode 100644\n"
                                          f"--- /dev/null\n+++ b/{name}\n@@ -0,0 +1 @@\n+{line}\n")
        atomic_json(out / "handoff.json", {"baseline": baseline, "outcome": "accepted"})
        record = _toolchain.prepare(h.dist, h.tmp / "runtime", h.project, pnpm=h.pnpm)
        atomic_json(out / "evidence/run-config.json", {"check_command": "pnpm run check",
                                                       "paths": {"project": str(h.project)}, "toolchain": record})
        npm_tests.VerifyDelivery.seal(out)
        return out

    def verify(self, h, delivery):
        into = h.tmp / f"verify-{len(list(h.tmp.glob('verify-*')))}"
        cp = subprocess.run([sys.executable, str(CLI), "verify-delivery", "--delivery", delivery, "--into", into],
                            capture_output=True, text=True, env=h.env, timeout=300)
        return json.loads(cp.stdout), into

    def test_a_matching_candidate_is_installed_frozen_and_checked(self):
        h = Harness(self)
        got, into = self.verify(h, self.delivery(h))
        self.assertTrue(got["verified"], got)
        deps = got["dependencies"]
        self.assertEqual(deps["command"][1:3], ["install", "--frozen-lockfile"])
        self.assertEqual(deps["command"][deps["command"].index("--store-dir") + 1], str(into / "pnpm-store"))
        self.assertIn("not an offline install", deps["network"])
        self.assertTrue(deps["config_matches_prepared"])
        self.assertIn("Packages: +1", deps["stdout"])
        self.assertIn("native-ran", got["project_check"]["stdout"])
        self.assertIn("offline=true", got["project_check"]["stdout"])

    def test_mismatch_failure_and_a_store_linked_install_are_not_verified(self):
        h = Harness(self)
        delivery = self.delivery(h)
        config = json.loads((delivery / "evidence/run-config.json").read_text())
        config["toolchain"]["dependencies"]["config_files"][".npmrc"] = "0" * 64
        (delivery / "evidence/run-config.json").write_text(json.dumps(config))
        npm_tests.VerifyDelivery.seal(delivery)
        got, into = self.verify(h, delivery)
        self.assertFalse(got["verified"])
        self.assertIsNone(got["dependencies"]["returncode"])
        self.assertFalse((into / "checkout/node_modules").exists(), "refused before installation")
        for trigger, words in (("fail-install", "did not succeed"), ("hardlink-store", "hard-linked")):
            with self.subTest(trigger):
                h2 = Harness(self)
                got, _ = self.verify(h2, self.delivery(h2, adds=(trigger, "x")))
                self.assertFalse(got["verified"], got)
                self.assertIn(words, got["dependencies"]["why"])
                self.assertIsNone(got["project_check"]["passed"])


@unittest.skipUnless(sys.platform == "darwin", "the worker boundary is macOS sandbox-exec")
class Boundary(unittest.TestCase):
    def test_the_worker_runs_the_prepared_pnpm_and_cannot_change_it_or_the_dependencies(self):
        if not npm_tests.sandbox_available():
            self.skipTest("sandbox-exec cannot start inside this process")
        from test_supervision import pinned_executor
        executor = pinned_executor()
        if executor is None:
            self.skipTest("authorization needs the pinned OpenCode 1.18.29 build, not installed here")
        h = Harness(self)
        h.executor = executor
        h.start()
        h.authorize()
        tooling = h.cli("status", "--run", h.run)["project_tooling"]
        self.assertTrue(tooling["verified"], tooling)
        rc, out = h.inside("/bin/sh", "-c", "pnpm run check")
        self.assertEqual(rc, 0, out)
        self.assertIn(VERSION, out)
        # A check may stop its own workers; nothing outside the sandbox can be signalled.
        rc, out = h.inside(sys.executable, "-c", "import os, subprocess, sys; c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); c.terminate(); c.wait(); print('child stopped')\ntry:\n    os.kill(os.getppid(), 0); print('outside: allowed')\nexcept PermissionError: print('outside: refused')")
        self.assertIn("child stopped", out)
        self.assertIn("outside: refused", out)
        prepared = Path(h.config()["toolchain"]["prepared"])
        for target in (h.project / "node_modules/.pnpm/tool@1.0.0/node_modules/tool/cli.sh",
                       prepared / pm.PNPM_PACKAGE / "bin/pnpm.cjs", prepared / "bin/pnpm"):
            rc, out = h.inside("/bin/sh", "-c", f"echo x >> '{target}'")
            self.assertNotEqual(rc, 0, target)
            self.assertIn("Operation not permitted", out)
        # Tool caches the record names are writable, and leave the dependency digest unchanged;
        # a new directory beside them is not.
        rc, out = h.inside("/bin/sh", "-c", "mkdir -p node_modules/.vite-temp node_modules/.tmp && echo x > node_modules/.tmp/build.info")
        self.assertEqual(rc, 0, out)
        self.assertEqual(_toolchain.problems(h.config()), [])
        rc, out = h.inside("/bin/sh", "-c", "mkdir node_modules/.not-a-cache")
        self.assertNotEqual(rc, 0)
        rc, out = h.inside("/bin/sh", "-c", "ln -s .pnpm node_modules/.vite/escape 2>/dev/null; mkdir -p node_modules/.vite && ln -s ../.pnpm/tool@1.0.0 node_modules/.vite/link && echo x > node_modules/.vite/link/node_modules/tool/cli.sh")
        self.assertNotEqual(rc, 0, "a cache symlink does not open the installed packages to writes")


if __name__ == "__main__":
    unittest.main()

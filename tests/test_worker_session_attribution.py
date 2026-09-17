"""The session lookup must be asked from the directory the worker ran in.

`opencode session list` scopes its answer to the working directory. Asked from anywhere else it
exits 0 and prints nothing, which parses as *no sessions* rather than as an error — so the terminal
record silently lost its session id and the usage the attempt incurred could not be attributed to
the launch that incurred it.

This was not hypothetical and it was not caused by any one attempt failing: every terminal record
in the first authority demonstration, including the attempts that completed cleanly, carried
`session_id: null` with the same parse error. Accounting that did not check attribution simply did
not notice.

No provider, no network, no cost: the fake `opencode` here answers `session list` only when its own
working directory is the project root, which is exactly the behaviour being relied upon.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_worker  # noqa: E402

#: Answers `session list` with one session when run from `PB_EXPECT_DIR`, and with an empty
#: string otherwise — the real CLI's directory scoping, reduced to the part that matters here.
FAKE = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, sys
    if sys.argv[1:3] != ["session", "list"]:
        raise SystemExit(2)
    if os.path.realpath(os.getcwd()) != os.path.realpath(os.environ["PB_EXPECT_DIR"]):
        raise SystemExit(0)          # exit 0, no output: "no sessions here"
    print(json.dumps([{"id": "ses_scoped", "title": "dsd:T:role:1"}]))
''')


class SessionAttributionTest(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-session-scope-")).resolve()
        self.addCleanup(__import__("shutil").rmtree, self.tmp, True)
        self.project = self.tmp / "project"
        self.project.mkdir()
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "opencode"
        fake.write_text(FAKE, encoding="utf-8")
        fake.chmod(0o755)
        self.env = {"PATH": f"{bin_dir}{os.pathsep}/usr/bin:/bin",
                    "PB_EXPECT_DIR": str(self.project)}

    def test_the_lookup_finds_the_session_when_asked_from_the_project_root(self):
        ident, error = run_worker.lookup_session_id(self.env, "dsd:T:role:1", self.project)
        self.assertIsNone(error)
        self.assertEqual(ident, "ses_scoped")

    def test_asking_from_the_wrong_directory_loses_the_session_silently(self):
        """The defect, pinned. Not an error — an empty answer that reads as 'no sessions'."""
        ident, error = run_worker.lookup_session_id(self.env, "dsd:T:role:1", self.tmp)
        self.assertIsNone(ident)
        self.assertIn("JSON parse failed", error or "",
                      "the failure is silent enough to look like a parse problem")

    def test_the_call_site_passes_the_project_root(self):
        """A unit test on the helper proves nothing if the caller still omits the directory."""
        source = (ROOT / "scripts" / "run_worker.py").read_text(encoding="utf-8")
        self.assertIn("lookup_session_id(env, title, project_root)", source)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

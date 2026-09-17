#!/usr/bin/env python3
"""Establish that the external suite is satisfiable and discriminating. Unpaid.

Two properties, neither of which can be assumed:

* **satisfiable** — a private witness passes it, and passes the project's own suite unedited. An
  unsatisfiable suite would fail every implementer regardless of merit.
* **discriminating** — it fails the unmodified fixture, it fails the predecessor's formula (the
  defect this successor exists to resolve), and it fails one variant per requirement. A suite that
  only ever passes proves nothing.

Every variant is generated into a temporary directory and deleted. None is ever placed in the
demonstration project or shown to any worker.

    python3 demo/pb-authority-demo-2/verify_suite.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITE = HERE / "external-suite"
WITNESS = SUITE / "witness"
FIXTURE = HERE / "fixture"

BASE = (FIXTURE / "rateguard" / "__init__.py").read_text(encoding="utf-8")

#: Shared, pure refill arithmetic, appended to the fixture so each variant differs only in
#: `retry_after`. Keeps the discrimination about the requirement under test.
HELPER = '''
    def _available(self, key, now):
        tokens = self._tokens.get(key, float(self.capacity))
        last = self._last.get(key, now)
        elapsed = now - last
        if elapsed < 0.0:
            elapsed = 0.0
        tokens = tokens + elapsed * self.refill_per_second
        if tokens > self.capacity:
            tokens = float(self.capacity)
        return tokens
'''

#: Each variant breaks exactly one requirement, and the suite must notice.
VARIANTS: "dict[str, tuple[str, str]]" = {
    "predecessor-formula": ("requirement 1 — the delay must actually admit", '''
    def retry_after(self, key):
        import math
        now = self._clock()
        available = self._available(key, now)
        if available >= 1.0:
            return 0.0
        return (1.0 - available) / self.refill_per_second
'''),
    "mutating-query": ("requirement 2 — the query must change nothing", '''
    def retry_after(self, key):
        import math
        now = self._clock()
        available = self._available(key, now)
        self._tokens[key] = max(0.0, available - 0.25)
        self._last[key] = now
        if available >= 1.0:
            return 0.0
        return (1.0 - available) / self.refill_per_second
'''),
    "wastefully-generous": ("requirement 1's bound on excess delay", '''
    def retry_after(self, key):
        import math
        now = self._clock()
        available = self._available(key, now)
        if available >= 1.0:
            return 0.0
        return (1.0 - available) / self.refill_per_second + 1.0
'''),
    "always-infinite": ("requirement 1 — a finite delay exists and must be returned", '''
    def retry_after(self, key):
        import math
        now = self._clock()
        if self._available(key, now) >= 1.0:
            return 0.0
        return math.inf
'''),
    "finite-for-subnormal": ("requirement 7 — the exceptional case must answer infinity", '''
    def retry_after(self, key):
        import math
        now = self._clock()
        available = self._available(key, now)
        if available >= 1.0:
            return 0.0
        wait = (1.0 - available) / self.refill_per_second
        if not math.isfinite(wait):
            return 1e308
        for _ in range(256):
            reached = now + wait
            if not math.isfinite(reached):
                return 1e308
            if self._available(key, reached) >= 1.0:
                return wait
            target = math.nextafter(reached, math.inf)
            nxt = target - now
            if not (math.isfinite(nxt) and nxt > wait):
                nxt = math.nextafter(wait, math.inf)
            wait = nxt
        return 1e308
'''),
    "sleeps-while-answering": ("the intent's no-sleeping constraint", '''
    def retry_after(self, key):
        import math, time as _t
        _t.sleep(0.0)
        now = self._clock()
        available = self._available(key, now)
        if available >= 1.0:
            return 0.0
        wait = (1.0 - available) / self.refill_per_second
        if not math.isfinite(wait):
            return math.inf
        for _ in range(256):
            reached = now + wait
            if not math.isfinite(reached):
                return math.inf
            if self._available(key, reached) >= 1.0:
                return wait
            target = math.nextafter(reached, math.inf)
            nxt = target - now
            if not (math.isfinite(nxt) and nxt > wait):
                nxt = math.nextafter(wait, math.inf)
            wait = nxt
        return math.inf
'''),
}


def run(pythonpath: Path, start: Path) -> "tuple[bool, str]":
    done = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(start), "-t", str(start)],
        capture_output=True, text=True, check=False,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(pythonpath),
             "HOME": str(Path(tempfile.gettempdir()) / "pb-demo2-verify-home")})
    tail = (done.stderr or done.stdout).strip().splitlines()
    return done.returncode == 0, tail[-1] if tail else ""


def variant(name: str, body: str) -> Path:
    root = Path(tempfile.mkdtemp(prefix=f"pb-demo2-{name}-"))
    (root / "rateguard").mkdir()
    (root / "rateguard" / "__init__.py").write_text(BASE + HELPER + body, encoding="utf-8")
    return root


def main() -> int:
    results: "dict[str, object]" = {}

    ok, tail = run(WITNESS, SUITE)
    results["witness_passes_external_suite"] = {"passed": ok, "tail": tail}
    ok_own, tail_own = run(WITNESS, FIXTURE / "tests")
    results["witness_passes_the_projects_own_suite_unedited"] = {"passed": ok_own,
                                                                 "tail": tail_own}
    ok_fix, tail_fix = run(FIXTURE, SUITE)
    results["unmodified_fixture_fails"] = {"failed": not ok_fix, "tail": tail_fix}

    discrimination = {}
    for name, (why, body) in VARIANTS.items():
        root = variant(name, body)
        try:
            passed, tail = run(root, SUITE)
            own_passed, _ = run(root, FIXTURE / "tests")
            discrimination[name] = {"breaks": why, "external_suite_failed": not passed,
                                    "projects_own_suite_passed": own_passed, "tail": tail}
        finally:
            shutil.rmtree(root, ignore_errors=True)
    results["discrimination"] = discrimination

    print(json.dumps(results, indent=2, sort_keys=True))
    good = (results["witness_passes_external_suite"]["passed"]
            and results["witness_passes_the_projects_own_suite_unedited"]["passed"]
            and results["unmodified_fixture_fails"]["failed"]
            and all(v["external_suite_failed"] for v in discrimination.values()))
    return 0 if good else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""M0 characterization: historical worker-rules snapshots stay verifiable as the registry grows.

A worker-rules revision is immutable. Its MANIFEST.json records the exact protocol
membership and an ordered fingerprint over that membership. Verification must therefore
judge a snapshot by the protocol identity it actually recorded, never by whatever the
current protocol registry happens to contain.

These tests pin an explicit historical protocol membership on purpose. They must not be
rewritten to derive that membership from the code under test: the whole point is that a
snapshot recorded under an older, smaller registry stays verifiable, and stays adversarially
checked, after the registry grows.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable

_SCRIPTS = str(ROOT / "scripts")
sys.path.insert(0, _SCRIPTS)
try:
    from _rules_snapshot import PROTOCOL_NAMES, verify_snapshot
finally:
    sys.path.remove(_SCRIPTS)

# Deliberately pinned, deliberately a strict subset of today's registry, and deliberately
# written in the canonical relative order a historical snapshot would have used.
HISTORICAL_PROTOCOL_NAMES = (
    "COMMON.md",
    "PROOF-PATTERNS.md",
    "roles/dsd-implementer/SKILL.md",
    "roles/dsd-fixer/SKILL.md",
    "roles/dsd-reviewer/SKILL.md",
)


def fingerprint(protocol_dir: Path, names) -> str:
    h = hashlib.sha256()
    for name in names:
        path = protocol_dir / name
        h.update(name.encode("utf-8")); h.update(b"\0")
        h.update(path.read_bytes()); h.update(b"\0")
    return h.hexdigest()


def write_snapshot(
    revision_root: Path,
    names,
    *,
    fingerprint_names=None,
    fmt: str = "dsd-worker-rules-manifest-v2",
    extra: dict | None = None,
) -> Path:
    """Create one immutable-looking worker-rules revision with exactly `names` recorded."""
    revision_root.mkdir(parents=True, exist_ok=True)
    rules = revision_root / "WORKER_RULES.md"
    rules.write_text("# rules\n", encoding="utf-8")
    protocol = revision_root / "protocol"
    protocol.mkdir(exist_ok=True)
    for name in names:
        path = protocol / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name + "\n", encoding="utf-8")
    manifest = {
        "format": fmt,
        "revision": int(revision_root.name[1:]),
        "path": str(rules.resolve()),
        "sha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
        "protocol_dir": str(protocol.resolve()),
        "protocol_fingerprint": fingerprint(protocol, fingerprint_names or names),
        "protocol": {n: hashlib.sha256((protocol / n).read_bytes()).hexdigest() for n in names},
    }
    if extra:
        manifest.update(extra)
    (revision_root / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return rules


class HistoricalProtocolSnapshotTest(unittest.TestCase):
    def historical(self, root: Path, **kwargs) -> Path:
        return write_snapshot(root / "worker-rules" / "r0001", HISTORICAL_PROTOCOL_NAMES, **kwargs)

    def test_pinned_history_is_a_strict_subset_of_the_current_registry(self):
        """Guards the premise: without this, the growth tests below would be vacuous."""
        self.assertTrue(set(HISTORICAL_PROTOCOL_NAMES) < set(PROTOCOL_NAMES))

    def test_serialized_manifest_key_order_is_not_the_protocol_order(self):
        """Guards the premise of the ordering tests: sorted key order != canonical order."""
        self.assertNotEqual(sorted(HISTORICAL_PROTOCOL_NAMES), list(HISTORICAL_PROTOCOL_NAMES))

    def test_historical_snapshot_verifies_after_registry_growth(self):
        with tempfile.TemporaryDirectory() as td:
            rules = self.historical(Path(td))
            result = verify_snapshot(rules)
            self.assertEqual(set(result["protocol"]), set(HISTORICAL_PROTOCOL_NAMES))

    def test_historical_snapshot_verifies_through_check_state_call_site(self):
        """The fix must reach production call sites, not only the library helper."""
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r1"
            run.mkdir(parents=True)
            rules = self.historical(run)
            state = {
                "execution_status": "active",
                "next_action": "launch worker",
                "worker_rules": {
                    "revision": 1,
                    "path": str(rules.resolve()),
                    "sha256": hashlib.sha256(rules.read_bytes()).hexdigest(),
                },
                "worker_runtime": {"harness": "opencode-cli"},
                "phases": {},
            }
            state_path = run / "state.json"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            cp = subprocess.run(
                [PYTHON, str(ROOT / "scripts" / "check_state.py"), str(state_path)],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)

    def test_tampered_historical_protocol_content_still_fails(self):
        with tempfile.TemporaryDirectory() as td:
            rules = self.historical(Path(td))
            (rules.parent / "protocol" / "roles" / "dsd-reviewer" / "SKILL.md").write_text(
                "tampered\n", encoding="utf-8"
            )
            with self.assertRaises(ValueError) as ctx:
                verify_snapshot(rules)
            self.assertIn("changed after creation", str(ctx.exception))

    def test_tampered_worker_rules_body_still_fails(self):
        with tempfile.TemporaryDirectory() as td:
            rules = self.historical(Path(td))
            rules.write_text("# rules tampered\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_snapshot(rules)

    def test_missing_historically_recorded_protocol_still_fails(self):
        with tempfile.TemporaryDirectory() as td:
            rules = self.historical(Path(td))
            (rules.parent / "protocol" / "roles" / "dsd-fixer" / "SKILL.md").unlink()
            with self.assertRaises(ValueError) as ctx:
                verify_snapshot(rules)
            self.assertIn("incomplete", str(ctx.exception))

    def test_fingerprint_recorded_over_sorted_key_order_is_rejected(self):
        """Serialized key order must never be mistaken for the recorded protocol order."""
        with tempfile.TemporaryDirectory() as td:
            rules = self.historical(
                Path(td), fingerprint_names=sorted(HISTORICAL_PROTOCOL_NAMES)
            )
            with self.assertRaises(ValueError) as ctx:
                verify_snapshot(rules)
            self.assertIn("protocol_fingerprint differs", str(ctx.exception))

    def test_unreproducible_recorded_fingerprint_is_rejected(self):
        """Fingerprint verification is never skipped to obtain compatibility."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rules = self.historical(root)
            manifest_path = rules.parent / "MANIFEST.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["protocol_fingerprint"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                verify_snapshot(rules)
            self.assertIn("protocol_fingerprint differs", str(ctx.exception))

    def test_explicitly_recorded_protocol_order_is_authoritative(self):
        """A manifest that records its own order is verified against that order, not the registry."""
        with tempfile.TemporaryDirectory() as td:
            unusual = list(reversed(HISTORICAL_PROTOCOL_NAMES))
            rules = write_snapshot(
                Path(td) / "worker-rules" / "r0001",
                HISTORICAL_PROTOCOL_NAMES,
                fingerprint_names=unusual,
                fmt="dsd-worker-rules-manifest-v3",
                extra={"protocol_names": unusual},
            )
            result = verify_snapshot(rules)
            self.assertEqual(set(result["protocol"]), set(HISTORICAL_PROTOCOL_NAMES))

    def test_recorded_protocol_names_must_match_the_recorded_protocol_map(self):
        with tempfile.TemporaryDirectory() as td:
            names = list(HISTORICAL_PROTOCOL_NAMES)
            rules = write_snapshot(
                Path(td) / "worker-rules" / "r0001",
                HISTORICAL_PROTOCOL_NAMES,
                fmt="dsd-worker-rules-manifest-v3",
                extra={"protocol_names": names[:-1]},
            )
            with self.assertRaises(ValueError) as ctx:
                verify_snapshot(rules)
            self.assertIn("protocol_names", str(ctx.exception))

    def test_unknown_manifest_format_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            rules = self.historical(Path(td), fmt="dsd-worker-rules-manifest-v9")
            with self.assertRaises(ValueError) as ctx:
                verify_snapshot(rules)
            self.assertIn("unsupported worker-rules manifest format", str(ctx.exception))

    def test_role_absent_from_a_historical_snapshot_cannot_launch(self):
        """The compensating control for verification being membership-based.

        Verification now accepts a snapshot recording fewer protocol files than the current
        registry. What keeps that safe is that launch authority is resolved from the exact
        snapshot: a role added after the snapshot was frozen has no protocol file in it and
        must fail loudly rather than launch with missing authority.
        """
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r1"
            run.mkdir(parents=True)
            rules = self.historical(run)
            task = run / "task.md"
            task.write_text("# Task T\nContract revision: r0001\n\n## Objective\nX.\n", encoding="utf-8")

            def render(role: str, report_name: str):
                return subprocess.run(
                    [PYTHON, str(ROOT / "scripts" / "render_worker_prompt.py"),
                     "--role", role, "--task-id", "T", "--run-root", str(run.resolve()),
                     "--worker-rules", str(rules.resolve()), "--task", str(task.resolve()),
                     "--report", str((run / report_name).resolve())],
                    text=True, capture_output=True, check=False,
                )

            # A role the snapshot actually recorded still launches.
            recorded = render("reviewer", "recorded.md")
            self.assertEqual(recorded.returncode, 0, recorded.stdout + recorded.stderr)

            # A role the current registry has but this snapshot predates must not.
            absent = next(
                name for name in PROTOCOL_NAMES
                if name.startswith("roles/") and name not in HISTORICAL_PROTOCOL_NAMES
            )
            role = absent.split("/")[1][len("dsd-"):]
            later = render(role, "later.md")
            self.assertNotEqual(later.returncode, 0)
            self.assertIn("missing launch authority", later.stderr)

    def test_historical_revision_can_still_be_reused(self):
        """`--reuse-existing` must judge an existing revision by its own manifest."""
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"
            run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r1"
            run.mkdir(parents=True)
            plan = project / "PLAN.md"
            plan.write_text("plan\n", encoding="utf-8")
            self.historical(run)
            cp = subprocess.run(
                [PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                 "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                 "--plan", str(plan.resolve()), "--reuse-existing"],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertEqual(set(json.loads(cp.stdout)["protocol"]), set(HISTORICAL_PROTOCOL_NAMES))

    def test_reuse_of_a_tampered_historical_revision_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"
            run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r1"
            run.mkdir(parents=True)
            plan = project / "PLAN.md"
            plan.write_text("plan\n", encoding="utf-8")
            rules = self.historical(run)
            (rules.parent / "protocol" / "COMMON.md").write_text("tampered\n", encoding="utf-8")
            cp = subprocess.run(
                [PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                 "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                 "--plan", str(plan.resolve()), "--reuse-existing"],
                text=True, capture_output=True, check=False,
            )
            self.assertNotEqual(cp.returncode, 0)
            self.assertIn("changed after creation", cp.stderr)

    def test_newly_created_snapshot_round_trips_and_records_its_own_order(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"
            run = project / "DeepSeekAndDestroy" / "plans" / "p" / "runs" / "r1"
            run.mkdir(parents=True)
            plan = project / "PLAN.md"
            plan.write_text("plan\n", encoding="utf-8")
            cp = subprocess.run(
                [PYTHON, str(ROOT / "scripts" / "prepare_worker_rules.py"),
                 "--project-root", str(project.resolve()), "--run-root", str(run.resolve()),
                 "--plan", str(plan.resolve())],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            rules = run / "worker-rules" / "r0001" / "WORKER_RULES.md"
            verify_snapshot(rules)
            manifest = json.loads((rules.parent / "MANIFEST.json").read_text(encoding="utf-8"))
            recorded_order = manifest.get("protocol_names")
            self.assertIsInstance(recorded_order, list)
            self.assertEqual(set(recorded_order), set(manifest["protocol"]))
            self.assertEqual(
                manifest["protocol_fingerprint"],
                fingerprint(rules.parent / "protocol", recorded_order),
            )


if __name__ == "__main__":
    unittest.main()

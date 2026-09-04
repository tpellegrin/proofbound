"""Characterization of Proofbound textual artifact identity.

Artifact identity is a wire format. These tests pin the exact algorithm, because the
ledger records identities that must still mean the same thing years from now, on a
different operating system, under a different `core.autocrlf`.

The rule being characterized:

    strict UTF-8 decode -> replace CRLF with LF -> encode UTF-8 -> SHA-256

Nothing else is normalized. Whitespace, wording, blank lines and Unicode code points
are all content. A lone CR is content too (see the dedicated test for why).
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from _artifact_identity import (  # noqa: E402
    ARTIFACT_IDENTITY_FORMAT,
    ArtifactIdentityError,
    artifact_identity,
    artifact_identity_file,
    canonical_text_bytes,
)


class ArtifactIdentityTest(unittest.TestCase):
    maxDiff = None

    def write(self, stack, raw: bytes) -> Path:
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        path = root / "artifact.md"
        path.write_bytes(raw)
        return path

    # ---------- the versioned wire format ----------

    def test_format_tag_is_pinned(self):
        self.assertEqual(ARTIFACT_IDENTITY_FORMAT, "proofbound-artifact-text-v1")

    def test_identity_is_plain_sha256_of_the_lf_normalized_utf8_bytes(self):
        """A human with sha256sum and an LF checkout can reproduce the ledger value.

        This is deliberate: the identity is not salted or domain-separated, so the
        ledger stays independently checkable with ordinary tools. Version confusion is
        prevented by the ledger's explicit `artifact_identity` field, not by the digest.
        """
        text = b"# Proposal\n\nProblem, scope, non-goals.\n"
        self.assertEqual(artifact_identity(text), hashlib.sha256(text).hexdigest())

    def test_identity_is_deterministic_across_repeated_hashing(self):
        raw = b"# Design\n\n- one\n- two\n"
        first = artifact_identity(raw)
        for _ in range(5):
            self.assertEqual(artifact_identity(raw), first)

    # ---------- line endings: the invariant that justifies canonicalization ----------

    def test_lf_and_crlf_checkouts_of_the_same_text_share_one_identity(self):
        lf = b"# Proposal\n\nProblem, scope, non-goals.\n"
        crlf = b"# Proposal\r\n\r\nProblem, scope, non-goals.\r\n"
        self.assertNotEqual(lf, crlf, "fixture is not exercising the normalization")
        self.assertEqual(artifact_identity(lf), artifact_identity(crlf))

    def test_mixed_line_endings_normalize_to_the_same_identity(self):
        mixed = b"# Proposal\r\n\nProblem.\r\n"
        self.assertEqual(artifact_identity(mixed), artifact_identity(b"# Proposal\n\nProblem.\n"))

    def test_lone_cr_is_content_not_a_line_ending(self):
        """Deliberate limit, aligned with Git's own `text` normalization.

        Git converts CRLF to LF on commit and never rewrites a lone CR. Normalizing CR
        here would make Proofbound identity disagree with Git about which files are "the
        same text", and no checkout configuration on any supported platform produces
        lone-CR files anyway. So there is no invariant to justify the extra normalization,
        and over-normalizing would silently erase real content.
        """
        self.assertNotEqual(artifact_identity(b"a\rb\n"), artifact_identity(b"a\nb\n"))

    def test_a_trailing_newline_is_content(self):
        self.assertNotEqual(artifact_identity(b"text"), artifact_identity(b"text\n"))

    # ---------- what else changes identity ----------

    def test_content_change_changes_identity(self):
        self.assertNotEqual(artifact_identity(b"scope: A\n"), artifact_identity(b"scope: B\n"))

    def test_whitespace_change_changes_identity(self):
        self.assertNotEqual(artifact_identity(b"- one\n"), artifact_identity(b"-  one\n"))

    def test_extra_blank_line_changes_identity(self):
        self.assertNotEqual(artifact_identity(b"a\nb\n"), artifact_identity(b"a\n\nb\n"))

    def test_unicode_code_points_are_preserved_and_significant(self):
        # No Unicode normalization: precomposed and decomposed forms stay distinct.
        precomposed = "caf\u00e9\n".encode("utf-8")   # e-acute as one code point
        decomposed = "cafe\u0301\n".encode("utf-8")   # e + combining acute
        self.assertNotEqual(artifact_identity(precomposed), artifact_identity(decomposed))

    def test_utf8_multibyte_content_round_trips(self):
        raw = "# Propósito\n\n— em português, com acentuação.\n".encode("utf-8")
        self.assertEqual(canonical_text_bytes(raw), raw)

    def test_a_utf8_bom_is_a_code_point_and_changes_identity(self):
        """Explicit rather than magical: the BOM decodes to U+FEFF and is preserved."""
        self.assertNotEqual(artifact_identity(b"\xef\xbb\xbftext\n"), artifact_identity(b"text\n"))

    # ---------- malformed input fails rather than being guessed ----------

    def test_non_utf8_bytes_fail_closed(self):
        with self.assertRaises(ArtifactIdentityError) as caught:
            artifact_identity(b"\xff\xfe not utf-8 \x80\n")
        self.assertIn("UTF-8", str(caught.exception))

    def test_latin1_text_is_rejected_rather_than_reinterpreted(self):
        with self.assertRaises(ArtifactIdentityError):
            artifact_identity("caf\u00e9\n".encode("latin-1"))

    def test_empty_artifact_has_a_defined_identity(self):
        self.assertEqual(artifact_identity(b""), hashlib.sha256(b"").hexdigest())

    # ---------- file reads never delegate newline handling to the platform ----------

    def test_file_identity_reads_bytes_not_platform_text(self):
        import contextlib

        with contextlib.ExitStack() as stack:
            crlf = self.write(stack, b"# Proposal\r\nBody.\r\n")
            self.assertEqual(artifact_identity_file(crlf), artifact_identity(b"# Proposal\nBody.\n"))

    def test_missing_file_fails_closed(self):
        import contextlib

        with contextlib.ExitStack() as stack:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            with self.assertRaises(ArtifactIdentityError):
                artifact_identity_file(root / "absent.md")

    def test_directory_is_not_an_artifact(self):
        import contextlib

        with contextlib.ExitStack() as stack:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            with self.assertRaises(ArtifactIdentityError):
                artifact_identity_file(root)

    # ---------- the identity survives a real Git round trip ----------

    def test_identity_survives_a_git_checkout_that_rewrites_line_endings(self):
        """The invariant in practice: `core.autocrlf` must not move artifact identity."""
        import contextlib

        def sh(*cmd, cwd):
            return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)

        with contextlib.ExitStack() as stack:
            root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            origin, clone = root / "origin", root / "clone"
            origin.mkdir()
            sh("git", "init", "-q", cwd=origin)
            sh("git", "config", "user.email", "t@test.invalid", cwd=origin)
            sh("git", "config", "user.name", "T", cwd=origin)
            (origin / ".gitattributes").write_bytes(b"*.md text eol=lf\n")
            (origin / "a.md").write_bytes(b"# Proposal\nBody.\n")
            sh("git", "add", "-A", cwd=origin)
            sh("git", "commit", "-qm", "base", cwd=origin)
            committed = artifact_identity_file(origin / "a.md")

            # A Windows-style checkout: Git materializes CRLF in the working tree.
            sh("git", "clone", "-q", str(origin), str(clone), cwd=root)
            sh("git", "config", "core.autocrlf", "true", cwd=clone)
            sh("git", "checkout", "--", ".", cwd=clone)
            sh("rm", "-f", str(clone / "a.md"), cwd=clone)
            sh("git", "checkout", "--", "a.md", cwd=clone)

            self.assertEqual(artifact_identity_file(clone / "a.md"), committed)


if __name__ == "__main__":
    unittest.main()

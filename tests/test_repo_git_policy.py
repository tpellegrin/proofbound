"""Proofbound Git authorship policy, enforced mechanically.

Policy: an AI agent may draft commit text, but may never claim ownership of the result.
No agent identity may appear as Git author, Git committer, or in an authorship trailer
(`Co-authored-by`, `On-behalf-of`, and equivalents). See AGENTS.md.

Deliberately *not* enforced here: that a particular human authored every commit. Proofbound
may accept human contributors later, and pinning one identity forever would have to be undone.
The repository-local `user.name`/`user.email` cover the current single-owner phase.

This is a denylist of known agent identities, so it is best-effort by construction: it catches
the trailers real harnesses emit, not every conceivable spelling. It is a backstop for the
repository-scope harness settings, not a substitute for them.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Vendor, model, and agent-runtime markers. Matched case-insensitively, and only against
# identity fields and attribution-trailer values -- never against free commit prose, because
# describing AI assistance in a commit body is explicitly allowed.
AGENT_MARKERS = (
    "claude", "anthropic", "chatgpt", "openai", "gpt-4", "gpt-5", "codex", "copilot",
    "gemini", "bard", "deepseek", "opencode", "kilo code", "cursor", "devin", "aider",
    "windsurf", "llm", "ai assistant", "bot@", "noreply@google.com",
)

# Trailers that assert authorship or ownership. `Signed-off-by` is a human DCO sign-off and is
# not an ownership claim, but an agent must not sign one either, so it is included.
ATTRIBUTION_TRAILER = re.compile(
    r"^\s*(co-authored-by|on-behalf-of|co-committed-by|signed-off-by)\s*:\s*(?P<value>.*)$",
    re.IGNORECASE | re.MULTILINE,
)

SEP = "\x1e"
FIELD = "\x1f"


def agent_marker(text: str) -> str | None:
    lowered = (text or "").lower()
    for marker in AGENT_MARKERS:
        if marker in lowered:
            return marker
    return None


def attribution_violations(author: str, committer: str, message: str) -> list[str]:
    """Pure policy predicate. Returns one string per violation; empty means compliant."""
    problems: list[str] = []
    for label, identity in (("author", author), ("committer", committer)):
        marker = agent_marker(identity)
        if marker:
            problems.append(f"{label} identity names an agent ({marker!r}): {identity}")
    for match in ATTRIBUTION_TRAILER.finditer(message or ""):
        value = match.group("value").strip()
        marker = agent_marker(value)
        if marker:
            trailer = match.group(1)
            problems.append(f"{trailer} trailer names an agent ({marker!r}): {value}")
    return problems


class AttributionPredicateTest(unittest.TestCase):
    """Proves the predicate against synthetic input, independent of real history."""

    HUMAN = "tpellegrin <tgpellegrin@gmail.com>"

    def test_ordinary_commit_is_compliant(self):
        self.assertEqual(attribution_violations(
            self.HUMAN, self.HUMAN,
            "fix: verify snapshots against recorded protocol identity\n\nRewrites the check.\n",
        ), [])

    def test_commit_may_describe_ai_assistance_in_prose(self):
        """Generating the text is allowed; only claiming ownership is not."""
        self.assertEqual(attribution_violations(
            self.HUMAN, self.HUMAN,
            "docs: record the reflection design\n\nDrafted with an AI coding agent; the\n"
            "architecture decisions and review are the author's.\n",
        ), [])

    def test_agent_co_authored_by_trailer_is_rejected(self):
        problems = attribution_violations(
            self.HUMAN, self.HUMAN,
            "feat: add roles\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n",
        )
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("co-authored-by", problems[0].lower())

    def test_other_vendors_are_rejected_too(self):
        for trailer in (
            "Co-authored-by: Codex <noreply@openai.com>",
            "Co-authored-by: Gemini <bot@google.com>",
            "On-behalf-of: DeepSeek Coder <agent@example.invalid>",
            "Co-authored-by: GitHub Copilot <copilot@github.com>",
        ):
            with self.subTest(trailer=trailer):
                self.assertTrue(attribution_violations(self.HUMAN, self.HUMAN, f"x\n\n{trailer}\n"))

    def test_human_co_author_is_allowed(self):
        self.assertEqual(attribution_violations(
            self.HUMAN, self.HUMAN,
            "feat: pair work\n\nCo-authored-by: A Colleague <colleague@example.com>\n",
        ), [])

    def test_agent_as_author_or_committer_is_rejected(self):
        agent = "Claude <noreply@anthropic.com>"
        self.assertTrue(attribution_violations(agent, self.HUMAN, "x"))
        self.assertTrue(attribution_violations(self.HUMAN, agent, "x"))


class RepositoryHistoryTest(unittest.TestCase):
    """Applies the predicate to this repository's actual commit objects."""

    def history(self):
        if shutil.which("git") is None:
            self.skipTest("git is not available")
        probe = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--git-dir"],
                               capture_output=True, text=True, check=False)
        if probe.returncode != 0:
            self.skipTest("not a git checkout")
        fmt = f"%H{FIELD}%an <%ae>{FIELD}%cn <%ce>{FIELD}%B{SEP}"
        cp = subprocess.run(["git", "-C", str(ROOT), "log", "--format=" + fmt],
                            capture_output=True, text=True, check=False)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        for record in cp.stdout.split(SEP):
            if not record.strip():
                continue
            sha, author, committer, message = record.lstrip("\n").split(FIELD, 3)
            yield sha, author, committer, message

    def test_no_commit_claims_agent_authorship(self):
        # A shallow clone only exposes the commits it fetched; CI uses fetch-depth: 0 so the
        # whole history is checked there.
        failures = []
        commits = 0
        for sha, author, committer, message in self.history():
            commits += 1
            for problem in attribution_violations(author, committer, message):
                failures.append(f"{sha[:10]}: {problem}")
        self.assertGreater(commits, 0, "no commits were inspected")
        self.assertEqual(failures, [], "AI attribution found in Git history:\n" + "\n".join(failures))


if __name__ == "__main__":
    unittest.main()

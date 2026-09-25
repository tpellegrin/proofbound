"""GitHub and Git remote operations for the draft-PR handoff: the only module that talks to a remote.

Everything runs on the coordinator host with the owner's existing `gh` and Git credentials. Nothing
here reaches the worker boundary, and nothing here changes credential configuration.

- **Reads** go through `gh api` (a real authenticated request, not `gh auth status`) and
  `git ls-remote`.
- **The two writes** are a single non-forced push of one commit to one new branch, and one
  `gh pr create --draft` with every argument explicit. `--dry-run` is never used: GitHub documents
  that it may push.
- **Never:** no merge, approval, ready-for-review, fork, reviewer request, branch deletion, account
  switch or login. Tokens are never read or printed.

Every command is an argument list. Multiline text goes through a file.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any

PR_FIELDS = ("number,url,state,isDraft,baseRefName,baseRefOid,headRefName,headRefOid,"
             "isCrossRepository,title")
#: GitHub's own check states, grouped without judging them. `stale`, `neutral` and
#: `action_required` stay distinct from pass and fail.
CHECK_GROUPS = {
    ("completed", "success"): "passed", ("completed", "failure"): "failed",
    ("completed", "timed_out"): "failed", ("completed", "startup_failure"): "failed",
    ("completed", "cancelled"): "cancelled", ("completed", "skipped"): "skipped",
    ("completed", "neutral"): "neutral", ("completed", "stale"): "stale",
    ("completed", "action_required"): "action_required",
}
STATUS_GROUPS = {"success": "passed", "failure": "failed", "error": "failed", "pending": "pending"}


class RemoteError(ValueError):
    """A remote command failed; the message carries the command's own error text."""


class GitHub:
    def __init__(self, gh: str = "gh", host: str = "github.com"):
        self.gh, self.host = gh, host

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        env = {**os.environ, "GH_PROMPT_DISABLED": "1", "GH_NO_UPDATE_NOTIFIER": "1",
               "NO_COLOR": "1", "GH_PAGER": "cat", "PAGER": "cat"}
        try:
            return subprocess.run([self.gh, *args], capture_output=True, text=True, env=env,
                                  stdin=subprocess.DEVNULL, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RemoteError(f"{self.gh} {args[0]} could not run: {exc}") from exc

    def _json(self, *args: str) -> Any:
        cp = self._run(*args)
        if cp.returncode != 0:
            raise RemoteError(f"gh {' '.join(args[:2])} failed: {(cp.stderr or cp.stdout).strip()[-400:]}")
        try:
            return json.loads(cp.stdout or "null")
        except ValueError as exc:
            raise RemoteError(f"gh {' '.join(args[:2])} returned no JSON") from exc

    def api(self, path: str) -> Any:
        """One read-only REST request (GET)."""
        return self._json("api", "--method", "GET", "--hostname", self.host, path)

    def login(self) -> str:
        """The account an authenticated request actually runs as."""
        user = self.api("user")
        if not isinstance(user, dict) or not user.get("login"):
            raise RemoteError("GitHub did not identify the authenticated account")
        return user["login"]

    def repository(self, repo: str) -> dict[str, Any]:
        r = self.api(f"repos/{repo}")
        return {"id": r.get("id"), "full_name": r.get("full_name"), "private": r.get("private"),
                "visibility": r.get("visibility") or ("private" if r.get("private") else "public"),
                "default_branch": r.get("default_branch"), "html_url": r.get("html_url"),
                "clone_url": r.get("clone_url"), "ssh_url": r.get("ssh_url"),
                "can_push": (r.get("permissions") or {}).get("push")}

    def git_protocol(self) -> str:
        cp = self._run("config", "get", "git_protocol", "--host", self.host)
        return (cp.stdout.strip() or "https") if cp.returncode == 0 else "https"

    def pulls_for_head(self, repo: str, head: str) -> list[dict[str, Any]]:
        """Every PR, in any state, whose head branch has this name (same or other repository)."""
        return self._json("pr", "list", "--repo", repo, "--head", head, "--state", "all",
                          "--limit", "50", "--json", PR_FIELDS)

    def pull(self, repo: str, number: int) -> dict[str, Any]:
        return self._json("pr", "view", str(number), "--repo", repo, "--json", PR_FIELDS)

    def create_draft(self, repo: str, base: str, head: str, title: str, body_file: Path,
                     cwd: Path) -> subprocess.CompletedProcess:
        """The one PR-creating call. `--head` names an already-pushed branch, so gh pushes nothing."""
        return subprocess.run(
            [self.gh, "pr", "create", "--repo", repo, "--base", base, "--head", head,
             "--title", title, "--body-file", str(body_file), "--draft"],
            capture_output=True, text=True, cwd=cwd, stdin=subprocess.DEVNULL, timeout=120,
            env={**os.environ, "GH_PROMPT_DISABLED": "1", "GH_NO_UPDATE_NOTIFIER": "1", "NO_COLOR": "1"})

    def checks(self, repo: str, sha: str) -> dict[str, Any]:
        """Check runs and commit statuses reported for exactly this commit, grouped as GitHub
        reports them. `unavailable` when they cannot be read; `none observed` when there are none.
        """
        from datetime import datetime, timezone
        observed = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        try:
            runs = self.api(f"repos/{repo}/commits/{sha}/check-runs?per_page=100")
            statuses = self.api(f"repos/{repo}/commits/{sha}/status")
        except RemoteError as exc:
            return {"sha": sha, "observed_at": observed, "state": "status unavailable", "why": str(exc)}
        items = []
        for run in (runs or {}).get("check_runs", []):
            if run.get("head_sha") not in (None, sha):
                continue
            group = ("pending" if run.get("status") != "completed"
                     else CHECK_GROUPS.get((run.get("status"), run.get("conclusion")), "unrecognized"))
            items.append({"kind": "check-run", "name": run.get("name"), "group": group,
                          "status": run.get("status"), "conclusion": run.get("conclusion"),
                          "completed_at": run.get("completed_at"), "url": run.get("html_url")})
        for st in (statuses or {}).get("statuses", []):
            items.append({"kind": "commit-status", "name": st.get("context"),
                          "group": STATUS_GROUPS.get(st.get("state"), "unrecognized"),
                          "status": st.get("state"), "url": st.get("target_url")})
        counts: dict[str, int] = {}
        for item in items:
            counts[item["group"]] = counts.get(item["group"], 0) + 1
        return {"sha": sha, "observed_at": observed,
                "state": "no checks observed" if not items else "observed",
                "counts": counts, "items": items, "workflow_runs": self.workflow_runs(repo, sha)}

    def workflow_runs(self, repo: str, sha: str) -> Any:
        """Actions runs for this head commit, by triggering event. A `push` run checked the branch
        head; a `pull_request` run checked GitHub's synthetic merge of the head into the base
        (`refs/pull/N/merge`). Both report against the head commit, so the event is what keeps
        them apart."""
        try:
            data = self.api(f"repos/{repo}/actions/runs?head_sha={sha}&per_page=50")
        except RemoteError as exc:
            return f"unavailable: {exc}"
        tested = {"push": "branch head", "pull_request": "pull-request merge ref"}
        return [{"name": r.get("name"), "event": r.get("event"),
                 "tested": tested.get(r.get("event"), r.get("event")),
                 "status": r.get("status"), "conclusion": r.get("conclusion"),
                 "attempt": r.get("run_attempt"), "url": r.get("html_url")}
                for r in (data or {}).get("workflow_runs", []) if r.get("head_sha") in (None, sha)]


def ls_remote(url: str, *branches: str) -> dict[str, str]:
    """The current commit of each named branch on the remote; an absent branch is absent."""
    refs = [f"refs/heads/{b}" for b in branches]
    cp = subprocess.run(["git", "ls-remote", "--", url, *refs], capture_output=True, text=True,
                        stdin=subprocess.DEVNULL, timeout=120)
    if cp.returncode != 0:
        raise RemoteError(f"git ls-remote failed: {cp.stderr.strip()[-400:]}")
    out = {}
    for line in cp.stdout.splitlines():
        sha, ref = line.split("\t", 1)
        out[ref.removeprefix("refs/heads/")] = sha
    return out


def push_new_branch(repo: Path, url: str, commit: str, branch: str) -> subprocess.CompletedProcess:
    """Push one commit to a branch that does not exist yet. No force: an existing branch that is
    not this commit makes the push fail, and nothing is overwritten."""
    return subprocess.run(["git", "-C", str(repo), "push", "--porcelain", "--", url,
                           f"{commit}:refs/heads/{branch}"],
                          capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300)

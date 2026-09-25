"""The concrete Git candidate for a sealed delivery: built, identified and bound to its verification.

A delivery is a patch against a recorded baseline. Its reviewable form is a Git commit. The commit's
tree is the only identity that covers content, file modes, deletions, binary files and symlinks
together, so verification and preparation both reduce the patched checkout to that tree:
- **verification** applies the sealed patch to a fresh baseline checkout with `git apply --index`
  and records the tree before any check runs, then records what the checks left behind;
- **preparation** applies the same sealed patch in a new, isolated clone and must reach the same
  tree. Nothing is copied from a worker's or coordinator's working tree.

Python establishes identity here, never quality (`P1`): a matching tree says the bytes are the bytes
that were verified, not that they are good. Digests establish integrity, not authority (`P5`).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

#: Trailers that would claim authorship or ownership for an agent. Git history is human ownership
#: (AGENTS.md); AI provenance belongs in the pull-request description instead.
FORBIDDEN_TRAILER = re.compile(r"(?im)^\s*(co-authored-by|on-behalf-of|claude-session)\s*:")


class CandidateError(ValueError):
    """The delivery, its verification or the candidate cannot be shown to be the same bytes."""


def _git(*args: str, cwd: "Path | None" = None, env: "dict[str, str] | None" = None,
         check: bool = True, text: bool = True) -> subprocess.CompletedProcess:
    cp = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=text,
                        env={**os.environ, **(env or {})}, stdin=subprocess.DEVNULL)
    if check and cp.returncode != 0:
        err = cp.stderr if text else cp.stderr.decode(errors="replace")
        raise CandidateError(f"git {args[0]} failed: {err.strip()[-600:]}")
    return cp


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def index_tree(checkout: Path) -> str:
    """The tree of the checkout's index: after `git apply --index`, exactly the patched content."""
    return _git("write-tree", cwd=checkout).stdout.strip()


def content_after_checks(checkout: Path, tree: str) -> dict[str, Any]:
    """What the checks left in tracked or unignored content, compared with the verified tree.

    Uses a temporary index, so the checkout's own index is untouched. Ignored files (build output,
    installed dependencies) are not content; an unignored generated file is, and is reported.
    """
    with tempfile.TemporaryDirectory(prefix="pb-index-") as tmp:
        env = {"GIT_INDEX_FILE": str(Path(tmp) / "index")}
        _git("read-tree", tree, cwd=checkout, env=env)
        _git("add", "-A", cwd=checkout, env=env)
        after = _git("write-tree", cwd=checkout, env=env).stdout.strip()
    changed = [] if after == tree else _git("diff-tree", "-r", "--name-status", "--no-renames",
                                            tree, after, cwd=checkout).stdout.splitlines()
    return {"tree": after, "unchanged": after == tree, "changed": changed[:50],
            "changed_count": len(changed)}


def verifier_identity(root: Path) -> dict[str, Any]:
    """The Proofbound revision that produced a verification, as far as Git can say."""
    head = _git("rev-parse", "HEAD", cwd=root, check=False)
    tree = _git("rev-parse", "HEAD:scripts", cwd=root, check=False)
    dirty = _git("status", "--porcelain", "--", "scripts", cwd=root, check=False)
    return {"proofbound_commit": head.stdout.strip() if head.returncode == 0 else None,
            "scripts_tree": tree.stdout.strip() if tree.returncode == 0 else None,
            "scripts_modified": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None}


# ---------------------------------------------------------------- delivery and verification

def check_delivery(delivery: Path) -> dict[str, Any]:
    """A sealed, accepted delivery whose files all match its manifest. Refuses anything else."""
    delivery = Path(delivery).resolve()
    manifest_path = delivery / "manifest.json"
    if not manifest_path.is_file():
        raise CandidateError(f"{delivery} has no manifest.json; it is not a sealed delivery")
    manifest = json.loads(manifest_path.read_text())
    altered = sorted(rel for rel, sha in manifest.items()
                     if not (delivery / rel).is_file() or sha256(delivery / rel) != sha)
    unlisted = sorted(str(p.relative_to(delivery)) for p in delivery.rglob("*")
                      if p.is_file() and p.name != "manifest.json"
                      and str(p.relative_to(delivery)) not in manifest)
    if altered or unlisted:
        raise CandidateError(f"the delivery no longer matches its manifest: altered {altered}, "
                             f"unlisted {unlisted}")
    handoff = json.loads((delivery / "handoff.json").read_text())
    if handoff.get("outcome") != "accepted" or not (delivery / "change.patch").is_file():
        raise CandidateError("only an accepted delivery (change.patch) can become a pull-request "
                             f"candidate; this one is {handoff.get('outcome')!r}")
    config = json.loads((delivery / "evidence" / "run-config.json").read_text())
    goal = Path(config.get("goal", ""))
    return {"path": str(delivery), "manifest_sha256": sha256(manifest_path),
            "patch": str(delivery / "change.patch"), "patch_sha256": sha256(delivery / "change.patch"),
            "baseline": handoff["baseline"], "outcome": handoff["outcome"],
            "change": goal.parent.name or None,
            "run": Path(config.get("paths", {}).get("run_root", "")).name or None,
            "project": config.get("paths", {}).get("project"),
            "check_command": config.get("check_command")}


def check_verification(path: Path, delivery: dict[str, Any]) -> dict[str, Any]:
    """Bind a verification record to this delivery, by identity rather than by a detached flag."""
    path = Path(path).resolve()
    v = json.loads(path.read_text())
    problems = []
    if v.get("verified") is not True:
        problems.append("the verification did not verify")
    if (v.get("patch") or {}).get("sha256") != delivery["patch_sha256"]:
        problems.append("the verification is of a different patch")
    if v.get("manifest_sha256") is None:
        problems.append("the verification predates manifest and candidate-tree identity; run "
                        "verify-delivery again with this version")
    elif v["manifest_sha256"] != delivery["manifest_sha256"]:
        problems.append("the verification is of a different delivery manifest")
    if v.get("baseline") != delivery["baseline"]:
        problems.append("the verification used a different baseline")
    if v.get("manifest_altered") or v.get("manifest_unlisted"):
        problems.append("the verification saw an altered delivery")
    if not v.get("candidate_tree"):
        problems.append("the verification records no candidate tree; run verify-delivery again")
    after = v.get("tracked_content_after_checks") or {}
    if v.get("candidate_tree") and after.get("unchanged") is not True:
        problems.append("the checks changed tracked or unignored content "
                        f"({after.get('changed_count')} paths), so the verified bytes are not the "
                        "published bytes; fix the checks or the ignore rules and verify again")
    if not (v.get("verifier") or {}).get("scripts_tree"):
        problems.append("the verification does not identify its verifier")
    if problems:
        raise CandidateError("verification cannot be bound to this delivery: " + "; ".join(problems))
    return {"path": str(path), "sha256": sha256(path), "verified_at": v.get("verified_at"),
            "candidate_tree": v["candidate_tree"], "verifier": v["verifier"],
            "project_check": {k: (v.get("project_check") or {}).get(k)
                              for k in ("command", "returncode", "passed")},
            "dependencies": {k: (v.get("dependencies") or {}).get(k)
                             for k in ("returncode", "matches_prepared")} if v.get("dependencies") else None,
            "outcome_check": {k: (v.get("outcome_check") or {}).get(k)
                              for k in ("returncode", "passed")} if v.get("outcome_check") else None,
            "accounting": {k: (v.get("accounting") or {}).get(k)
                           for k in ("available", "derived_recomputes", "usage_recomputes")}}


# ---------------------------------------------------------------- the candidate commit

def human_identity(source: Path) -> dict[str, str]:
    """The repository's effective human Git identity, read and never changed."""
    name = _git("config", "user.name", cwd=source, check=False).stdout.strip()
    email = _git("config", "user.email", cwd=source, check=False).stdout.strip()
    if not name or not email:
        raise CandidateError(f"{source} has no Git user.name/user.email; configure the repository's "
                             "human identity (Proofbound never sets it)")
    return {"name": name, "email": email}


def build(delivery: dict[str, Any], verification: dict[str, Any], source: Path, into: Path, *,
          message: str, identity: dict[str, str], date: str) -> dict[str, Any]:
    """Build the candidate commit in a new clone under `into`, from the sealed patch only.

    The clone shares no object store with `source` (`--no-hardlinks`), so later changes to the
    source repository cannot change the candidate. The commit is deterministic for the same patch,
    baseline, identity, message and date.
    """
    if FORBIDDEN_TRAILER.search(message):
        raise CandidateError("the commit message carries an authorship trailer for an agent; AI "
                             "provenance belongs in the pull-request description")
    repo = Path(into) / "candidate"
    _git("clone", "--quiet", "--no-hardlinks", "--no-checkout", str(source), str(repo))
    _git("checkout", "--quiet", "--detach", delivery["baseline"], cwd=repo)
    _git("apply", "--binary", "--index", delivery["patch"], cwd=repo)
    tree = index_tree(repo)
    if tree != verification["candidate_tree"]:
        raise CandidateError(f"the sealed patch on the baseline gives tree {tree}, but the "
                             f"verification recorded {verification['candidate_tree']}")
    msg = Path(into) / "commit-message.txt"
    msg.write_text(message.rstrip("\n") + "\n")
    env = {"GIT_AUTHOR_NAME": identity["name"], "GIT_AUTHOR_EMAIL": identity["email"],
           "GIT_COMMITTER_NAME": identity["name"], "GIT_COMMITTER_EMAIL": identity["email"],
           "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    commit = _git("commit-tree", tree, "-p", delivery["baseline"], "-F", str(msg),
                  cwd=repo, env=env).stdout.strip()
    _git("update-ref", "refs/proofbound/candidate", commit, cwd=repo)
    return {"repository": str(repo), "commit": commit, "tree": tree, "parent": delivery["baseline"],
            "author": identity, "date": date, "files": changed_files(repo, delivery["baseline"], commit),
            "diffstat": _git("diff", "--stat=200", delivery["baseline"], commit, cwd=repo).stdout}


def changed_files(repo: Path, base: str, commit: str) -> list[dict[str, str]]:
    """Every changed path with status and modes, NUL-separated so any file name is safe."""
    raw = _git("diff-tree", "-r", "-z", "--raw", "--no-renames", "--no-commit-id", base, commit,
               cwd=repo, text=False).stdout.split(b"\0")
    out = []
    for meta, name in zip(raw[0::2], raw[1::2]):
        if not meta:
            continue
        old_mode, new_mode, _old, _new, status = meta.decode().lstrip(":").split(" ")
        out.append({"status": status, "path": name.decode(errors="surrogateescape"),
                    "old_mode": old_mode, "new_mode": new_mode})
    return out


def check_candidate(plan: dict[str, Any]) -> list[str]:
    """Why the prepared candidate repository no longer holds exactly the planned commit."""
    c = plan["candidate"]
    repo = Path(c["repository"])
    if not repo.is_dir():
        return [f"the candidate repository {repo} is missing"]
    problems = []
    got = _git("rev-parse", "--verify", "--quiet", f"{c['commit']}^{{commit}}", cwd=repo, check=False)
    if got.returncode != 0:
        return [f"the candidate commit {c['commit']} is missing from {repo}"]
    if _git("rev-parse", f"{c['commit']}^{{tree}}", cwd=repo).stdout.strip() != c["tree"]:
        problems.append("the candidate commit's tree is not the planned tree")
    parents = _git("rev-list", "--parents", "-n", "1", c["commit"], cwd=repo).stdout.split()[1:]
    if parents != [c["parent"]]:
        problems.append("the candidate commit's parent is not the verified baseline")
    if changed_files(repo, c["parent"], c["commit"]) != c["files"]:
        problems.append("the candidate's changed files are not the planned changes")
    ident = _git("log", "-1", "--format=%an%x00%ae%x00%cn%x00%ce", c["commit"], cwd=repo).stdout.strip().split("\0")
    if ident != [c["author"]["name"], c["author"]["email"]] * 2:
        problems.append("the candidate commit's author or committer is not the planned human identity")
    return problems



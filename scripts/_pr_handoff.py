"""From a verified delivery to an owner-reviewable draft pull request.

Three operations, each with its own authority:

- **prepare** is local, plus read-only remote inspection. It builds the candidate commit from the
  sealed patch (`_pr_candidate`), binds it to its verification, renders the exact PR body, and
  writes an immutable plan and a preview. It pushes nothing and creates nothing.
- **publish** needs the owner's authorization naming the plan's digest. It rechecks every identity
  and the remote state, pushes one new branch without force, and creates one draft PR. On a
  retry it reconciles with what GitHub shows before writing anything.
- **status** is read-only. It shows the PR, whether its head is still the verified commit, whether
  the base moved, and the checks GitHub reports for that exact head.

A draft PR is a review surface. It is not proof of correctness, not merge readiness and not
approval. Python records facts and relays the coordinator's explicit judgments. It never infers
quality, goal satisfaction or acceptable risk (`P1`).
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any

import _pr_candidate as candidate
import _pr_github as github

PLAN = "plan.json"
BODY = "pr-body.md"
PREVIEW = "preview.md"
AUTHORIZATIONS = "authorizations.json"
PUBLICATION = "publication.json"
SUMMARY_FORMAT = "proofbound-review-summary-v1"
GOAL_STATES = ("original", "revised", "not-established", "unknown")
REQUIRED_LISTS = ("implementation_choices", "defects", "waived_requirements", "unverified_claims",
                  "review_recipe", "post_delivery_edits", "architecture")
EFFECTS = (
    "pushes one new branch holding exactly the candidate commit; nothing is force-pushed",
    "creates one draft pull request from that branch into the base branch",
    "may start the repository's CI or other workflows, as any push or pull request can; the draft "
    "flag does not prevent workflows or deployments that the repository triggers on these events",
    "is visible to everyone who can see the repository",
)
NOT_DONE = ("merge", "approve", "mark ready for review", "request reviewers", "fork",
            "delete branches", "switch GitHub accounts or change credentials", "rerun CI")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, data: Any) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def _read_json(path: Path, default: Any = None) -> Any:
    return json.loads(path.read_text()) if path.is_file() else default


# ---------------------------------------------------------------- review summary

def load_summary(path: Path) -> dict[str, Any]:
    """The coordinator's review summary: every judgment the PR states, supplied explicitly.

    Only its shape is checked. An empty list is an explicit statement ("none reported"); a
    missing field is an error. Goal satisfaction must be chosen, and "unknown" is allowed.
    """
    s = json.loads(Path(path).read_text())
    problems = []
    if s.get("format") != SUMMARY_FORMAT:
        problems.append(f"format must be {SUMMARY_FORMAT!r}")
    for key in ("title", "problem", "behavior", "coordinator_usage"):
        if not isinstance(s.get(key), str) or not s[key].strip():
            problems.append(f"{key} must be a non-empty string")
    for key in REQUIRED_LISTS:
        if not isinstance(s.get(key), list):
            problems.append(f"{key} must be a list (empty means none)")
    for key in ("implementation_choices", "review_recipe"):
        if isinstance(s.get(key), list) and not s[key]:
            problems.append(f"{key} needs at least one entry")
    goal = s.get("goal_satisfaction") or {}
    if goal.get("status") not in GOAL_STATES or not str(goal.get("explanation", "")).strip():
        problems.append(f"goal_satisfaction needs a status in {GOAL_STATES} and an explanation")
    for claim in s.get("architecture") or []:
        if not isinstance(claim, dict) or not str(claim.get("claim", "")).strip() or not claim.get("references"):
            problems.append("every architecture claim needs its text and at least one reference")
    if problems:
        raise ValueError("review summary is incomplete: " + "; ".join(problems))
    return s


def _reference_problems(summary: dict[str, Any], repo: Path, commit: str) -> list[str]:
    """Each architecture reference must be a URL or a path present in the candidate."""
    out = []
    for claim in summary["architecture"]:
        for ref in claim["references"]:
            if re.match(r"^https://", ref):
                continue
            path = ref.split("#", 1)[0]
            cp = candidate._git("cat-file", "-e", f"{commit}:{path}", cwd=repo, check=False)
            if cp.returncode != 0:
                out.append(f"architecture reference {ref!r} is neither a URL nor a path in the candidate")
    return out


# ---------------------------------------------------------------- the PR body

def _lines(items: list[str], empty: str) -> str:
    return "\n".join(f"- {x}" for x in items) if items else f"- {empty}"


def render_body(summary: dict[str, Any], plan: dict[str, Any]) -> str:
    """The exact PR text. Material limitations first; facts and judgments labelled apart."""
    d, v, c, t = plan["delivery"], plan["verification"], plan["candidate"], plan["target"]
    blob = f"{t['html_url']}/blob/{c['commit']}"
    goal = summary["goal_satisfaction"]
    arch = "\n".join(
        f"- {a['claim']} — " + ", ".join(
            (f"[{r}]({r})" if r.startswith("https://") else f"[`{r}`]({blob}/{r})") for r in a["references"])
        for a in summary["architecture"]) or "- The coordinator stated no architecture claims."
    checks = [f"- Project check `{v['project_check']['command']}`: exit {v['project_check']['returncode']}"]
    if v.get("dependencies"):
        checks.append(f"- Dependency preparation: exit {v['dependencies']['returncode']}, "
                      f"matches the prepared dependencies: {v['dependencies']['matches_prepared']}")
    if v.get("outcome_check"):
        checks.append(f"- Outcome check (command kept private): exit {v['outcome_check']['returncode']}")
    u = plan.get("usage") or {}
    files = "\n".join(f"- `{f['status']}` `{f['path']}`" + (f" (mode {f['old_mode']} → {f['new_mode']})"
                      if f["status"] in "MT" and f["old_mode"] != f["new_mode"] else "")
                      for f in c["files"])
    return f"""> **Draft for owner review.** This pull request is a review surface for a change produced through
> Proofbound. Its checks and reviews are evidence, not approval: whether it should merge is the
> owner's decision. Sections marked *coordinator* are judgments supplied explicitly by the
> coordinator; sections marked *recorded* are facts Proofbound observed.

## Read first: known defects, waivers and unverified claims (coordinator)

**Known defects**
{_lines(summary['defects'], 'none reported by the coordinator')}

**Waived or revised requirements**
{_lines(summary['waived_requirements'], 'none reported by the coordinator')}

**Claims not verified**
{_lines(summary['unverified_claims'], 'none reported by the coordinator')}

## Goal satisfaction (coordinator)

**{goal['status']}**: {goal['explanation']}

## Problem and resulting behavior (coordinator)

{summary['problem']}

{summary['behavior']}

## Main implementation choices (coordinator)

{_lines(summary['implementation_choices'], '')}

## Architecture touched (coordinator claims, with references)

{arch}

## Checks (recorded)

`verify-delivery` applied the sealed patch to a fresh checkout of the baseline and ran the checks
there. The candidate commit's tree is the tree it verified.
{chr(10).join(checks)}

These results belong to that verification. CI on this pull request is reported separately by GitHub.

## How to review it (coordinator)

{chr(10).join(f"{i}. {s}" for i, s in enumerate(summary['review_recipe'], 1))}

## Changed files (recorded)

{files}

```
{c['diffstat'].rstrip()}
```

## Post-delivery edits

- Recorded: the commit applies the sealed delivery's patch unchanged (patch sha256 `{d['patch_sha256']}`).
- Coordinator: {'; '.join(summary['post_delivery_edits']) if summary['post_delivery_edits'] else 'none'}

## Identities (recorded)

| | |
|---|---|
| Change | `{d.get('change')}`, run `{d.get('run')}` |
| Baseline | `{d['baseline']}` |
| Candidate commit / tree | `{c['commit']}` / `{c['tree']}` |
| Delivery manifest | sha256 `{d['manifest_sha256']}` |
| Verification | sha256 `{v['sha256']}`, at {v.get('verified_at')}, by Proofbound `{(v['verifier'].get('proofbound_commit') or 'unknown')[:12]}` (scripts tree `{v['verifier']['scripts_tree'][:12]}`) |

## Usage

- Worker (recorded): derived ${u.get('derived')}, complete: {u.get('complete')}, {u.get('calls')} calls, priced at `{u.get('table')}`. Derived cost is not provider billing.
- Coordinator (coordinator): {summary['coordinator_usage']}

## Evidence

The sealed delivery, run records, per-call usage rows and verification output are **private**,
retained by the owner, and not part of this pull request.
{_lines(summary.get('private_evidence') or [], 'No further private evidence was named.')}
"""


def _private_paths(text: str, extra: list[str]) -> list[str]:
    found = [p for p in [str(Path.home()), "/private/tmp/", "/private/var/", "/var/folders/", *extra]
             if p and p in text]
    return sorted(set(found))


# ---------------------------------------------------------------- prepare

def prepare(*, delivery: Path, verification: Path, repo: str, base: str, summary_path: Path,
            into: Path, gh: str = "gh", host: str = "github.com", head: "str | None" = None,
            account: "str | None" = None, source: "Path | None" = None) -> dict[str, Any]:
    into = Path(into).resolve()
    if into.exists():
        raise ValueError(f"{into} exists; each prepared plan gets its own new directory")
    d = candidate.check_delivery(Path(delivery))
    v = candidate.check_verification(Path(verification), d)
    summary = load_summary(Path(summary_path))
    src = Path(source).resolve() if source else Path(d["project"] or "")
    if not (src / ".git").exists():
        raise ValueError(f"{src} is not a Git repository holding the baseline; pass --source")
    identity = candidate.human_identity(src)
    date = v["verified_at"]
    if not date:
        raise ValueError("the verification has no time; verify again with this version")

    # Read-only remote inspection. Nothing here writes.
    hub = github.GitHub(gh, host)
    inspection = {"read_only": True, "at": _now(), "commands": [
        "gh api --method GET user", f"gh api --method GET repos/{repo}", "git ls-remote",
        "gh pr list --state all --head <branch>"]}
    login = hub.login()
    if account and login != account:
        raise ValueError(f"gh is authenticated as {login!r}, not the requested {account!r}; "
                         "Proofbound does not switch accounts")
    target = hub.repository(repo)
    if (target["full_name"] or "").lower() != repo.lower():
        raise ValueError(f"{repo} resolves to {target['full_name']!r}; name the repository exactly")
    push_url = target["ssh_url"] if hub.git_protocol() == "ssh" else target["clone_url"]

    into.mkdir(parents=True)
    title = summary["title"].strip()
    built = candidate.build(d, v, src, into, message=summary.get("commit_message") or title,
                            identity=identity, date=date)
    head = head or f"proofbound/{d.get('change') or 'change'}-{built['commit'][:12]}"
    refs = github.ls_remote(push_url, base, head)
    problems = _reference_problems(summary, Path(built["repository"]), built["commit"])
    if base not in refs:
        problems.append(f"the base branch {base!r} does not exist in {repo}")
    elif refs[base] != d["baseline"]:
        problems.append(f"the base branch {base!r} is at {refs[base]}, not the verified baseline "
                        f"{d['baseline']}. A new candidate built and verified on the new base is "
                        "needed; Proofbound does not rebase, merge or reuse this verification")
    if head in refs and refs[head] != built["commit"]:
        problems.append(f"the branch {head!r} already exists at {refs[head]}; choose another --head")
    existing = [p for p in hub.pulls_for_head(repo, head) if not p.get("isCrossRepository")]
    if any(p.get("headRefOid") != built["commit"] for p in existing):
        problems.append(f"a pull request for branch {head!r} already exists with other content")
    usage = _read_json(Path(d["path"]) / "usage.json", {}) or {}
    plan = {
        "format": "proofbound-pr-plan-v1", "prepared_at": _now(),
        "delivery": {k: d[k] for k in ("path", "manifest_sha256", "patch_sha256", "baseline",
                                       "outcome", "change", "run")},
        "verification": v,
        "candidate": {k: built[k] for k in ("repository", "commit", "tree", "parent", "author",
                                             "date", "files", "diffstat")},
        "target": {"host": host, "repo": target["full_name"], "id": target["id"],
                   "visibility": target["visibility"], "html_url": target["html_url"],
                   "push_url": push_url, "base": base, "base_sha_observed": refs.get(base),
                   "can_push": target["can_push"]},
        "head_branch": head, "title": title, "account": login,
        "summary_sha256": candidate.sha256(Path(summary_path)),
        "usage": {"derived": usage.get("derived"), "complete": usage.get("complete"),
                  "calls": (usage.get("usage") or {}).get("calls_finished"),
                  "table": (usage.get("billing") or {}).get("table")},
        "effects": list(EFFECTS), "not_done": list(NOT_DONE), "inspection": inspection,
    }
    body = render_body(summary, plan)
    leaked = _private_paths(body, [str(into), d["path"], str(Path(verification).resolve().parent)])
    if leaked:
        problems.append(f"the PR body would publish private local paths {leaked}; remove them from "
                        "the review summary")
    if problems:
        _write_json(into / "refused.json", {"at": _now(), "problems": problems})
        raise ValueError("not prepared: " + "; ".join(problems) + f" (details in {into / 'refused.json'})")
    (into / BODY).write_text(body)
    plan["body_sha256"] = candidate.sha256(into / BODY)
    _write_json(into / PLAN, plan)
    plan_sha = candidate.sha256(into / PLAN)
    (into / PREVIEW).write_text(render_preview(plan, plan_sha, body))
    return {"prepared": str(into), "plan_sha256": plan_sha, "preview": str(into / PREVIEW),
            "body": str(into / BODY), "candidate_commit": built["commit"], "head_branch": head,
            "pushed": False, "pull_request_created": False,
            "authorize_with": f"publish-pr --handoff {into} --owner-authorization "
                              f"'<your words, including {plan_sha}>'"}


def render_preview(plan: dict[str, Any], plan_sha: str, body: str) -> str:
    t, c = plan["target"], plan["candidate"]
    files = "\n".join(f"  {f['status']}  {f['path']}" for f in c["files"])
    return f"""# Publication preview — nothing has been pushed or created

Plan sha256: `{plan_sha}`

## What publication would do
- Repository: {t['repo']} on {t['host']} ({t['visibility']}); push URL {t['push_url']}
- Account: {plan['account']} (the account `gh` authenticated as when this was prepared)
- New branch: `{plan['head_branch']}` at commit `{c['commit']}`
- Draft pull request into `{t['base']}`, whose head was `{t['base_sha_observed']}` when inspected
  (a base branch can move after this; publication checks it again)
- Title: {plan['title']}

Effects:
{chr(10).join('- ' + e for e in plan['effects'])}

Never done: {', '.join(plan['not_done'])}.

## Files in the commit
{files}

## Pull request body, exactly
{body}
## To authorize
Publication needs your authorization naming this plan's digest, `{plan_sha}`. A changed candidate,
destination or text makes a new plan with a new digest.
"""


# ---------------------------------------------------------------- publish

def _load_plan(handoff: Path) -> tuple[dict[str, Any], str]:
    plan_path = handoff / PLAN
    if not plan_path.is_file():
        raise ValueError(f"{handoff} holds no prepared plan")
    return json.loads(plan_path.read_text()), candidate.sha256(plan_path)


def _local_problems(handoff: Path, plan: dict[str, Any]) -> list[str]:
    problems = []
    body = handoff / BODY
    if not body.is_file() or candidate.sha256(body) != plan["body_sha256"]:
        problems.append("the PR body differs from the prepared body")
    problems += candidate.check_candidate(plan)
    if plan["candidate"]["tree"] != plan["verification"]["candidate_tree"]:
        problems.append("the candidate tree is not the verified tree")
    return problems


def _authorization(handoff: Path, plan_sha: str, text: "str | None") -> dict[str, Any]:
    records = _read_json(handoff / AUTHORIZATIONS, []) or []
    for rec in records:
        if rec.get("plan_sha256") == plan_sha:
            return rec
    if not text or not text.strip():
        raise ValueError(f"publication needs the owner's authorization naming plan {plan_sha}")
    if plan_sha not in text:
        raise ValueError("the authorization does not name this plan's digest; it may have been "
                         f"given for another plan. Plan sha256: {plan_sha}")
    rec = {"plan_sha256": plan_sha, "text": text, "recorded_at": _now()}
    _write_json(handoff / AUTHORIZATIONS, records + [rec])
    return rec


def _event(record: dict[str, Any], path: Path, state: str, **detail: Any) -> None:
    record["state"] = state
    record.setdefault("events", []).append({"at": _now(), "state": state, **detail})
    _write_json(path, record)


def _matching(prs: list[dict[str, Any]], head: str) -> list[dict[str, Any]]:
    return [p for p in prs if p.get("headRefName") == head and not p.get("isCrossRepository")]


def publish(handoff: Path, *, gh: str = "gh", authorization: "str | None" = None) -> dict[str, Any]:
    handoff = Path(handoff).resolve()
    plan, plan_sha = _load_plan(handoff)
    problems = _local_problems(handoff, plan)
    if problems:
        raise ValueError("the prepared candidate changed: " + "; ".join(problems) + ". Prepare again.")
    auth = _authorization(handoff, plan_sha, authorization)
    t, c, head = plan["target"], plan["candidate"], plan["head_branch"]
    rec_path = handoff / PUBLICATION
    record = _read_json(rec_path, None) or {"plan_sha256": plan_sha, "state": "prepared", "events": []}
    if record["plan_sha256"] != plan_sha:
        raise ValueError("the publication record belongs to another plan")

    def blocked(why: str, **detail: Any) -> dict[str, Any]:
        _event(record, rec_path, "blocked", why=why, **detail)
        return {"published": False, "state": "blocked", "why": why, "record": str(rec_path), **detail}

    hub = github.GitHub(gh, t["host"])
    login = hub.login()
    if login != plan["account"]:
        return blocked(f"gh is authenticated as {login!r}, but the plan was prepared for "
                       f"{plan['account']!r}. Proofbound does not switch accounts")
    repo = hub.repository(t["repo"])
    if repo["id"] != t["id"] or repo["full_name"] != t["repo"] or repo["visibility"] != t["visibility"]:
        return blocked("the target repository's identity or visibility changed since preparation",
                       observed={k: repo[k] for k in ("id", "full_name", "visibility")})
    refs = github.ls_remote(t["push_url"], t["base"], head)
    if refs.get(t["base"]) != plan["delivery"]["baseline"]:
        return blocked(f"the base branch {t['base']!r} is at {refs.get(t['base'])}, not the verified "
                       "baseline; a new candidate and verification are needed")

    def reconcile() -> "dict[str, Any] | None":
        found = _matching(hub.pulls_for_head(t["repo"], head), head)
        if not found:
            return None
        if len(found) > 1:
            return blocked("more than one pull request uses this branch; not choosing",
                           pulls=[p.get("url") for p in found])
        p = hub.pull(t["repo"], found[0]["number"])
        if p.get("state") != "OPEN":
            return blocked(f"a {p.get('state')} pull request already used this branch ({p.get('url')}); "
                           "Proofbound does not recreate it", pull=p.get("url"))
        if p.get("headRefOid") != c["commit"] or p.get("baseRefName") != t["base"]:
            return blocked("the existing pull request's head or base is not the planned candidate "
                           "(changed externally); nothing was overwritten", pull=p.get("url"),
                           observed={"head": p.get("headRefOid"), "base": p.get("baseRefName")})
        observed = {k: p.get(k) for k in ("number", "url", "isDraft", "state", "baseRefName",
                                          "baseRefOid", "headRefName", "headRefOid")}
        observed.update(repository=t["repo"], observed_at=_now())
        record["pull_request"] = observed
        _event(record, rec_path, "published", pull=p.get("url"), draft=p.get("isDraft"))
        return {"published": True, "state": "published", "pull_request": observed,
                "record": str(rec_path), "authorization_recorded_at": auth["recorded_at"],
                "note": ("the pull request is not a draft; Proofbound did not change it"
                         if not p.get("isDraft") else "draft; the base branch can move after this")}

    done = reconcile()
    if done:
        return done
    remote_head = refs.get(head)
    if remote_head is None:
        _event(record, rec_path, "push-intended", commit=c["commit"], branch=head)
        cp = github.push_new_branch(Path(c["repository"]), t["push_url"], c["commit"], head)
        after = github.ls_remote(t["push_url"], head).get(head)
        if after != c["commit"]:
            return blocked("the push did not leave the branch at the candidate commit",
                           push_exit=cp.returncode, push_error=cp.stderr.strip()[-400:], observed=after)
        _event(record, rec_path, "pushed", commit=c["commit"])
    elif remote_head != c["commit"]:
        return blocked(f"the branch {head!r} exists at {remote_head}, not the candidate; "
                       "nothing was overwritten")
    else:
        _event(record, rec_path, "pushed", commit=c["commit"], note="already on the remote")
    _event(record, rec_path, "create-intended")
    cp = hub.create_draft(t["repo"], t["base"], head, plan["title"], handoff / BODY, handoff)
    detail = {"create_exit": cp.returncode, "create_error": cp.stderr.strip()[-400:] or None}
    done = reconcile()   # the command's exit alone does not say what exists
    if done:
        done["create"] = detail
        return done
    return blocked("no matching pull request is observable after the create request", **detail)


# ---------------------------------------------------------------- status

def status(handoff: Path, *, gh: str = "gh") -> dict[str, Any]:
    handoff = Path(handoff).resolve()
    plan, plan_sha = _load_plan(handoff)
    record = _read_json(handoff / PUBLICATION, None)
    t, c, v = plan["target"], plan["candidate"], plan["verification"]
    out: dict[str, Any] = {
        "plan_sha256": plan_sha,
        "local": {"candidate_commit": c["commit"], "candidate_tree": c["tree"],
                  "candidate_intact": not _local_problems(handoff, plan),
                  "verification": {"verified_at": v.get("verified_at"), "project_check": v["project_check"],
                                   "outcome_check": v.get("outcome_check"), "sha256": v["sha256"]},
                  "authorized": any(r.get("plan_sha256") == plan_sha
                                    for r in _read_json(handoff / AUTHORIZATIONS, []) or [])},
        "publication": {"state": (record or {}).get("state", "not published"),
                        "pull_request": (record or {}).get("pull_request")},
        "not_equivalent": "local verification, CI results, worker review, mergeability and owner "
                          "approval are different facts; none implies another",
    }
    hub = github.GitHub(gh, t["host"])
    remote: dict[str, Any] = {"observed_at": _now(), "read_only": True}
    try:
        refs = github.ls_remote(t["push_url"], t["base"], plan["head_branch"])
        remote["base_sha"] = refs.get(t["base"])
        remote["base_advanced"] = refs.get(t["base"]) != plan["delivery"]["baseline"]
        remote["branch_sha"] = refs.get(plan["head_branch"])
    except github.RemoteError as exc:
        remote["refs"] = f"unavailable: {exc}"
    pr = (record or {}).get("pull_request")
    head_sha = remote.get("branch_sha")
    if pr:
        try:
            p = hub.pull(t["repo"], pr["number"])
            remote["pull_request"] = {k: p.get(k) for k in ("url", "state", "isDraft", "baseRefName",
                                                            "baseRefOid", "headRefOid")}
            head_sha = p.get("headRefOid")
        except github.RemoteError as exc:
            remote["pull_request"] = f"unavailable: {exc}"
    if head_sha:
        remote["head_is_verified_candidate"] = head_sha == c["commit"]
        remote["checks"] = hub.checks(t["repo"], head_sha)
        if head_sha != c["commit"]:
            remote["warning"] = (f"the remote head {head_sha} is not the verified candidate "
                                 f"{c['commit']}; the checks shown are for the remote head only")
    else:
        remote["checks"] = {"state": "no checks observed", "why": "nothing has been published"}
    failed = (remote.get("checks") or {}).get("counts", {}).get("failed")
    if failed:
        remote["attention"] = (f"{failed} check(s) failed on the published head. The local "
                               "verification above still stands as recorded, for its own run")
    out["remote"] = remote
    return out

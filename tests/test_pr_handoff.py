"""Draft-PR handoff: a verified delivery becomes a reviewable draft PR, and nothing else happens.

Real Git throughout: a project repository, a sealed delivery, a real `verify-delivery`, a local bare
repository as the remote. GitHub is a recording stand-in `gh` that serves a recorded state and
refuses every command it does not know, so the tests need no credentials and cannot reach GitHub.
A logging `git` shim records every Git invocation.

What each group falsifies:
- **Identity.** The candidate is the sealed patch on the baseline, the tree verification recorded:
  modes, a deletion, binaries, a symlink and a file name full of shell metacharacters included.
  Tampered or mismatched evidence, a check that writes content, and dirty source files never
  reach it.
- **Refusals before anything is written.** A moved base, the wrong repository or account, a branch
  collision, an unauthorized or re-planned publication.
- **Publication and retries.** One push, one draft PR. A lost response or a repeated call returns
  the existing PR. An external change, or a closed PR, stops without overwriting.
- **Status.** Check states stay distinct, belong to the head commit, and an old green run on an
  older commit is not evidence for a newer head.
- **Never.** No merge, force-push, account switch, fork or reviewer request; no private path in the
  published text; nothing is pushed or created by preparation.
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
REAL_GIT = shutil.which("git")

FAKE_GH = r'''#!PYTHON
import json, os, subprocess, sys
state_path = os.environ["FAKE_GH_STATE"]
state = json.load(open(state_path))
args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a") as log:
    log.write(json.dumps(args) + "\n")
def out(obj): print(json.dumps(obj)); sys.exit(0)
def fail(msg, code=1): sys.stderr.write(msg + "\n"); sys.exit(code)
def opt(name):
    return args[args.index(name) + 1] if name in args else None
def bare(repo): return state["repos"][repo]["clone_url"]
def rev(repo, branch):
    cp = subprocess.run(["REALGIT", "--git-dir", bare(repo), "rev-parse", "--verify", "--quiet",
                         "refs/heads/" + branch], capture_output=True, text=True)
    return cp.stdout.strip() or None
def live(pr):
    now = rev(pr["repo"], pr["headRefName"])
    return {**pr, "headRefOid": now or pr["headRefOid"]}
def fields(pr, spec):
    return {k: pr.get(k) for k in spec.split(",")}
if args[:1] == ["api"]:
    path = args[-1]
    if state.get("fail", {}).get("api"): fail("HTTP 502: bad gateway")
    if path == "user": out({"login": state["login"]})
    if path.startswith("repos/"):
        parts = path.split("?")[0].split("/")
        repo = "/".join(parts[1:3])
        if repo not in state["repos"]: fail("HTTP 404: Not Found (https://api.github.com/" + path + ")")
        if len(parts) == 3: out(state["repos"][repo])
        if len(parts) == 5 and parts[3] == "actions" and parts[4] == "runs":
            sha = path.split("head_sha=")[1].split("&")[0]
            out({"workflow_runs": state.get("workflow_runs", {}).get(sha, [])})
        if len(parts) == 6 and parts[3] == "commits":
            if state.get("fail", {}).get("checks"): fail("HTTP 403: rate limited")
            sha = parts[4]
            if parts[5] == "check-runs": out({"check_runs": state.get("check_runs", {}).get(sha, [])})
            if parts[5] == "status": out({"statuses": state.get("statuses", {}).get(sha, [])})
    fail("UNSUPPORTED api " + path, 3)
if args[:3] == ["config", "get", "git_protocol"]:
    print(state.get("protocol", "https")); sys.exit(0)
if args[:2] == ["pr", "list"]:
    repo, head = opt("--repo"), opt("--head")
    out([fields(live(p), opt("--json")) for p in state["pulls"] if p["repo"] == repo and p["headRefName"] == head])
if args[:2] == ["pr", "view"]:
    repo, number = opt("--repo"), int(args[2])
    for p in state["pulls"]:
        if p["repo"] == repo and p["number"] == number: out(fields(live(p), opt("--json")))
    fail("no pull request found")
if args[:2] == ["pr", "create"]:
    repo, base, head = opt("--repo"), opt("--base"), opt("--head")
    if state.get("fail", {}).get("create"): fail("HTTP 500: create failed")
    if not rev(repo, head): fail("head branch not found")
    n = len(state["pulls"]) + 1
    state["pulls"].append({"repo": repo, "number": n, "url": "https://github.com/%s/pull/%d" % (repo, n),
        "state": "OPEN", "isDraft": "--draft" in args, "baseRefName": base, "baseRefOid": rev(repo, base),
        "headRefName": head, "headRefOid": rev(repo, head), "isCrossRepository": False,
        "title": opt("--title"), "body": open(opt("--body-file")).read()})
    json.dump(state, open(state_path, "w"))
    if state.get("fail", {}).get("lose_response"): fail("connection reset by peer")
    print(state["pulls"][-1]["url"]); sys.exit(0)
fail("UNSUPPORTED " + " ".join(args), 3)
'''

GIT_SHIM = r'''#!PYTHON
import json, os, sys
with open(os.environ["GIT_SHIM_LOG"], "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\n")
os.execv("REALGIT", ["git"] + sys.argv[1:])
'''

METACHAR_NAME = "notes/odd $(touch PWNED) & name; `x`.md"
TITLE = 'Add "v2" behaviour; $(touch PWNED) & `echo hi` | safe'


def git(*args, cwd=None, check=True):
    cp = subprocess.run([REAL_GIT, *args], cwd=cwd, capture_output=True, text=True)
    if check and cp.returncode:
        raise AssertionError(cp.stderr)
    return cp.stdout.strip()


class Harness:
    def __init__(self, case, *, check_writes_tracked=False):
        self.case = case
        self.tmp = Path(tempfile.mkdtemp(prefix="pb pr $(touch PWNED) ", dir="/private/tmp" if sys.platform == "darwin" else None))
        case.addCleanup(shutil.rmtree, self.tmp, True)
        self.project = self.tmp / "project"
        self._project()
        self.remote = self.tmp / "remote.git"
        git("init", "--quiet", "--bare", str(self.remote))
        git("push", "--quiet", str(self.remote), f"{self.baseline}:refs/heads/main", cwd=self.project)
        self.delivery = self._delivery(check_writes_tracked)
        self._tools()
        self.state = {"login": "owner-human", "protocol": "https", "pulls": [], "check_runs": {}, "statuses": {},
                      "repos": {"acme/app": {"id": 7, "full_name": "acme/app", "visibility": "public",
                                             "private": False, "default_branch": "main",
                                             "html_url": "https://github.com/acme/app",
                                             "clone_url": str(self.remote), "ssh_url": str(self.remote),
                                             "permissions": {"push": True}}}}
        self.save()
        self.summary = self.tmp / "review summary.json"
        self.write_summary()

    # ---------------------------------------------------------------- fixtures
    def _project(self):
        p = self.project
        (p / "src").mkdir(parents=True); (p / "bin").mkdir(); (p / "assets").mkdir(); (p / "docs").mkdir()
        (p / ".gitignore").write_text("build/\n")
        (p / "src/app.txt").write_text("v1\n")
        (p / "bin/tool.sh").write_text("#!/bin/sh\necho tool\n")
        (p / "assets/logo.bin").write_bytes(bytes(range(256)))
        (p / "docs/guide with spaces.md").write_text("guide\n")
        (p / "old.txt").write_text("to be deleted\n")
        git("init", "--quiet", "-b", "main", cwd=p)
        git("config", "user.name", "Owner Human", cwd=p); git("config", "user.email", "owner@example.invalid", cwd=p)
        git("add", "-A", cwd=p); git("commit", "--quiet", "-m", "baseline", cwd=p)
        self.baseline = git("rev-parse", "HEAD", cwd=p)

    def _delivery(self, check_writes_tracked):
        p = self.project
        (p / "src/app.txt").write_text("v2\n")
        os.chmod(p / "bin/tool.sh", 0o755)
        (p / "old.txt").unlink()
        (p / "assets/new.bin").write_bytes(bytes(reversed(range(256))) * 3)
        os.symlink("src/app.txt", p / "link-to-app")
        (p / "notes").mkdir(); (p / METACHAR_NAME).write_text("metacharacters in a file name\n")
        git("add", "-A", cwd=p)
        patch = subprocess.run([REAL_GIT, "diff", "--cached", "--binary", self.baseline], cwd=p,
                               capture_output=True, check=True).stdout
        git("reset", "--quiet", "--hard", self.baseline, cwd=p); git("clean", "-qfdx", cwd=p)
        d = self.tmp / "run" / "delivery"
        (d / "evidence").mkdir(parents=True)
        (d / "change.patch").write_bytes(patch)
        (d / "handoff.json").write_text(json.dumps({"baseline": self.baseline, "outcome": "accepted"}))
        check = (f"{sys.executable} -c \"import pathlib, sys; "
                 + ("pathlib.Path('generated.txt').write_text('x'); " if check_writes_tracked else "")
                 + "pathlib.Path('build').mkdir(exist_ok=True); pathlib.Path('build/out').write_text('ignored'); "
                 "print('checked 1 file'); print('ran in', pathlib.Path.cwd()); "
                 "sys.exit(pathlib.Path('src/app.txt').read_text() != 'v2\\n')\"")
        (d / "evidence/run-config.json").write_text(json.dumps({
            "check_command": check, "goal": str(p / "specs/CH-PR-1/goal.md"),
            "paths": {"project": str(p), "run_root": str(self.tmp / "run" / "first")}}))
        (d / "usage.json").write_text(json.dumps({"derived": 0.0123, "complete": True,
                                                  "usage": {"calls_finished": 4},
                                                  "billing": {"table": "table-x"}}))
        self.seal(d)
        return d

    @staticmethod
    def seal(d):
        import hashlib
        (d / "manifest.json").write_text(json.dumps({
            str(f.relative_to(d)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in d.rglob("*") if f.is_file() and f.name != "manifest.json"}))

    def _tools(self):
        bin_dir = self.tmp / "bin"; bin_dir.mkdir()
        self.gh = bin_dir / "gh"
        self.gh.write_text(FAKE_GH.replace("PYTHON", sys.executable).replace("REALGIT", REAL_GIT))
        shim = bin_dir / "git"
        shim.write_text(GIT_SHIM.replace("PYTHON", sys.executable).replace("REALGIT", REAL_GIT))
        for f in (self.gh, shim):
            f.chmod(0o755)
        self.gh_log, self.git_log = self.tmp / "gh.log", self.tmp / "git.log"
        self.state_path = self.tmp / "gh-state.json"
        self.env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
                    "FAKE_GH_STATE": str(self.state_path), "FAKE_GH_LOG": str(self.gh_log),
                    "GIT_SHIM_LOG": str(self.git_log)}

    def save(self):
        self.state_path.write_text(json.dumps(self.state))

    def load(self):
        self.state = json.loads(self.state_path.read_text())
        return self.state

    def write_summary(self, **changes):
        s = {"format": "proofbound-review-summary-v1", "title": TITLE,
             "problem": "Operators need version 2 of the app text.",
             "behavior": "The app text reads v2; the tool is executable; old.txt is gone.",
             "implementation_choices": ["Edited the text file in place."],
             "architecture": [{"claim": "Only the app text and assets change.", "references": ["src/app.txt"]}],
             "defects": ["The link is relative and breaks if moved."],
             "waived_requirements": [], "unverified_claims": ["Behaviour on Windows was not observed."],
             "goal_satisfaction": {"status": "revised", "explanation": "The owner narrowed the goal."},
             "review_recipe": ["Read src/app.txt.", "Run the check."],
             "post_delivery_edits": [], "coordinator_usage": "unavailable",
             "private_evidence": ["the sealed delivery and run records"]}
        s.update(changes)
        self.summary.write_text(json.dumps(s))

    # ---------------------------------------------------------------- commands
    def cli(self, *args, ok=True):
        cp = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True,
                            text=True, env=self.env, cwd=self.tmp, timeout=300)
        try:
            out = json.loads(cp.stdout)
        except ValueError:
            raise AssertionError(f"not JSON (exit {cp.returncode}): {cp.stdout[-800:]} {cp.stderr[-1500:]}")
        if ok is True:
            self.case.assertEqual(cp.returncode, 0, out)
        elif ok is False:
            self.case.assertNotEqual(cp.returncode, 0, out)
        return out

    def verify(self, name="verify"):
        out = self.cli("verify-delivery", "--delivery", self.delivery, "--into", self.tmp / name, ok=None)
        return self.tmp / name / "verification.json", out

    def prepare(self, name="handoff", verification=None, ok=True, **extra):
        verification = verification or self.verify()[0]
        args = ["prepare-pr", "--delivery", self.delivery, "--verification", verification,
                "--repo", extra.pop("repo", "acme/app"), "--base", extra.pop("base", "main"),
                "--review-summary", self.summary, "--into", self.tmp / name, "--gh", self.gh]
        for k, v in extra.items():
            args += [f"--{k}", v]
        return self.cli(*args, ok=ok)

    def publish(self, handoff, authorization=None, ok=True):
        args = ["publish-pr", "--handoff", handoff, "--gh", self.gh]
        if authorization is not None:
            args += ["--owner-authorization", authorization]
        return self.cli(*args, ok=ok)

    def remote_branches(self):
        return {line.split()[1].removeprefix("refs/heads/"): line.split()[0]
                for line in git("--git-dir", str(self.remote), "show-ref", check=False).splitlines()}

    def gh_calls(self):
        return [json.loads(l) for l in self.gh_log.read_text().splitlines()] if self.gh_log.exists() else []

    def git_calls(self):
        return [json.loads(l) for l in self.git_log.read_text().splitlines()] if self.git_log.exists() else []


class Preparation(unittest.TestCase):
    def test_the_candidate_is_the_verified_sealed_patch_and_nothing_is_published(self):
        h = Harness(self)
        verification, v = h.verify()
        self.assertTrue(v["verified"], v)
        self.assertTrue(v["tracked_content_after_checks"]["unchanged"], v["tracked_content_after_checks"])
        out = h.prepare(verification=verification)
        plan = json.loads((Path(out["prepared"]) / "plan.json").read_text())
        c = plan["candidate"]
        self.assertEqual(c["tree"], v["candidate_tree"])
        repo = Path(c["repository"])
        self.assertEqual(git("rev-parse", f"{c['commit']}^", cwd=repo), h.baseline)
        files = {f["path"]: f for f in c["files"]}
        self.assertEqual(files["old.txt"]["status"], "D")
        self.assertEqual((files["bin/tool.sh"]["old_mode"], files["bin/tool.sh"]["new_mode"]), ("100644", "100755"))
        self.assertEqual(files["link-to-app"]["new_mode"], "120000")
        self.assertIn("assets/new.bin", files)
        self.assertIn(METACHAR_NAME, files)
        self.assertEqual(git("log", "-1", "--format=%an <%ae>|%cn <%ce>|%B", c["commit"], cwd=repo).split("|")[:2],
                         ["Owner Human <owner@example.invalid>"] * 2)
        self.assertNotIn("Co-authored-by", git("log", "-1", "--format=%B", c["commit"], cwd=repo))
        # Nothing published: no new remote branch, no PR, only read-only gh calls.
        self.assertEqual(set(h.remote_branches()), {"main"})
        self.assertEqual(h.load()["pulls"], [])
        for call in h.gh_calls():
            self.assertTrue(call[:3] == ["api", "--method", "GET"] or call[:2] == ["pr", "list"]
                            or call[:3] == ["config", "get", "git_protocol"], call)
        self.assertFalse(any(c[:1] == ["push"] for c in h.git_calls()))
        # The preview shows the exact text and files, and the plan digest to authorize.
        preview = Path(out["preview"]).read_text()
        body = Path(out["body"]).read_text()
        self.assertIn(body, preview)
        self.assertIn(out["plan_sha256"], preview)
        self.assertIn(METACHAR_NAME, preview)
        self.assertIn("may start the repository's CI", preview)
        # Limitations come before check results; judgments and facts are labelled.
        self.assertLess(body.index("The link is relative"), body.index("## Checks (recorded)"))
        self.assertIn("**revised**: The owner narrowed the goal.", body)
        self.assertIn("## Architecture touched (coordinator claims, with references)", body)
        self.assertIn(f"https://github.com/acme/app/blob/{c['commit']}/src/app.txt", body)
        # The check's own output is relayed verbatim; a line naming a local path is withheld.
        self.assertIn("checked 1 file", body)
        self.assertIn("[line withheld: it names a local path]", body)
        # No private local path in the published text.
        for private in (str(h.tmp), str(Path.home()), "/private/tmp/", "/var/folders/"):
            self.assertNotIn(private, body)
        self.assertFalse(list(h.tmp.rglob("PWNED")) or Path("PWNED").exists())

    def test_dirty_source_files_never_reach_the_candidate(self):
        h = Harness(self)
        (h.project / "src/app.txt").write_text("dirty local edit\n")
        (h.project / "stray.txt").write_text("untracked\n")
        out = h.prepare()
        plan = json.loads((Path(out["prepared"]) / "plan.json").read_text())
        repo = Path(plan["candidate"]["repository"])
        self.assertEqual(git("show", f"{plan['candidate']['commit']}:src/app.txt", cwd=repo), "v2")
        self.assertNotIn("stray.txt", {f["path"] for f in plan["candidate"]["files"]})

    def test_tampered_or_unrelated_evidence_is_refused(self):
        h = Harness(self)
        verification, _ = h.verify()
        # A verification of another delivery.
        other = Harness(self)
        other_verification, _ = other.verify()
        out = h.prepare("h1", verification=other_verification, ok=False)
        # Possibly the same patch bytes, but another sealed delivery: bound by identity, refused.
        self.assertIn("different delivery manifest", out["error"])
        # A verification whose patch digest names other bytes.
        v = json.loads(verification.read_text()); v["patch"]["sha256"] = "0" * 64
        other_patch = h.tmp / "other-patch.json"; other_patch.write_text(json.dumps(v))
        self.assertIn("different patch", h.prepare("h1b", verification=other_patch, ok=False)["error"])
        # A verification whose recorded tree is not what the sealed patch produces.
        v = json.loads(verification.read_text()); v["candidate_tree"] = "1" * 40
        other_tree = h.tmp / "other-tree.json"; other_tree.write_text(json.dumps(v))
        self.assertIn("but the verification recorded", h.prepare("h1c", verification=other_tree, ok=False)["error"])
        # A detached verified:true without identity.
        v = json.loads(verification.read_text())
        for key in ("candidate_tree", "manifest_sha256"):
            v.pop(key)
        stripped = h.tmp / "stripped.json"; stripped.write_text(json.dumps(v))
        self.assertIn("run verify-delivery again", h.prepare("h2", verification=stripped, ok=False)["error"])
        # A delivery changed after verification.
        (h.delivery / "change.patch").write_bytes((h.delivery / "change.patch").read_bytes() + b"\n")
        self.assertIn("no longer matches its manifest", h.prepare("h3", verification=verification, ok=False)["error"])

    def test_checks_that_write_tracked_content_are_reported_not_published(self):
        h = Harness(self, check_writes_tracked=True)
        verification, v = h.verify()
        self.assertFalse(v["tracked_content_after_checks"]["unchanged"])
        self.assertIn("A\tgenerated.txt", v["tracked_content_after_checks"]["changed"])
        self.assertIn("checks changed tracked", h.prepare(verification=verification, ok=False)["error"])

    def test_a_moved_base_is_refused(self):
        h = Harness(self)
        git("commit", "--quiet", "--allow-empty", "-m", "later", cwd=h.project)
        git("push", "--quiet", str(h.remote), "HEAD:refs/heads/main", cwd=h.project)
        out = h.prepare(ok=False)
        self.assertIn("not the verified baseline", out["error"])
        self.assertIn("does not rebase", out["error"])

    def test_wrong_repository_or_account_is_refused(self):
        h = Harness(self)
        self.assertIn("404", h.prepare("h1", repo="acme/other", ok=False)["error"])
        self.assertIn("not the requested", h.prepare("h2", account="someone-else", ok=False)["error"])

    def test_an_existing_branch_is_never_reused_for_other_content(self):
        h = Harness(self)
        git("push", "--quiet", str(h.remote), f"{h.baseline}:refs/heads/taken", cwd=h.project)
        self.assertIn("already exists", h.prepare(head="taken", ok=False)["error"])
        self.assertEqual(h.remote_branches()["taken"], h.baseline)

    def test_an_incomplete_summary_or_a_private_path_is_refused(self):
        h = Harness(self)
        h.write_summary(goal_satisfaction={"status": "great"})
        self.assertIn("goal_satisfaction", h.prepare("h1", ok=False)["error"])
        h.write_summary(architecture=[{"claim": "Clean architecture.", "references": []}])
        self.assertIn("at least one reference", h.prepare("h2", ok=False)["error"])
        h.write_summary(architecture=[{"claim": "Touches the core.", "references": ["src/missing.py"]}])
        self.assertIn("neither a URL nor a path", h.prepare("h3", ok=False)["error"])
        h.write_summary(review_recipe=[f"Open {h.tmp}/run/delivery and look."])
        self.assertIn("private local paths", h.prepare("h4", ok=False)["error"])


class Publication(unittest.TestCase):
    def prepared(self, h):
        out = h.prepare()
        return Path(out["prepared"]), out["plan_sha256"]

    def test_authorized_publication_pushes_one_branch_and_opens_one_draft(self):
        h = Harness(self)
        handoff, plan_sha = self.prepared(h)
        self.assertIn("authorization", h.publish(handoff, ok=False)["error"])
        self.assertIn("does not name this plan", h.publish(handoff, "yes, publish it", ok=False)["error"])
        out = h.publish(handoff, f"I authorize publishing plan {plan_sha}.")
        self.assertTrue(out["published"], out)
        pr = out["pull_request"]
        plan = json.loads((handoff / "plan.json").read_text())
        self.assertEqual((pr["isDraft"], pr["baseRefName"], pr["headRefOid"]), (True, "main", plan["candidate"]["commit"]))
        self.assertEqual(h.remote_branches()[plan["head_branch"]], plan["candidate"]["commit"])
        state = h.load()
        self.assertEqual(len(state["pulls"]), 1)
        self.assertEqual(state["pulls"][0]["title"], TITLE)
        self.assertEqual(state["pulls"][0]["body"], (handoff / "pr-body.md").read_text())
        # An unchanged retry needs no new authorization and creates nothing new.
        again = h.publish(handoff)
        self.assertTrue(again["published"])
        self.assertEqual(len(h.load()["pulls"]), 1)
        self.assert_never(h)

    def test_a_lost_response_is_reconciled_without_a_duplicate(self):
        h = Harness(self)
        handoff, plan_sha = self.prepared(h)
        h.state["fail"] = {"lose_response": True}; h.save()
        out = h.publish(handoff, plan_sha)
        self.assertTrue(out["published"], out)
        self.assertEqual(out["create"]["create_exit"], 1)
        state = h.load(); state["fail"] = {}; h.state = state; h.save()
        self.assertTrue(h.publish(handoff)["published"])
        self.assertEqual(len(h.load()["pulls"]), 1)

    def test_push_succeeded_but_creation_failed_then_a_retry_creates_once(self):
        h = Harness(self)
        handoff, plan_sha = self.prepared(h)
        h.state["fail"] = {"create": True}; h.save()
        out = h.publish(handoff, plan_sha, ok=False)
        self.assertEqual(out["state"], "blocked")
        record = json.loads((handoff / "publication.json").read_text())
        self.assertIn("pushed", [e["state"] for e in record["events"]])
        state = h.load(); state["fail"] = {}; h.state = state; h.save()
        self.assertTrue(h.publish(handoff)["published"])
        self.assertEqual(len(h.load()["pulls"]), 1)
        pushes = [c for c in h.git_calls() if "push" in c]
        self.assertEqual(len(pushes), 1, pushes)

    def test_a_plan_changed_after_authorization_needs_a_new_one(self):
        h = Harness(self)
        handoff, plan_sha = self.prepared(h)
        (handoff / "pr-body.md").write_text("edited after authorization\n")
        self.assertIn("differs from the prepared body", h.publish(handoff, plan_sha, ok=False)["error"])
        self.assertEqual(h.load()["pulls"], [])

    def test_a_base_moved_after_preparation_blocks_publication(self):
        h = Harness(self)
        handoff, plan_sha = self.prepared(h)
        git("commit", "--quiet", "--allow-empty", "-m", "later", cwd=h.project)
        git("push", "--quiet", str(h.remote), "HEAD:refs/heads/main", cwd=h.project)
        out = h.publish(handoff, plan_sha, ok=False)
        self.assertIn("not the verified baseline", out["why"])
        self.assertEqual(set(h.remote_branches()), {"main"})

    def test_a_different_account_blocks_publication(self):
        h = Harness(self)
        handoff, plan_sha = self.prepared(h)
        h.state["login"] = "someone-else"; h.save()
        out = h.publish(handoff, plan_sha, ok=False)
        self.assertIn("does not switch accounts", out["why"])
        self.assertFalse(any(c[:2] == ["auth", "switch"] for c in h.gh_calls()))

    def test_an_external_change_or_a_closed_pr_is_never_overwritten(self):
        h = Harness(self)
        handoff, plan_sha = self.prepared(h)
        h.publish(handoff, plan_sha)
        plan = json.loads((handoff / "plan.json").read_text())
        # Someone pushes to the branch.
        work = h.tmp / "someone"; git("clone", "--quiet", str(h.remote), str(work))
        git("checkout", "--quiet", plan["head_branch"], cwd=work)
        git("-c", "user.name=X", "-c", "user.email=x@example.invalid", "commit", "--quiet", "--allow-empty", "-m", "external", cwd=work)
        git("push", "--quiet", "origin", plan["head_branch"], cwd=work)
        external = git("rev-parse", "HEAD", cwd=work)
        out = h.publish(handoff, ok=False)
        self.assertIn("changed externally", out["why"])
        self.assertEqual(h.remote_branches()[plan["head_branch"]], external)
        status = h.cli("pr-status", "--handoff", handoff, "--gh", h.gh)
        self.assertFalse(status["remote"]["head_is_verified_candidate"])
        self.assertIn("not the verified candidate", status["remote"]["warning"])
        # A closed PR is not recreated.
        state = h.load(); state["pulls"][0]["state"] = "CLOSED"; h.state = state; h.save()
        self.assertIn("does not recreate", h.publish(handoff, ok=False)["why"])
        self.assertEqual(len(h.load()["pulls"]), 1)
        self.assert_never(h)

    def assert_never(self, h):
        for call in h.gh_calls():
            joined = " ".join(call)
            for forbidden in ("pr merge", "pr ready", "pr review", "auth switch", "auth login",
                              "repo fork", "--reviewer", "--dry-run", "--fill", "pr close", "api --method POST",
                              "api --method DELETE", "api --method PATCH"):
                self.assertNotIn(forbidden, joined)
        for call in h.git_calls():
            if "push" in call:
                self.assertFalse(any(a in ("--force", "-f", "--force-with-lease", "--delete", "--mirror")
                                     or a.startswith("+") for a in call), call)
            self.assertFalse("config" in call and "--global" in call, call)


class Status(unittest.TestCase):
    def published(self):
        h = Harness(self)
        out = h.prepare()
        handoff = Path(out["prepared"])
        h.publish(handoff, out["plan_sha256"])
        plan = json.loads((handoff / "plan.json").read_text())
        return h, handoff, plan["candidate"]["commit"]

    def status(self, h, handoff):
        return h.cli("pr-status", "--handoff", handoff, "--gh", h.gh)

    def test_check_states_stay_distinct_and_belong_to_the_head(self):
        h, handoff, sha = self.published()
        self.assertEqual(self.status(h, handoff)["remote"]["checks"]["state"], "no checks observed")
        runs = [
            {"name": "unit", "status": "completed", "conclusion": "success", "head_sha": sha},
            {"name": "lint", "status": "completed", "conclusion": "failure", "head_sha": sha},
            {"name": "e2e", "status": "in_progress", "conclusion": None, "head_sha": sha},
            {"name": "deploy-preview", "status": "completed", "conclusion": "cancelled", "head_sha": sha},
            {"name": "docs", "status": "completed", "conclusion": "skipped", "head_sha": sha},
            # A run reported for another commit is not evidence for this head, whatever it says.
            {"name": "misfiled", "status": "completed", "conclusion": "success", "head_sha": "f" * 40}]
        h.state = h.load(); h.state["check_runs"] = {sha: runs, "0" * 40: [
            {"name": "old", "status": "completed", "conclusion": "success", "head_sha": "0" * 40}]}
        h.state["statuses"] = {sha: [{"context": "ci/legacy", "state": "pending"}]}
        h.state["workflow_runs"] = {sha: [
            {"name": "Validation", "event": "push", "status": "completed", "conclusion": "success", "head_sha": sha, "run_attempt": 1},
            {"name": "Validation", "event": "pull_request", "status": "completed", "conclusion": "failure", "head_sha": sha, "run_attempt": 1}]}
        h.save()
        s = self.status(h, handoff)
        checks = s["remote"]["checks"]
        self.assertEqual(checks["sha"], sha)
        self.assertEqual(checks["counts"], {"passed": 1, "failed": 1, "pending": 2, "cancelled": 1, "skipped": 1})
        self.assertNotIn("old", [i["name"] for i in checks["items"]])
        self.assertNotIn("misfiled", [i["name"] for i in checks["items"]])
        self.assertIn("still stands", s["remote"]["attention"])
        self.assertTrue(s["local"]["verification"]["project_check"]["passed"] is not None)
        self.assertFalse(s["remote"]["base_advanced"])
        self.assertIn("observed_at", checks)
        # Branch-head and merge-ref runs stay distinguishable although both report on the head.
        runs = {(r["tested"], r["conclusion"]) for r in checks["workflow_runs"]}
        self.assertEqual(runs, {("branch head", "success"), ("pull-request merge ref", "failure")})

    def test_unavailable_checks_and_an_advanced_base_are_reported(self):
        h, handoff, sha = self.published()
        h.state = h.load(); h.state["fail"] = {"checks": True}; h.save()
        git("commit", "--quiet", "--allow-empty", "-m", "later", cwd=h.project)
        git("push", "--quiet", str(h.remote), "HEAD:refs/heads/main", cwd=h.project)
        s = self.status(h, handoff)
        self.assertEqual(s["remote"]["checks"]["state"], "status unavailable")
        self.assertTrue(s["remote"]["base_advanced"])
        self.assertTrue(s["remote"]["head_is_verified_candidate"])

    def test_an_old_green_run_is_not_evidence_for_a_newer_head(self):
        h, handoff, sha = self.published()
        plan = json.loads((handoff / "plan.json").read_text())
        work = h.tmp / "someone"; git("clone", "--quiet", str(h.remote), str(work))
        git("checkout", "--quiet", plan["head_branch"], cwd=work)
        git("-c", "user.name=X", "-c", "user.email=x@example.invalid", "commit", "--quiet", "--allow-empty", "-m", "newer", cwd=work)
        git("push", "--quiet", "origin", plan["head_branch"], cwd=work)
        h.state = h.load(); h.state["check_runs"] = {sha: [{"name": "unit", "status": "completed", "conclusion": "success", "head_sha": sha}]}
        h.save()
        checks = self.status(h, handoff)["remote"]["checks"]
        self.assertNotEqual(checks["sha"], sha)
        self.assertEqual(checks["state"], "no checks observed")


if __name__ == "__main__":
    unittest.main()

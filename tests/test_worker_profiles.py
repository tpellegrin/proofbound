"""Worker profiles through the production path. Credential-free; no provider is ever reached.

What each group falsifies, rather than restates:

* resolution — a profile carrying a secret, a credential-bearing URL, a non-loopback host, a
  misspelt field or no limits is refused, every problem named at once;
* accounting — a local run is never priced through the DeepSeek default, zero-token calls are
  unknown rather than free, and only the allowance that consumes telemetry is blocked by its gaps;
* the front door — the profile is frozen at start, an edited profile file does not reach a resumed
  run, the launch never passes `--variant` to a local model or ambient credentials to its executor;
* teardown — the shared inference server is never an attempt's to stop;
* the real executor — pinned OpenCode completes a tool loop against a scripted loopback endpoint
  inside the real boundary, and a malformed tool call does not.
"""
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "evals"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import _worker_profiles as profiles                                        # noqa: E402
from _launch_budget import LaunchLedger, spend                             # noqa: E402
import _host_serial                                                        # noqa: E402

CLI = ROOT / "scripts" / "pb_workflow.py"


def setUpModule():
    _host_serial.serialise(__name__)


def tearDownModule():
    _host_serial.release()


def local_profile(path: Path, **overrides) -> Path:
    raw = {"format": profiles.PROFILE_FORMAT, "id": "local-test", "kind": profiles.LOCAL_KIND,
           "endpoint": "http://127.0.0.1:18080/v1", "model": "qwen3-coder",
           "limits": {"context": 32768, "output": 4096}, "tool_call": True}
    raw.update(overrides)
    path.write_text(json.dumps(raw))
    return path


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Resolution(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-profiles-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_the_default_requests_the_recorded_route_and_prices_what_now_serves_it(self):
        """Since 2026-09-10 the provider serves V4.1 Flash for the legacy name, billed at the Flash
        price. The request is unchanged; the interpretation of new runs is dated and explicit."""
        s = profiles.resolve()
        self.assertEqual((s["model"], s["variant"]), ("deepseek/deepseek-v4-flash", "high"))
        self.assertEqual(s["profile"]["revision"], "2026-09-24")
        self.assertEqual(s["billing"], {"basis": "dated-table", "table": "deepseek-2026-09-23",
                                        "price_model": "deepseek-flash"})
        self.assertEqual(s["provider"]["documented_serving"]["model_version"],
                         "DeepSeek-V4.1-Flash")
        self.assertIn("does not retain", s["provider"]["runtime_identity"])
        self.assertIn("weights", s["provider"]["runtime_identity"])
        self.assertEqual(s["credential"], {"auth_entry": "deepseek"})
        self.assertEqual(s["executor"]["sha256"], profiles.OPENCODE_SHA256)
        self.assertEqual(s["digest"], profiles.settings_digest(s))
        self.assertEqual(profiles.resolve()["digest"], s["digest"], "resolution is deterministic")

    def test_a_local_profile_resolves_without_variant_credential_or_price(self):
        s = profiles.resolve(local_profile(self.tmp / "p.json"))
        self.assertEqual(s["model"], "local/qwen3-coder")
        self.assertIsNone(s["variant"])
        self.assertIsNone(s["credential"]["auth_entry"])
        self.assertEqual(s["billing"]["basis"], profiles.NO_EXTERNAL_BILLING)
        self.assertEqual(s["network"]["mode"], "loopback-only")
        config = s["opencode_config"]
        self.assertEqual(config["enabled_providers"], ["local"])
        self.assertEqual(config["small_model"], "local/qwen3-coder",
                         "an auxiliary call must not name a hosted default model")
        self.assertEqual(config["provider"]["local"]["options"], {"baseURL":
                                                                  "http://127.0.0.1:18080/v1"})
        self.assertIn("OPENCODE_DISABLE_PROJECT_CONFIG", s["opencode_env"])

    def test_every_problem_is_named_and_no_secret_enters_identity(self):
        path = local_profile(self.tmp / "bad.json", api_key="sk-never",
                             endpoint="http://user:pw@127.0.0.1:8080/v1?key=x",
                             limits={"context": 10}, tool_call=False)
        with self.assertRaises(profiles.ProfileError) as caught:
            profiles.resolve(path)
        message = str(caught.exception)
        for fragment in ("api_key", "userinfo", "query", "limits must state exactly",
                         "tool_call must be true"):
            self.assertIn(fragment, message)
        self.assertNotIn("sk-never", message)
        self.assertNotIn(":pw@", message)

    def test_a_non_loopback_or_portless_endpoint_is_refused(self):
        for endpoint in ("http://10.0.0.5:8080/v1", "http://example.com:8080/v1",
                         "http://127.0.0.1/v1", "ftp://127.0.0.1:21/"):
            with self.subTest(endpoint=endpoint), self.assertRaises(profiles.ProfileError):
                profiles.resolve(local_profile(self.tmp / "p.json", endpoint=endpoint))

    def test_the_deepseek_route_is_not_selectable_by_file(self):
        path = self.tmp / "ds.json"
        path.write_text(json.dumps(profiles.BUILTIN[profiles.DEFAULT_PROFILE]))
        with self.assertRaises(profiles.ProfileError):
            profiles.resolve(path)

    def test_recorded_settings_that_were_edited_are_refused(self):
        settings = profiles.resolve(local_profile(self.tmp / "p.json"))
        config = {"worker_profile": settings, "model": settings["model"], "variant": None}
        profiles.of(config)
        tampered = json.loads(json.dumps(config))
        tampered["worker_profile"]["provider"]["endpoint"]["url"] = "http://127.0.0.1:9/v1"
        with self.assertRaises(profiles.ProfileError):
            profiles.of(tampered)
        mismatched = {**config, "model": "deepseek/deepseek-v4-flash"}
        with self.assertRaises(profiles.ProfileError):
            profiles.of(mismatched)

    def test_a_run_recorded_before_profiles_reads_as_it_was_recorded(self):
        legacy = profiles.of({"model": "deepseek/deepseek-v4-flash", "variant": "high"})
        self.assertTrue(legacy["legacy"])
        self.assertEqual(legacy["billing"], {"basis": "dated-table", "table": "deepseek-2026-09-09",
                                             "price_model": "deepseek-v4-flash"},
                         "a later price must never reinterpret a recorded run")
        self.assertEqual(legacy["profile"]["revision"], "2026-09-09")
        self.assertIsNone(legacy["resources"]["attempt_containment"],
                          "containment is not retrofitted onto runs started without it")
        other = profiles.of({"model": "opencode-go/deepseek-v4-flash", "variant": None})
        self.assertEqual(other["model"], "opencode-go/deepseek-v4-flash")
        self.assertIsNone(other["variant"])

    def test_differences_name_the_fields_that_moved(self):
        a = profiles.resolve(local_profile(self.tmp / "p.json"))
        b = profiles.resolve(local_profile(self.tmp / "p.json",
                                           limits={"context": 32768, "output": 2048}))
        fields = [d["field"] for d in profiles.differences(a, b)]
        self.assertIn("limits.output", fields)
        self.assertIn("profile.source_sha256", fields)


def session(db: Path, calls, *, stamp=None, session_id="s", title="t"):
    """A genuine OpenCode-shaped database: `calls` is a list of (input, output) per finished call."""
    stamp = stamp or int(time.time() * 1000)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("create table if not exists session (id text,title text)")
        conn.execute("create table if not exists message "
                     "(id text,session_id text,time_created integer,data text)")
        conn.execute("create table if not exists part (id text,message_id text,data text)")
        conn.execute("insert into session values (?,?)", (session_id, title))
        for n, (inp, out) in enumerate(calls):
            mid = f"{session_id}-m{n}"
            conn.execute("insert into message values (?,?,?,?)",
                         (mid, session_id, stamp + n, json.dumps({"role": "assistant"})))
            conn.execute("insert into part values (?,?,?)", (mid + "s", mid,
                                                             json.dumps({"type": "step-start"})))
            conn.execute("insert into part values (?,?,?)", (mid + "f", mid, json.dumps(
                {"type": "step-finish", "tokens": {"input": inp, "output": out,
                                                   "cache": {"read": 0, "write": 0}}})))
        conn.commit()


def attempt(run: Path, name="implementer-1", *, terminal=True, session_id="s"):
    event = run / "attempts" / name
    event.mkdir(parents=True)
    (event / "attempt.json").write_text(json.dumps({"started_at": "2026-09-21T00:30:00+00:00"}))
    (event / "launch-reservation.json").write_text("{}")
    if terminal:
        (event / "terminal.json").write_text(json.dumps({"status": "completed",
                                                         "session_id": session_id}))
    return event


class Accounting(unittest.TestCase):
    """Hand-computed: 1,000,000 uncached input tokens off-peak price to $0.22 on the DeepSeek table."""

    UNBILLED = {"basis": profiles.NO_EXTERNAL_BILLING, "claim": "none"}

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-accounting-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.run_root = self.tmp / "run"
        self.db = self.tmp / "worker.db"

    def off_peak(self):
        from datetime import datetime, timezone
        return int(datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)

    def test_the_default_prices_what_a_local_run_must_never_be_priced_as(self):
        attempt(self.run_root)
        session(self.db, [(1_000_000, 0)], stamp=self.off_peak())
        legacy = spend(self.run_root, self.db)
        self.assertEqual(legacy["derived"], 0.22, "the historical default is the DeepSeek table")
        local = spend(self.run_root, self.db, billing=self.UNBILLED)
        self.assertIsNone(local["derived"])
        self.assertTrue(local["complete"])
        self.assertIsNone(local["cost"]["amount"])
        self.assertNotIn("price_id", local["cost"])
        self.assertEqual(local["usage"]["input"], 1_000_000, "usage is still measured")

    def test_an_unknown_billing_basis_is_unknown_spend(self):
        attempt(self.run_root)
        session(self.db, [(10, 5)])
        got = spend(self.run_root, self.db, billing={"basis": "dated-table", "table": "other"})
        self.assertFalse(got["complete"])
        self.assertIsNone(got["derived"])

    def test_zero_token_calls_are_unknown_not_free_on_either_basis(self):
        """Observed: the pinned executor records zeros when a server omits usage."""
        attempt(self.run_root)
        session(self.db, [(0, 0)], stamp=self.off_peak())
        priced = spend(self.run_root, self.db)
        self.assertFalse(priced["complete"], "a $0 figure here would be an unmeasured call")
        self.assertIn("zero input and zero output", priced["claim"])
        unbilled = spend(self.run_root, self.db, billing=self.UNBILLED)
        self.assertFalse(unbilled["telemetry_complete"])
        self.assertTrue(unbilled["complete"], "nothing admitted consumes the counts")
        allowed = spend(self.run_root, self.db, billing=self.UNBILLED, output_token_allowance=100)
        self.assertFalse(allowed["complete"], "an allowance computed from telemetry cannot be "
                                              "settled without it")

    def test_an_attempt_without_a_terminal_record_blocks_whatever_the_worker_costs(self):
        attempt(self.run_root, terminal=False)
        session(self.db, [(10, 5)])
        got = spend(self.run_root, self.db, billing=self.UNBILLED)
        self.assertFalse(got["lifecycle_complete"])
        self.assertFalse(got["complete"])

    def test_the_ledger_freezes_its_basis_and_refuses_another(self):
        path = self.tmp / "ledger.json"
        ledger = LaunchLedger(path, ceiling=3, billing=self.UNBILLED)
        ledger.reserve(phase="p", task="t", role="implementer")
        self.assertEqual(json.loads(path.read_text())["billing"], self.UNBILLED)
        with self.assertRaises(ValueError):
            LaunchLedger(path, billing={"basis": "dated-table", "table": "deepseek-2026-09-09",
                                        "price_model": "deepseek-v4-flash"})
        legacy = self.tmp / "legacy.json"
        LaunchLedger(legacy, ceiling=3).reserve(phase="p", task="t", role="implementer")
        with self.assertRaises(ValueError):
            LaunchLedger(legacy, billing=self.UNBILLED)

    def test_the_output_allowance_refuses_the_next_launch_once_reached(self):
        attempt(self.run_root)
        session(self.db, [(100, 60)])
        path = self.tmp / "ledger.json"
        ledger = LaunchLedger(path, ceiling=5, billing=self.UNBILLED, output_token_allowance=50)
        slot = ledger.reserve(phase="p", task="t", role="reviewer")
        ledger.classify(slot["slot"], run_root=self.run_root,
                        event_dir=self.run_root / "attempts" / "implementer-1",
                        launcher_returncode=0, launcher_output="")
        verdict = ledger.admit(phase="p", task="t", role="reviewer", run_root=self.run_root,
                               db=self.db)
        self.assertFalse(verdict["admit"])
        self.assertIn("60 generated tokens", " ".join(verdict["why"]))
        self.assertIsNone(verdict["derived"])


FAKE = r'''#!PYTHON
import hashlib, json, os, pathlib, re, sqlite3, sys, time
args = sys.argv[1:]
db = pathlib.Path(os.environ['OPENCODE_DB'])
if args[:2] == ['session', 'list']:
    with sqlite3.connect(db) as conn:
        print(json.dumps([{'id': s, 'title': t} for s, t in conn.execute('select id,title from session')]))
    sys.exit()
pathlib.Path(__file__).with_name('observed.json').write_text(json.dumps(
    {'argv': args[:-1], 'env': sorted(os.environ)}))
title = args[args.index('--title') + 1]
sid = 'ses_' + hashlib.sha256(title.encode()).hexdigest()[:12]
report = pathlib.Path(re.search(r'^Report: (.+)$', args[-1], re.M).group(1))
report.write_text('# Stand-in report\n\nMechanics only.\n')
with sqlite3.connect(db) as conn:
    conn.execute('create table if not exists session (id text, title text)')
    conn.execute('create table if not exists message (id text, session_id text, time_created integer, data text)')
    conn.execute('create table if not exists part (id text, message_id text, data text)')
    conn.execute('insert into session values (?,?)', (sid, title))
    conn.execute('insert into message values (?,?,?,?)', (sid, sid, int(time.time()*1000), json.dumps({'role': 'assistant'})))
    for kind in ('step-start', 'step-finish'):
        conn.execute('insert into part values (?,?,?)', (sid + kind, sid, json.dumps({'type': kind, 'cost': 0, 'tokens': {'input': 10, 'output': 5, 'cache': {'read': 0, 'write': 0}}})))
'''


class FrontDoor(unittest.TestCase):
    """The public CLI with a local profile and a stand-in executor. Mechanics, never agent quality."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb local profile "))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.project = self.tmp / "project"
        self.project.mkdir()
        (self.project / ".gitignore").write_text("DeepSeekAndDestroy/\n__pycache__/\n")
        (self.project / "README.md").write_text("# p\n")
        for args in (("init", "-q"), ("config", "user.name", "T"),
                     ("config", "user.email", "t@example.invalid"), ("add", "."),
                     ("commit", "-qm", "i")):
            subprocess.run(["git", "-C", str(self.project), *args], check=True)
        self.fake = self.tmp / "bin" / "opencode"
        self.fake.parent.mkdir()
        self.fake.write_text(FAKE.replace("PYTHON", sys.executable))
        self.fake.chmod(0o755)
        self.profile = local_profile(self.tmp / "local.json")

    def cli(self, *args, ok=True, env=None):
        cp = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True,
                            text=True, env=env, stdin=subprocess.DEVNULL)
        if ok:
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        else:
            self.assertNotEqual(cp.returncode, 0, cp.stdout)
        return json.loads(cp.stdout)

    def start(self, profile=None):
        out = self.cli("start", "--project", self.project, "--goal", "Add greeting.",
                       "--check", f"{sys.executable} -c pass", "--executor", self.fake,
                       "--worker-profile", profile or self.profile)
        run = Path(out["run"])
        config = json.loads((run / "run-config.json").read_text())
        self.addCleanup(shutil.rmtree, Path(config["home"]).parent, True)
        return run, config

    def offline(self, run):
        """The canonical suite's test-only injection: exact stand-in, no boundary constructed."""
        path = run / "run-config.json"
        config = json.loads(path.read_text())
        config.update(mode="offline-test", auto_flag="",
                      policy={"aggregate_limit": 0, "reserve": 0, "launch_ceiling": 4,
                              "repair_cycles": 1})
        path.write_text(json.dumps(config))

    def test_doctor_is_actionable_without_an_endpoint_and_consults_no_credential(self):
        port = free_port()
        profile = local_profile(self.tmp / "down.json", endpoint=f"http://127.0.0.1:{port}/v1")
        got = self.cli("doctor", "--worker-profile", profile, "--executor", self.fake)
        self.assertFalse(got["ready"])
        problem = " ".join(got["problems"])
        self.assertIn("is not reachable", problem)
        self.assertIn("never falls back", problem)
        self.assertNotIn("DeepSeek credential", problem)
        self.assertEqual(got["readiness"]["credential_configured"], "not required")
        self.assertEqual(got["provider_requests"], 0)

    def test_doctor_lists_models_without_requesting_a_completion(self):
        from _stand_in_endpoint import StandInEndpoint
        with StandInEndpoint(model="qwen3-coder") as endpoint:
            profile = local_profile(self.tmp / "up.json", endpoint=endpoint.url)
            got = self.cli("doctor", "--worker-profile", profile, "--executor", self.fake)
            posts = [r for r in endpoint.requests if r["method"] == "POST"]
        self.assertTrue(got["readiness"]["endpoint"]["reachable"])
        self.assertTrue(got["readiness"]["endpoint"]["model_listed"])
        self.assertEqual(posts, [], "doctor must never generate")
        self.assertIn("not established", got["readiness"]["tool_loop"])

    def test_start_freezes_the_profile_and_writes_executor_config_outside_the_project(self):
        run, config = self.start()
        settings = config["worker_profile"]
        self.assertEqual(settings["digest"], profiles.settings_digest(settings))
        self.assertEqual((config["model"], config["variant"]), ("local/qwen3-coder", None))
        written = Path(config["opencode_config"]["path"])
        self.assertTrue(written.is_file())
        self.assertFalse(written.resolve().is_relative_to(self.project.resolve()))
        self.assertEqual(json.loads(written.read_text()), settings["opencode_config"])
        self.assertEqual(config["worker_env"]["OPENCODE_CONFIG"], str(written))
        state = json.loads((run / "state.json").read_text())
        self.assertEqual(state["worker_runtime"]["model"], "local/qwen3-coder")
        status = self.cli("status", "--run", run)
        self.assertEqual(status["worker"]["billing"], profiles.NO_EXTERNAL_BILLING)

    def test_an_edited_profile_file_does_not_reach_a_started_run(self):
        run, config = self.start()
        local_profile(self.profile, limits={"context": 32768, "output": 1024})
        error = self.cli("start", "--project", self.project, "--goal", "Add greeting.",
                         "--check", f"{sys.executable} -c pass", "--executor", self.fake,
                         "--worker-profile", self.profile, ok=False)["error"]
        self.assertIn("--worker-profile", error)
        self.assertIn("limits.output", error)
        self.assertIn("NOT applied", error)
        after = json.loads((run / "run-config.json").read_text())
        self.assertEqual(after["worker_profile"], config["worker_profile"])
        # And resume keeps using the recorded settings, not the file.
        self.assertEqual(self.cli("status", "--run", run)["worker"]["digest"],
                         config["worker_profile"]["digest"])

    def test_authorization_follows_the_billing_basis(self):
        run, _ = self.start()
        error = self.cli("authorize-spending", "--run", run, "--aggregate-limit", "1",
                         "--reserve", ".1", "--launch-ceiling", "3", "--owner-authorization",
                         "TEST", ok=False)["error"]
        self.assertIn("authorize-resources", error)
        self.assertFalse((run / "launch-ledger.json").exists())

    def test_the_launch_passes_no_variant_and_no_ambient_credential(self):
        run, _ = self.start()
        self.offline(run)
        env = {**os.environ, "DEEPSEEK_API_KEY": "sk-ambient-never", "OPENCODE_MODEL": "x",
               "OPENAI_API_KEY": "sk-ambient-never"}
        self.cli("continue", "--run", run, env=env)
        launched = self.cli("continue", "--run", run, env=env)["launch"]
        self.assertEqual(launched["returncode"], 0, launched)
        observed = json.loads(self.fake.with_name("observed.json").read_text())
        self.assertNotIn("--variant", observed["argv"])
        self.assertEqual(observed["argv"][observed["argv"].index("--model") + 1],
                         "local/qwen3-coder")
        for leaked in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "OPENCODE_MODEL"):
            self.assertNotIn(leaked, observed["env"])
        self.assertIn("OPENCODE_CONFIG", observed["env"])
        self.assertIn("OPENCODE_DISABLE_PROJECT_CONFIG", observed["env"])
        ledger = json.loads((run / "launch-ledger.json").read_text())
        self.assertEqual(ledger["billing"]["basis"], profiles.NO_EXTERNAL_BILLING)

    def test_a_moved_executor_config_refuses_before_the_executor(self):
        run, config = self.start()
        self.offline(run)
        Path(config["opencode_config"]["path"]).write_text('{"model": "opencode/big-pickle"}')
        self.cli("continue", "--run", run)
        refused = self.cli("continue", "--run", run)["launch"]
        self.assertFalse(refused["executor_reached"])
        self.assertIn("no longer matches", " ".join(refused["why"]))
        self.assertFalse((run / "launch-ledger.json").exists(), "no slot was consumed")

    def test_finish_derives_no_price_and_records_requested_and_observed_identity(self):
        run, _ = self.start()
        self.offline(run)
        self.cli("continue", "--run", run)
        self.cli("continue", "--run", run)
        report = self.tmp / "final.md"
        report.write_text("TEST ONLY stand-in; blocked delivery for accounting evidence.")
        delivery = Path(self.cli("finish", "--run", run, "--report", report,
                                 "--outcome", "blocked")["delivery"])
        usage = json.loads((delivery / "usage.json").read_text())
        self.assertIsNone(usage["derived"])
        self.assertEqual(usage["billing"]["basis"], profiles.NO_EXTERNAL_BILLING)
        handoff = json.loads((delivery / "handoff.json").read_text())
        self.assertEqual(handoff["worker_profile"]["model"], "local/qwen3-coder")
        self.assertIn("not observed", handoff["observed_worker_identity"]["note"])

    def test_a_run_recorded_before_profiles_still_resumes(self):
        run, _ = self.start(profile=profiles.DEFAULT_PROFILE)
        path = run / "run-config.json"
        config = json.loads(path.read_text())
        del config["worker_profile"]
        path.write_text(json.dumps(config))
        status = self.cli("status", "--run", run)
        self.assertTrue(status["worker"]["legacy_record"])
        self.assertEqual(status["worker"]["model"], "deepseek/deepseek-v4-flash")
        # The default's interpretation moved on (revision 2026-09-23); asking for it on a run
        # recorded under the old one names every field that would differ and applies none.
        error = self.cli("start", "--project", self.project, "--goal", "Add greeting.",
                         "--check", f"{sys.executable} -c pass", "--executor", self.fake,
                         ok=False)["error"]
        for field in ("profile.revision", "billing.table", "billing.price_model"):
            self.assertIn(field, error)
        self.assertEqual(self.cli("status", "--run", run)["worker"]["legacy_record"], True)


def parts_db(db: Path, calls, *, start=0, stamp=None):
    """Append finished calls to an OpenCode-shaped database: (reason, input, output) each."""
    stamp = stamp or int(time.time() * 1000)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("create table if not exists session (id text, title text)")
        conn.execute("create table if not exists message "
                     "(id text, session_id text, time_created integer, data text)")
        conn.execute("create table if not exists part (id text, message_id text, data text)")
        for n, (reason, inp, out) in enumerate(calls, start):
            mid = f"m{n:04d}"
            conn.execute("insert into message values (?,?,?,?)",
                         (mid, "s", stamp + n, json.dumps({"role": "assistant"})))
            conn.execute("insert into part values (?,?,?)",
                         (mid + "a", mid, json.dumps({"type": "step-start"})))
            conn.execute("insert into part values (?,?,?)", (mid + "b", mid, json.dumps(
                {"type": "step-finish", "reason": reason,
                 "tokens": {"input": inp, "output": out, "cache": {"read": 0, "write": 0}}})))
        conn.commit()


class AttemptContainment(unittest.TestCase):
    """The host counts what the executor does not bound. Real SQLite, synthetic calls."""

    CONTAINMENT = {"max_model_requests": 6, "max_consecutive_incomplete_responses": 3}

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-watch-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.db = self.tmp / "worker.db"
        from _supervised_launch import AttemptWatch
        self.Watch = AttemptWatch

    def test_earlier_attempts_in_the_same_database_are_not_counted(self):
        parts_db(self.db, [("unknown", 0, 0)] * 10)
        watch = self.Watch(self.db, containment=self.CONTAINMENT)
        self.assertIsNone(watch.check(), "the run's previous attempts are not this attempt")
        parts_db(self.db, [("tool-calls", 10, 5)], start=10)
        self.assertIsNone(watch.check())

    def test_a_run_of_incomplete_responses_is_stopped_and_a_complete_one_resets_it(self):
        watch = self.Watch(self.db, containment=self.CONTAINMENT)
        parts_db(self.db, [("unknown", 0, 0), ("unknown", 0, 0), ("stop", 10, 5),
                           ("unknown", 0, 0), ("unknown", 0, 0)])
        self.assertIsNone(watch.check(), "a complete response ends the run of incomplete ones")
        parts_db(self.db, [("unknown", 0, 0)], start=5)
        self.assertEqual(watch.check(), {"rule": "max_consecutive_incomplete_responses",
                                         "observed": 3, "limit": 3})

    def test_the_request_cap_counts_healthy_calls_too(self):
        watch = self.Watch(self.db, containment=self.CONTAINMENT)
        parts_db(self.db, [("tool-calls", 10, 5)] * 7)
        self.assertEqual(watch.check()["rule"], "max_model_requests")

    def test_derived_spend_during_the_attempt_is_bounded_by_the_room_left(self):
        """Hand-computed: 1,000,000 uncached input tokens off-peak at deepseek-2026-09-23 price to
        $0.15; with $0.10 of room the attempt is stopped."""
        import _worker_pricing
        from datetime import datetime, timezone
        off_peak = int(datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)
        watch = self.Watch(self.db, containment={"max_model_requests": 99},
                           spend_room=0.10, table=_worker_pricing.DEEPSEEK_2026_09_23,
                           price_model="deepseek-flash")
        parts_db(self.db, [("tool-calls", 400_000, 0)], stamp=off_peak)
        self.assertIsNone(watch.check(), "$0.06 is inside the room")
        parts_db(self.db, [("tool-calls", 600_000, 0)], start=1, stamp=off_peak)
        self.assertEqual(watch.check(), {"rule": "derived_spend_during_attempt",
                                         "observed": 0.15, "limit": 0.1})

    def test_no_database_yet_is_nothing_to_stop(self):
        self.assertIsNone(self.Watch(self.tmp / "absent.db",
                                     containment=self.CONTAINMENT).check())


@unittest.skipUnless(sys.platform == "darwin", "worker teardown is qualified on macOS only")
class SharedServerOwnership(unittest.TestCase):
    def test_teardown_stops_the_attempt_and_leaves_the_inference_server_running(self):
        from _attempt_teardown import stop_attempt
        tmp = Path(tempfile.mkdtemp(prefix="pb-owner-", dir="/private/tmp"
                                    if sys.platform == "darwin" else None))
        self.addCleanup(shutil.rmtree, tmp, True)
        runtime = tmp / "runtime-root-for-this-attempt"
        runtime.mkdir()
        run = tmp / "run"
        server = subprocess.Popen([sys.executable, "-m", "http.server", str(free_port()),
                                   "--bind", "127.0.0.1"], stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL, start_new_session=True)
        self.addCleanup(server.wait)
        self.addCleanup(server.kill)
        worker = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)",
                                   str(runtime)], start_new_session=True)
        self.addCleanup(worker.kill)
        # Reaped as it dies: in production the worker is never this process's own child, and an
        # unreaped zombie would read as a survivor.
        import threading
        threading.Thread(target=worker.wait, daemon=True).start()
        event = run / "attempts" / "implementer-1"
        event.mkdir(parents=True)
        (event / "attempt.json").write_text(json.dumps({"worker_pid": worker.pid}))
        time.sleep(0.5)
        result = stop_attempt(runtime, run, grace=2)
        self.assertTrue(result["stopped"], result)
        self.assertIsNotNone(worker.poll(), "the attempt's own process was stopped")
        self.assertIsNone(server.poll(), "the shared server is not the attempt's to stop")


@unittest.skipUnless(sys.platform == "darwin", "the worker boundary is macOS sandbox-exec")
class LoopbackBoundary(unittest.TestCase):
    def test_the_deepseek_boundary_text_is_unchanged(self):
        from _execution_view import Policy
        from _workflow_boundary import profile_text
        from _execution_view import _profile
        runtime, tools, project = Path("/r"), Path("/r/tools"), Path("/p")
        policy = Policy(network=True)
        self.assertEqual(profile_text(runtime, tools, project, policy),
                         _profile(runtime, tools, policy)
                         + '(allow file-write* (subpath "/p"))\n'
                         + '(deny file-write* (subpath "/r/tools"))\n'
                         + '(deny file-write* (literal "/r/boundary.sb"))\n')

    def test_loopback_only_allows_the_endpoint_and_refuses_anything_else(self):
        from _workflow_boundary import probe_network, UNROUTABLE_PROBE
        root = Path(tempfile.mkdtemp(prefix="pb-net-", dir="/private/tmp"))
        self.addCleanup(shutil.rmtree, root, True)
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(4)
        self.addCleanup(listener.close)
        port = listener.getsockname()[1]
        for loopback, expected in ((True, True), (False, False)):
            profile = root / f"p{int(loopback)}.sb"
            rule = '(allow network-outbound (remote ip "localhost:*"))' if loopback else ""
            profile.write_text(f"(version 1)(allow default)(deny network*){rule}")
            got = probe_network(profile, home=root, cwd=root,
                                endpoint={"host": "127.0.0.1", "port": port})
            with self.subTest(loopback=loopback):
                self.assertEqual(got["loopback_endpoint_allowed"], expected, got)
                self.assertTrue(got["non_loopback_denied"], got)
                self.assertEqual(got["checks"]["unroutable"]["errno"], 1)
        self.assertEqual(UNROUTABLE_PROBE[0], "192.0.2.1", "TEST-NET-1: never routed")


def pinned_executor():
    """The pinned OpenCode build, found by content. None where it is not installed."""
    import hashlib
    for candidate in (Path.home() / ".proofbound/executors/opencode-1.18.29-darwin-arm64/opencode",
                      shutil.which("opencode")):
        if candidate and Path(candidate).resolve().is_file():
            path = Path(candidate).resolve()
            if hashlib.sha256(path.read_bytes()).hexdigest() == profiles.OPENCODE_SHA256:
                return path
    return None


def sandbox_available():
    return Path("/usr/bin/sandbox-exec").exists() and subprocess.run(
        ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)", "/usr/bin/true"],
        capture_output=True).returncode == 0


@unittest.skipUnless(sys.platform == "darwin", "the worker boundary is macOS sandbox-exec")
class RealExecutorToolLoop(unittest.TestCase):
    """The pinned OpenCode against a scripted loopback endpoint, through `authorize-resources`.

    Skipped where the pinned build is not installed. What passes here is the protocol round trip
    and Proofbound's handling of it; the endpoint is a stand-in and no model is qualified.
    """

    def setUp(self):
        self.executor = pinned_executor()
        if self.executor is None:
            self.skipTest("the pinned OpenCode 1.18.29 build is not installed on this host")
        if not sandbox_available():
            self.skipTest("sandbox-exec cannot start inside this process")
        self.tmp = Path(tempfile.mkdtemp(prefix="pb-real-loop-", dir="/private/tmp"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.project = self.tmp / "project"
        self.project.mkdir()
        (self.project / ".gitignore").write_text("DeepSeekAndDestroy/\n__pycache__/\n")
        (self.project / "README.md").write_text("# p\n")
        for args in (("init", "-q"), ("config", "user.name", "T"),
                     ("config", "user.email", "t@example.invalid"), ("add", "."),
                     ("commit", "-qm", "i")):
            subprocess.run(["git", "-C", str(self.project), *args], check=True)

    def cli(self, *args):
        cp = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True,
                            text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
        return json.loads(cp.stdout)

    def loop(self, behaviour):
        from _stand_in_endpoint import StandInEndpoint
        requirements = self.project / "specs" / "CH-001" / "requirements.md"
        marker = f"TOOL LOOP {behaviour}"
        with StandInEndpoint(model="qwen3-coder", behaviour=behaviour, roles={
                "spec-author": {"files": {str(requirements): f"# R\n\n{marker}\n"}}}) as ep:
            profile = local_profile(self.tmp / "p.json", endpoint=ep.url)
            run = Path(self.cli("start", "--project", self.project, "--goal", "Write the marker.",
                                "--check", f"{sys.executable} -c pass", "--executor",
                                self.executor, "--worker-profile", profile,
                                "--deadline-seconds", 60)["run"])
            config = json.loads((run / "run-config.json").read_text())
            self.addCleanup(shutil.rmtree, Path(config["home"]).parent, True)
            self.cli("authorize-resources", "--run", run, "--launch-ceiling", 2,
                     "--owner-authorization", "TEST ONLY: stand-in endpoint mechanics")
            self.cli("continue", "--run", run)
            launched = self.cli("continue", "--run", run)["launch"]
            summary = ep.summary()
        runtime = Path(config["home"]).parent
        return {"run": run, "launch": launched, "endpoint": summary,
                "artifact": requirements.read_text(), "marker": marker,
                "network": json.loads((runtime / "network-probe.json").read_text()),
                "staged_auth": (Path(config["home"]) / ".local/share/opencode/auth.json").exists()}

    def test_a_well_formed_tool_loop_completes_inside_the_boundary(self):
        got = self.loop("well-formed")
        self.assertEqual(got["launch"]["returncode"], 0, got["launch"])
        self.assertIn(got["marker"], got["artifact"])
        self.assertGreaterEqual(got["endpoint"]["continuations_with_tool_results"], 1)
        self.assertFalse(got["endpoint"]["authorization_header_seen"])
        self.assertEqual(got["endpoint"]["max_tokens"], [4096])
        self.assertTrue(got["network"]["established"])
        self.assertFalse(got["staged_auth"])

    def test_a_malformed_tool_call_leaves_the_artifact_untouched(self):
        got = self.loop("malformed-arguments")
        self.assertNotIn(got["marker"], got["artifact"])

    def test_the_host_contains_a_response_loop_the_executor_does_not_bound(self):
        """Before containment the same endpoint drew 4,649 requests in 900 s; the executor's own
        `steps` limit was measured not to count them."""
        got = self.loop("interrupted")
        containment = got["launch"].get("containment") or {}
        self.assertEqual(containment.get("rule"), "max_consecutive_incomplete_responses",
                         got["launch"])
        self.assertLess(got["endpoint"]["requests"], 40)
        self.assertTrue(got["launch"]["unresolved"], "a stopped attempt is not a result")
        self.assertIn("unknown", containment["note"])
        self.assertEqual(got["launch"]["termination"]["survivors"], [])


if __name__ == "__main__":
    unittest.main()

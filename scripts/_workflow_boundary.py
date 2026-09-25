"""Construct and measure the supported macOS worker boundary, without provider requests."""
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
from _execution_view import Policy, _profile, SYSTEM_EXECS


def stage_interpreter(tools):
    """Make worker commands use the same supported interpreter as the coordinator."""
    shim = Path(tools) / "python3"
    shim.write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' "$@"\n')
    shim.chmod(0o755)


def profile_text(runtime, tools, project, policy, *, loopback_only=False, protected=(),
                 protected_trees=(), exec_trees=(), writable_trees=(), signal_same_sandbox=False):
    # The executor is a hard link: a write here would alter the host binary too.
    text = (_profile(runtime, tools, policy)
            + f'(allow file-write* (subpath "{project}"))\n'
            + f'(deny file-write* (subpath "{tools}"))\n'
            + f'(deny file-write* (literal "{runtime / "boundary.sb"}"))\n')
    for path in protected:
        # Executor configuration the worker must not rewrite for its own next launch.
        text += f'(deny file-write* (literal "{path}"))\n'
    for path in protected_trees:
        text += f'(deny file-write* (subpath "{path}"))\n'
    for path in exec_trees:
        # A declared toolchain's prepared dependencies only (`_toolchain`); writes there are denied.
        text += f'(allow process-exec (subpath "{path}"))\n'
    if signal_same_sandbox:
        # A process may signal only processes inside this same sandbox, such as its own workers.
        text += '(allow signal (target same-sandbox))\n'
    for path in writable_trees:
        # Tool caches inside a protected tree that a pnpm run's record names (`_package_manager`).
        # After the denies, because a later rule wins.
        text += f'(allow file-write* (subpath "{path}"))\n'
    if loopback_only:
        # After the policy's blanket `(deny network*)`: outbound connections to loopback only.
        # A later rule wins. What this does not stop is recorded with the profile's network claim.
        text += '(allow network-outbound (remote ip "localhost:*"))\n'
    return text


#: TEST-NET-1 (RFC 5737). Never routed, so probing it sends nothing anywhere real; under a
#: loopback-only boundary the connect must be refused by the sandbox itself (EPERM).
UNROUTABLE_PROBE = ("192.0.2.1", 443)


def probe_network(profile, *, home, cwd, endpoint):
    """Whether the boundary allows the loopback endpoint and refuses anything else. Sends no data."""
    program = '''import errno, json, socket, sys
out = {}
for label, host, port in json.loads(sys.argv[1]):
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    s = socket.socket(family, socket.SOCK_STREAM); s.settimeout(2)
    try:
        s.connect((host, port)); out[label] = {"connect": "established"}
    except OSError as exc:
        out[label] = {"connect": "failed", "errno": exc.errno, "name": errno.errorcode.get(exc.errno)}
    finally:
        s.close()
print(json.dumps(out))
'''
    targets = [["endpoint", "127.0.0.1" if endpoint["host"] == "localhost" else endpoint["host"],
                endpoint["port"]], ["unroutable", *UNROUTABLE_PROBE]]
    try:
        cp = subprocess.run(["/usr/bin/sandbox-exec", "-f", str(profile), sys.executable, "-c",
                             program, json.dumps(targets)], cwd=cwd,
                            env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
                            capture_output=True, text=True, timeout=20)
        checks = json.loads(cp.stdout) if cp.returncode == 0 else {}
    except (subprocess.TimeoutExpired, ValueError) as exc:
        return {"checks": {}, "unmeasured": str(exc)}
    # A probe that produced nothing observed nothing: neither claim is made from an empty result.
    endpoint_allowed = "endpoint" in checks and checks["endpoint"].get("errno") != 1
    other_denied = checks.get("unroutable", {}).get("errno") == 1
    return {"checks": checks, "loopback_endpoint_allowed": endpoint_allowed,
            "non_loopback_denied": other_denied, "established": endpoint_allowed and other_denied,
            "scope": "one loopback connect and one unroutable connect from a wrapped child; "
                     "no data sent. Says nothing about the coordinator, which is outside"}


def probe(profile, *, home, cwd, paths):
    # Absolute paths originate on the host. Never expand ~ after substituting HOME.
    program = '''import json, os, sys
out = {}
for label, path in json.loads(sys.argv[1]).items():
    try:
        if os.path.isdir(path):
            with os.scandir(path) as entries: next(entries, None)
        else:
            with open(path, "rb") as stream: stream.read(1)
        out[label] = {"path": path, "readable": True}
    except OSError as exc:
        out[label] = {"path": path, "readable": False, "errno": exc.errno}
print(json.dumps(out))
'''
    try:
        cp = subprocess.run(["/usr/bin/sandbox-exec", "-f", str(profile), sys.executable,
                             "-c", program, json.dumps({k: str(v) for k,v in paths.items()})],
                            cwd=cwd, env={"HOME": str(home), "PATH": "/usr/bin:/bin"},
                            capture_output=True, text=True, timeout=20)
        checks = json.loads(cp.stdout) if cp.returncode == 0 else {}
        return {"checks": checks, "returncode": cp.returncode,
                "error": cp.stderr[-500:] if cp.returncode else None,
                "scope": "sampled absolute paths from wrapped child only; no observation of host coordinator access"}
    except (subprocess.TimeoutExpired, ValueError) as exc:
        return {"checks": {}, "unmeasured": str(exc)}


def worker_env(c, *, tools=None):
    """The environment a worker's commands run with, as `_supervised_launch` builds it."""
    from _toolchain import worker_env as toolchain_env
    runtime = Path(c["home"]).parent
    extra = toolchain_env(c)
    path = [str(tools or runtime / "tools"), "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    if extra.get("PATH_PREFIX"):
        path.insert(0, extra.pop("PATH_PREFIX"))
    return {"LANG": "en_US.UTF-8", "TMPDIR": str(runtime / "tmp"), "HOME": c["home"],
            "PATH": os.pathsep.join(path), **extra}


def tooling_check(c, profile, project, *, timeout=600):
    """Run the project's check inside the boundary, unpaid, and say what happened."""
    import time
    from datetime import datetime, timezone
    started = time.monotonic()
    record = {"command": c["check_command"], "inside": str(profile),
              "checked_at": datetime.now(timezone.utc).isoformat()}
    try:
        cp = subprocess.run(["/usr/bin/sandbox-exec", "-f", str(profile),
                             *shlex.split(c["check_command"])], cwd=project, env=worker_env(c),
                            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {**record, "returncode": None, "passed": None,
                "seconds": round(time.monotonic() - started, 1),
                "note": f"did not finish within {timeout}s; unknown, not verified"}
    return {**record, "returncode": cp.returncode, "passed": cp.returncode == 0,
            "seconds": round(time.monotonic() - started, 1),
            "tail": (cp.stdout + cp.stderr).strip().splitlines()[-12:]}


def prepare(config):
    from _worker_profiles import of
    c = dict(config)
    settings = of(c)
    loopback = settings["network"]["mode"] == "loopback-only"
    runtime = Path(c["home"]).parent
    project = Path(c["paths"]["project"])
    harness = Path(__file__).resolve().parent.parent
    exe = Path(c["executor"]["path"])
    tools = runtime / "tools"; tools.mkdir(exist_ok=True)
    stage_interpreter(tools)
    staged = tools / "opencode"
    if not staged.exists(): os.link(exe, staged)  # preserve macOS code signature
    reads = [str(harness), str(project), str(Path(sys.prefix).resolve()),
             str(Path(sys.executable).resolve().parents[1]), "/opt/homebrew/Cellar", "/opt/homebrew/opt", "/opt/homebrew/lib"]
    # Escape profile paths before constructing a policy (quotes/newlines cannot become rules).
    if any('"' in x or '\n' in x or '\\' in x for x in [str(runtime), str(tools), *reads]):
        raise ValueError("sandbox profile paths cannot contain quotes, backslashes or newlines")
    policy = Policy(extra_reads=reads, system_execs=(*SYSTEM_EXECS, *reads[2:]), network=not loopback, notifications=True)
    profile = runtime / "boundary.sb"
    protected = [(c.get("opencode_config") or {}).get("path")] if loopback else []
    trees = []
    if settings["executor"].get("startup"):
        # The staged executor configuration and the catalogue cache: a write to either would change
        # how the next executor starts. Denied writes also make the executor's own writability
        # check fail, which is what stops its npm install (`_executor_startup`).
        from _executor_startup import boundary_rules
        for kind, path in boundary_rules(c["home"]):
            (trees if kind == "subpath" else protected).append(path)
    exec_trees, writable, signals = [], [], False
    if c.get("toolchain"):
        from _toolchain import boundary_rules
        rules = boundary_rules(c)
        trees += rules["deny_write"]
        exec_trees = rules["allow_exec"]
        writable = rules.get("allow_write", [])
        signals = rules.get("signal_same_sandbox", False)
    if any('"' in x or '\n' in x or '\\' in x for x in [*trees, *exec_trees, *writable]):
        raise ValueError("sandbox profile paths cannot contain quotes, backslashes or newlines")
    profile.write_text(profile_text(runtime, tools, project, policy, loopback_only=loopback,
                                    protected=[p for p in protected if p],
                                    protected_trees=trees, exec_trees=exec_trees,
                                    writable_trees=writable, signal_same_sandbox=signals))
    c["boundary_profile"] = str(profile)
    c["executor"] = {**c["executor"], "path": str(staged)}
    observed = probe(profile, home=c["home"], cwd=project,
                     paths={"host_home": Path.home(), "staged_home": Path(c["home"]), "project": project})
    from dsd_state import atomic_json
    atomic_json(runtime / "boundary-probe.json", observed)
    checks = observed["checks"]
    if not checks or checks["host_home"].get("readable") or checks["host_home"].get("errno") not in (1, 13) or not checks["project"]["readable"] or not checks["staged_home"]["readable"]:
        raise ValueError("boundary probe did not establish expected deny/allow results; see " + str(runtime / "boundary-probe.json"))
    if loopback:
        network = probe_network(profile, home=c["home"], cwd=project,
                                endpoint=settings["provider"]["endpoint"])
        atomic_json(runtime / "network-probe.json", network)
        if not network.get("established"):
            raise ValueError("boundary probe did not establish loopback-only network access; see "
                             + str(runtime / "network-probe.json"))
    if c.get("toolchain"):
        # Project-tooling readiness is established only here, by running the project's own check
        # inside this boundary with the worker's environment — before any credential is staged.
        c["toolchain"] = {**c["toolchain"], "boundary_check": tooling_check(c, profile, project)}
        atomic_json(runtime / "project-tooling-check.json", c["toolchain"]["boundary_check"])
    entry = settings["credential"]["auth_entry"]
    if entry is None:
        # Nothing staged, deliberately: a local worker needs no cloud credential, and an absent
        # auth file cannot be picked up by a provider the profile did not name.
        return c
    credential = Path(c["home"]) / ".local/share/opencode/auth.json"
    credential.parent.mkdir(parents=True, exist_ok=True)
    # Minimize staged credentials: retain only this backend's entry.
    auth = json.loads((Path.home() / ".local/share/opencode/auth.json").read_text())
    if entry not in auth:
        raise ValueError(f"the worker profile needs the {entry!r} credential entry, which is not "
                         "configured; no provider request was made")
    with credential.open("w") as stream: json.dump({entry: auth[entry]}, stream)
    credential.chmod(0o600)
    return c

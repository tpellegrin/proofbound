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


def profile_text(runtime, tools, project, policy):
    # The executor is a hard link: a write here would alter the host binary too.
    return (_profile(runtime, tools, policy)
            + f'(allow file-write* (subpath "{project}"))\n'
            + f'(deny file-write* (subpath "{tools}"))\n'
            + f'(deny file-write* (literal "{runtime / "boundary.sb"}"))\n')


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


def prepare(config):
    c = dict(config)
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
    policy = Policy(extra_reads=reads, system_execs=(*SYSTEM_EXECS, *reads[2:]), network=True, notifications=True)
    profile = runtime / "boundary.sb"
    profile.write_text(profile_text(runtime, tools, project, policy))
    c["boundary_profile"] = str(profile)
    c["executor"] = {**c["executor"], "path": str(staged)}
    observed = probe(profile, home=c["home"], cwd=project,
                     paths={"host_home": Path.home(), "staged_home": Path(c["home"]), "project": project})
    from dsd_state import atomic_json
    atomic_json(runtime / "boundary-probe.json", observed)
    checks = observed["checks"]
    if not checks or checks["host_home"].get("readable") or checks["host_home"].get("errno") not in (1, 13) or not checks["project"]["readable"] or not checks["staged_home"]["readable"]:
        raise ValueError("boundary probe did not establish expected deny/allow results; see " + str(runtime / "boundary-probe.json"))
    credential = Path(c["home"]) / ".local/share/opencode/auth.json"
    credential.parent.mkdir(parents=True, exist_ok=True)
    # Minimize staged credentials: retain only this backend's entry.
    auth = json.loads((Path.home() / ".local/share/opencode/auth.json").read_text())
    with credential.open("w") as stream: json.dump({"deepseek": auth["deepseek"]}, stream)
    credential.chmod(0o600)
    return c

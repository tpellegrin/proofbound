#!/usr/bin/env python3
"""A runtime whose evidence surface is constructed, and an exposure probe that measures it.

The source checkout holds this slice's own answers: expected verdicts in `case.json`, reference
implementations in `_implementations.py` and `_checker_corpus.py`, a validation record, the
experiment plan, and two recovery-probe write-ups. A coordinator or worker that can read those is
not recovering anything — it is reading the key. Moving the fixture elsewhere does not help while
the original checkout is still reachable, and *asking* an agent not to look is not a restriction.

So the runtime is built from an allowlist and bounded by the mechanism this repository already
has: `_semantic_view`'s constructed evidence surface. Everything outside the view is denied, the
allowlist says what goes in, and `probe()` then **measures** what is reachable from inside rather
than trusting the construction.

**What this is and is not.** It is an evidence boundary, not a security boundary — the same
disclaimer `_semantic_view` makes. Its scope is *processes launched inside the view*: the harness,
the workers, and any command a coordinator runs through the wrapper. A coordinator whose own tool
calls run on the host is outside it, and `describe()` says so rather than implying otherwise.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "evals"))

import _hermetic                      # noqa: E402
import _live                          # noqa: E402
import _semantic_view                 # noqa: E402

#: What a coordinator legitimately needs: the harness, its worker doctrine, the operational
#: documents, the authority artifacts, and the tooling that reads them. Nothing that answers the
#: question being asked.
HARNESS_ALLOWLIST = (
    "scripts", "worker", "templates",
    "SKILL.md", "AGENTS.md", "WORKSPACE.md", "OPENCODE.md", "PROMPTS.md", "COMPACTION.md",
    "CONTRIBUTING.md", "CONFIG.example.md", "HARNESS.md", "CLAUDE.md", "CODEX.md", "KILO.md",
)

#: From the evaluation tree, only what the operational path imports.
EVALS_ALLOWLIST = ("_pricing.py", "_profile.py")

SLICE_ALLOWLIST = (
    "pb_slice.py", "_live.py", "_guard.py", "_launch_paths.py", "_obligations.py", "_checker.py",
    "_fixtures.py", "goal.md", "contracts",
)

#: Never staged. Each would answer some part of what the run is supposed to establish.
WITHHELD = (
    "_implementations.py",          # working implementations of the task under test
    "_checker_corpus.py",           # more of the same, plus expected verdicts
    "cases/coherent-requirements/case.json",
    "cases/contradictory-requirements/case.json",
    "README.md", "next-live-experiment.md", "probe-observations.md",
)


def _stage_harness(destination: Path) -> "dict[str, Any]":
    destination.mkdir(parents=True, exist_ok=True)
    staged: "list[str]" = []
    for name in HARNESS_ALLOWLIST:
        source = ROOT / name
        if not source.exists():
            continue
        target = destination / name
        if source.is_dir():
            shutil.copytree(source, target,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copyfile(source, target)
        staged.append(name)
    evals = destination / "evals"
    evals.mkdir(parents=True, exist_ok=True)
    for name in EVALS_ALLOWLIST:
        shutil.copyfile(ROOT / "evals" / name, evals / name)
        staged.append(f"evals/{name}")
    slice_dir = evals / "authority_slice"
    slice_dir.mkdir(parents=True, exist_ok=True)
    for name in SLICE_ALLOWLIST:
        source = HERE / name
        target = slice_dir / name
        if source.is_dir():
            shutil.copytree(source, target,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copyfile(source, target)
        staged.append(f"evals/authority_slice/{name}")
    # The requirements document is authority the coordinator and the checker both need. Its
    # answer key, which sits beside it in the source tree, is not staged.
    case = slice_dir / "cases" / "coherent-requirements"
    case.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERE / "cases" / "coherent-requirements" / "requirements.md",
                    case / "requirements.md")
    staged.append("evals/authority_slice/cases/coherent-requirements/requirements.md")
    return {"staged": sorted(staged), "withheld": sorted(WITHHELD)}


def sensitive_paths() -> "list[Path]":
    """The files whose content must not be reachable from inside a subject runtime."""
    out = [HERE / name for name in WITHHELD]
    out.append(ROOT / "evals" / "results" / "authority-slice-validation-v1.json")
    return [p for p in out if p.exists()]


def sensitive() -> "list[Any]":
    """The same files, as the hermeticity scan recognises them: by content, never by name."""
    import hashlib
    paths = sensitive_paths()
    return [_hermetic.Sensitive(
        "evaluator-answers",
        stems={p.name for p in paths},
        digests={hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})]


def build(*, mode: str = _live.REHEARSAL, root: "str | Path | None" = None,
          executor: "str | Path | None" = None) -> "dict[str, Any]":
    """Construct the runtime, prepare the experiment inside it, and measure what it exposes."""
    root = Path(root) if root else (_semantic_view.DEFAULT_PARENT
                                    / f"pb-handoff-1-{os.getpid()}")
    root = Path(root).resolve()
    if root.exists():
        raise SystemExit(f"{root} already exists; refusing to reuse a runtime")
    tools_root = root.parent / f"{root.name}-tools"
    tools_root.mkdir(parents=True, exist_ok=True)

    tools: "list[_semantic_view.Tool]" = []
    if mode == _live.LIVE:
        source = Path(executor) if executor else _live.PINNED_EXECUTOR
        tools.append(_semantic_view.Tool("opencode", source))

    # The interpreter the run was prepared on has to be the interpreter inside the boundary. A
    # dress rehearsal found the alternative the hard way: with only system paths exposed, `python3`
    # resolved to Apple's shim, which dies trying to write an `xcrun` cache into the per-user
    # temporary directory the boundary denies — and the only interpreter that ran at all was a 3.9
    # the repository does not support. Exposing the interpreter's own prefix is a capability, not
    # an evidence leak: no experiment material lives there.
    interpreter_prefix = str(Path(sys.prefix).resolve())
    interpreter_root = str(Path(sys.executable).resolve().parents[1])
    exposure = sorted({interpreter_prefix, interpreter_root, "/opt/homebrew/Cellar",
                       "/opt/homebrew/opt", "/opt/homebrew/lib"})
    exposure = [p for p in exposure if Path(p).exists()]
    policy = _semantic_view.Policy(
        tools=tools,
        extra_reads=exposure,
        system_execs=(*_semantic_view.SYSTEM_EXECS, *exposure),
        network=(mode == _live.LIVE),        # the executor reaches a provider; nothing else does
        notifications=(mode == _live.LIVE),  # opencode will not start without FSEvents
    )
    # Tools are staged by **hard link**, exactly as `_semantic_view.semantic_view` does it: a copied
    # macOS binary loses its code signature and is killed on exec. This builder constructs the view
    # directly — it has to outlive a context manager, since a coordinator runs many commands against
    # it — so the staging the context manager would have done happens here instead.
    for tool in policy.tools:
        staged = tools_root / tool.name
        if staged.exists():
            staged.unlink()
        try:
            os.link(tool.source, staged)
        except OSError as exc:
            raise SystemExit(
                f"tool {tool.name!r} at {tool.source} cannot be staged by hard link "
                f"({exc.strerror}). A copy would lose its code signature and be killed on exec; "
                f"move the tool onto the same volume as {tools_root.parent}.") from exc

    view = _semantic_view.View(root, tools_root, policy)

    # `python3` on the view's PATH must be the recorded interpreter, not whatever the system
    # resolves first. A shim rather than a copy: the interpreter is a framework, not a file.
    shim = tools_root / "python3"
    shim.write_text(f'#!/bin/sh\nexec "{Path(sys.executable).resolve()}" "$@"\n', encoding="utf-8")
    shim.chmod(0o755)

    harness = _stage_harness(view.workspace / "harness")
    staged_executor = (tools_root / "opencode") if mode == _live.LIVE else None

    # The executor's credential is the one thing a live run needs from outside the boundary. It is
    # staged into the view's own home rather than the boundary being widened to reach the real one,
    # so what the subject can read is still exactly what was placed there.
    credential = None
    if mode == _live.LIVE:
        source = Path.home() / ".local/share/opencode/auth.json"
        if not source.is_file():
            raise SystemExit(f"no executor credential at {source}; a live run cannot start")
        view.stage_file(source, "home/.local/share/opencode/auth.json")
        credential = "home/.local/share/opencode/auth.json"

    prepared = _live.prepare(view.workspace / "work", mode=mode, executor=staged_executor,
                             home=view.home, harness_root=view.workspace / "harness",
                             identities_into=root.parent / f"{root.name}.identities.json")

    wrapper = root.parent / f"{root.name}-run"
    environment = view.environment()
    wrapper.write_text(
        "#!/bin/sh\n"
        "# Run one command inside the constructed evidence surface. Everything outside it is\n"
        "# denied: this is what makes the boundary a measurement rather than a request.\n"
        "#\n"
        "# The environment is assembled, not inherited: a caller's own working directory and\n"
        "# temporary directory are outside the boundary, and a shell that starts in one cannot\n"
        "# even resolve where it is.\n"
        f'cd "{view.workspace / "work"}" || exit 1\n'
        f'PATH="{environment["PATH"]}"; export PATH\n'
        f'HOME="{environment["HOME"]}"; export HOME\n'
        f'TMPDIR="{environment["TMPDIR"]}"; export TMPDIR\n'
        f'exec /usr/bin/sandbox-exec -f "{view.profile_path}" /bin/sh -c "$@"\n',
        encoding="utf-8")
    wrapper.chmod(0o755)

    described = {
        "mode": mode,
        "root": str(root),
        "tools_root": str(tools_root),
        "policy_identity": policy.identity(),
        "profile": str(view.profile_path),
        "wrapper": str(wrapper),
        "harness_root": str(view.workspace / "harness"),
        "interpreter": {"executable": sys.executable, "version": sys.version.split()[0],
                        "shim": str(shim), "exposed_prefixes": exposure},
        "workdir": str(view.workspace / "work"),
        "environment": environment,
        "harness": harness,
        "credential_staged": credential,
        "prepared": {k: v for k, v in prepared.items() if k != "seeded_steps"},
        "boundary": ("processes launched inside the view. A coordinator whose own tool calls run "
                     "on the host is outside it; what it actually accessed is reported rather "
                     "than assumed"),
    }
    (root / "runtime.json").write_text(json.dumps(described, indent=2, sort_keys=True) + "\n",
                                       encoding="utf-8")
    return described


def probe(runtime: "dict[str, Any] | str | Path") -> "dict[str, Any]":
    """Measure the boundary from inside: what can a process in this runtime actually read?

    Ordinary access paths, not a token check: the original checkout by absolute path, a parent
    directory listing, a `find` for the withheld names, and the home directory that holds
    credentials.
    """
    if not isinstance(runtime, dict):
        runtime = json.loads((Path(runtime) / "runtime.json").read_text(encoding="utf-8"))
    profile = runtime["profile"]
    env = dict(runtime["environment"])
    cwd = runtime["workdir"]

    def inside(script: str, timeout: int = 45) -> "dict[str, Any]":
        import subprocess
        try:
            done = subprocess.run(
                ["/usr/bin/sandbox-exec", "-f", profile, "/bin/sh", "-c", script],
                cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            # A probe that runs out of time has measured nothing, and saying so is not the same as
            # saying the path was denied.
            return {"returncode": None, "stdout": "", "stderr": "",
                    "unmeasured": f"the probe did not finish within {timeout}s"}
        return {"returncode": done.returncode,
                "stdout": done.stdout.strip()[:400],
                "stderr": done.stderr.strip()[:200]}

    checks = {
        "source_checkout_readable": inside(f"cat {ROOT}/README.md 2>&1 | head -1"),
        "answer_key_readable": inside(
            f"cat {HERE}/cases/coherent-requirements/case.json 2>&1 | head -1"),
        "reference_implementation_readable": inside(f"cat {HERE}/_implementations.py 2>&1 | head -1"),
        "checker_corpus_readable": inside(f"cat {HERE}/_checker_corpus.py 2>&1 | head -1"),
        "experiment_plan_readable": inside(f"cat {HERE}/next-live-experiment.md 2>&1 | head -1"),
        "real_home_readable": inside("ls ~/.local/share/opencode 2>&1 | head -1"),
        "search_finds_withheld_names": inside(
            "find /Users /private/tmp -maxdepth 6 \\( -name 'case.json' -o "
            "-name '_implementations.py' \\) 2>/dev/null | head -5"),
        "harness_readable": inside(f"head -1 {runtime['harness_root']}/AGENTS.md 2>&1"),
        "interpreter_available": inside(
            "python3 -c 'import sys; print(sys.version.split()[0])'"),
        "interpreter_writes_to_a_pipe": inside("python3 -c 'print(1)' | head -1"),
        "cat_to_a_pipe": inside("cat /etc/hosts | head -1"),
    }
    reachable = [name for name, r in checks.items()
                 if name.endswith("_readable") and r.get("returncode") == 0
                 and "not permitted" not in r["stdout"].lower()
                 and "no such file" not in r["stdout"].lower()]
    checks["search_finds_withheld_names"]["found_paths"] = [
        line for line in checks["search_finds_withheld_names"]["stdout"].splitlines() if line]
    leaked = [n for n in reachable if n not in ("harness_readable",)]
    scan = _hermetic.scan([Path(runtime["root"])], sensitive(), declared=[])
    return {
        "checks": checks,
        "reachable_from_inside": reachable,
        "withheld_material_reachable": leaked,
        "boundary_holds": not leaked and not scan.get("findings"),
        "hermeticity": {"findings": scan.get("findings", []),
                        "claim": scan.get("claim")},
        "note": "measured by running ordinary commands inside the view, not by inspecting the "
                "profile text",
    }

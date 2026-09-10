#!/usr/bin/env python3
"""A per-slot execution environment built from declared inputs rather than inherited from the host.

An evaluated agent's evidence is whatever it can find, not whatever was placed in its working
directory. A calibration run proved the difference expensively: an arm whose prepared workspace
deliberately contained no implementation source ran one host-wide search, found a copy left by an
earlier materialisation, and read it. The workspace was exactly as designed and the treatment had
already failed.

So the environment stops being inherited. Every slot gets a **semantic view**: a directory tree the
control plane constructs, an environment assembled from an allowlist rather than copied, a fresh
home and scratch, staged tools, and a filesystem policy under which ordinary discovery sees that tree
and the system resources tools need — and nothing else the evaluator happens to keep on the same
machine.

**Concept and mechanism are separate.** The concept is a constructed evidence surface. The mechanism
here is the macOS sandbox profile, chosen because it delivers the property on this platform without
changing the interpreter the fixture was compiled by. It is deprecated by Apple, it is not portable,
and a Linux implementation would use something else without changing anything above.

**What this is not.** Not a security boundary. No claim about malicious code, kernel isolation,
`/proc`, side channels, or an agent trying to escape. Discovery commands are not blocked — `find`,
`grep` and absolute reads all work, because they are how agents behave and how the evidence that
motivated this was produced. What changes is what they find.

**Generic by construction.** This module knows about directories, tools, environment variables and
policies. What is sensitive, what a workspace contains, which runtime to stage and what an arm
declares are all supplied by the experiment that uses it.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence

# The view is built here rather than in the per-user temporary directory, for one mechanical reason:
# a subject's `find /` has to be able to descend into its own workspace, and the per-user directory
# is precisely the place the boundary must deny. The parent stays listable and its siblings stay
# unreadable, and that distinction is measured rather than assumed.
DEFAULT_PARENT = Path("/private/tmp")
VIEW_PREFIX = "pb-sem-"
TOOLS_PREFIX = "pb-tool-"

# System locations tools need in order to start at all. None of them holds experiment evidence, and
# a probe asserts that rather than trusting it.
SYSTEM_READS = (
    "/usr/lib", "/usr/bin", "/bin", "/sbin", "/usr/sbin", "/System", "/usr/share",
    "/Library/Developer", "/private/var/db/dyld", "/private/var/select", "/private/etc", "/dev",
)
SYSTEM_EXECS = ("/usr/bin", "/bin", "/sbin", "/usr/sbin", "/System", "/Library/Developer")
# Directories that must be listable for a path to be walked down to the view. Listable, not readable:
# their contents stay denied.
TRAVERSAL = ("/", "/usr", "/Library", "/private", "/private/tmp", "/tmp", "/private/var", "/var",
             "/etc")

# Everything a shell, an interpreter and the ordinary search tools were measured to need. The list is
# short because it was derived by running them under an empty environment and adding only what
# failed without it.
BASE_PATH = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")

SANDBOX = "/usr/bin/sandbox-exec"

# Slots this process made and could not remove. Destruction is meant to be total, and a failure to
# achieve it is recorded rather than swallowed: `ignore_errors` hid one for long enough that
# forty-five empty directories accumulated before anything noticed.
_UNREMOVED: set = set()


def unremoved() -> tuple[Path, ...]:
    """Slots this process created and failed to destroy."""
    return tuple(sorted(_UNREMOVED))


class ViewError(RuntimeError):
    """The semantic view could not be constructed as declared."""


class Tool:
    """One executable staged for the subject, identified by its bytes.

    Staged outside the writable root, so the subject can run it and the policy can refuse to let it
    be rewritten. Two platform facts shape how:

    A copied system binary will not run. macOS validates code signatures, a copy does not carry one,
    and the kernel kills the process — measured, `SIGKILL` with no output. So staging is by hard
    link, which preserves the inode and the signature, and a source on another volume is refused
    loudly rather than copied into something that dies on exec.

    The staged link is never `chmod`-ed. It shares an inode with the control plane's own file, so
    changing its mode would change that file's mode. Write is refused by the policy instead, which
    is where a rule about what the subject may do belongs.

    Tools that already live somewhere the policy allows — the system directories — are not staged at
    all. Staging exists for executables under a path the boundary denies.
    """

    def __init__(self, name: str, source: str | Path):
        self.name = name
        self.source = Path(source)
        if not self.source.is_file():
            raise ViewError(f"tool {name!r} not found at {self.source}")
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def describe(self) -> dict[str, str]:
        return {"name": self.name, "sha256": self.digest, "mode": "read-execute"}


class Policy:
    """What kind of boundary this is — as against which instance of it is running.

    Identity is taken over this and never over the slot: the random path, the process and the files
    that happen to exist are the instance. Two slots of one experiment are the same boundary; a slot
    that exposes one more root is a different one.
    """

    def __init__(self, *, tools: Sequence[Tool] = (), env: dict[str, str] | None = None,
                 system_reads: Sequence[str] = SYSTEM_READS,
                 system_execs: Sequence[str] = SYSTEM_EXECS,
                 traversal: Sequence[str] = TRAVERSAL,
                 extra_reads: Sequence[str] = (), network: bool = False,
                 declared: Sequence[str] = ()):
        self.tools = tuple(tools)
        self.env = dict(env or {})
        self.system_reads = tuple(system_reads)
        self.system_execs = tuple(system_execs)
        self.traversal = tuple(traversal)
        self.extra_reads = tuple(extra_reads)
        self.network = bool(network)
        self.declared = tuple(declared)

    def identity(self) -> str:
        """A digest of the rule, stable across slots and sensitive to what the subject can reach."""
        payload = {
            "tools": sorted(t.describe() for t in self.tools),
            "env_keys": sorted(self.env),
            "system_reads": sorted(self.system_reads),
            "system_execs": sorted(self.system_execs),
            "traversal": sorted(self.traversal),
            "extra_reads": sorted(self.extra_reads),
            "network": self.network,
            "declared": sorted(self.declared),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _profile(root: Path, tools: Path, policy: Policy) -> str:
    """The sandbox profile for one instance, generated from the policy.

    Written out rather than kept as a template with holes, so the text that was enforced can be
    retained beside the run that used it.
    """
    lines = [
        "(version 1)",
        '(import "system.sb")',
        "(allow process-fork)",
        "(deny file-read* file-write*)",
        f'(allow file-read* file-write* (subpath "{root}"))',
        f'(allow file-read* (subpath "{tools}"))',
        "(allow file-read* " + " ".join(f'(subpath "{p}")' for p in policy.system_reads) + ")",
        "(allow file-read* " + " ".join(f'(literal "{p}")' for p in policy.traversal) + ")",
    ]
    if policy.extra_reads:
        lines.append("(allow file-read* "
                     + " ".join(f'(subpath "{p}")' for p in policy.extra_reads) + ")")
        # Exposing a directory implies being able to walk down to it. Path resolution reads every
        # ancestor, so an exposure whose parents are denied is an exposure that cannot be reached —
        # measured as `realpath: Operation not permitted` on an interpreter that was allowed.
        ancestors = sorted({str(a) for root in policy.extra_reads
                            for a in Path(root).parents} - set(policy.traversal))
        if ancestors:
            lines.append("(allow file-read-metadata "
                         + " ".join(f'(literal "{a}")' for a in ancestors) + ")")
    lines += [
        '(allow file-write-data (literal "/dev/null") (literal "/dev/stdout") '
        '(literal "/dev/stderr") (literal "/dev/dtracehelper"))',
        "(deny process-exec)",
        "(allow process-exec " + " ".join(f'(subpath "{p}")' for p in policy.system_execs)
        + f' (subpath "{root}") (subpath "{tools}"))',
    ]
    lines.append("(allow network*)" if policy.network else "(deny network*)")
    return "\n".join(lines) + "\n"


class View:
    """One constructed slot. Created by `semantic_view`, destroyed when its block ends."""

    #: Directories the subject owns. Every one is fresh, writable and inside the boundary.
    AREAS = ("workspace", "runtime", "data", "tmp", "home", "session")

    def __init__(self, root: Path, tools_root: Path, policy: Policy):
        self.root = root
        self.tools_root = tools_root
        self.policy = policy
        for area in self.AREAS:
            setattr(self, area, root / area)
            getattr(self, area).mkdir(parents=True, exist_ok=True)
        self.profile_path = root / ".profile.sb"
        self.profile_path.write_text(_profile(root, tools_root, policy), encoding="utf-8")

    # -- staging ---------------------------------------------------------------------------------

    def stage_file(self, source: str | Path, destination: str | Path, *, link: bool = False
                   ) -> Path:
        """Place one file in the view.

        Copied by default. A hard link shares an inode, and everything inside the view is writable
        by the subject, so linking a control-plane file would hand the subject a handle to the
        evaluator's own copy. Linking is available for genuinely immutable material staged outside
        the writable root, which is what `Tool` does.
        """
        target = self.root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        if link:
            os.link(Path(source), target)
        else:
            shutil.copyfile(Path(source), target)
        return target

    def stage_tree(self, source: str | Path, destination: str | Path) -> Path:
        """Place a directory in the view, copied so nothing is shared with its origin."""
        target = self.root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(Path(source), target, dirs_exist_ok=True)
        return target

    # -- execution -------------------------------------------------------------------------------

    def environment(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """The subject's environment, assembled rather than inherited.

        Built from an empty mapping upward. The three names below were derived by running a shell,
        an interpreter and the search tools under an empty environment and adding only what they
        failed without; everything else an experiment needs it declares.
        """
        env = {
            "PATH": os.pathsep.join([str(self.tools_root), *BASE_PATH]),
            "HOME": str(self.home),
            "TMPDIR": str(self.tmp),
        }
        env.update(self.policy.env)
        env.update(extra or {})
        return env

    def run(self, argv: Sequence[str], *, cwd: str | Path | None = None,
            env: dict[str, str] | None = None, timeout: int | None = 120,
            check: bool = False) -> subprocess.CompletedProcess:
        """Run one command inside the boundary.

        The single way this module executes anything. A caller that reached for `subprocess` itself
        would be running outside the view it just constructed, which is the mistake most worth making
        impossible to make by accident.
        """
        if not Path(SANDBOX).exists():                      # pragma: no cover - platform guard
            raise ViewError(f"{SANDBOX} is not available on this platform")
        command = [SANDBOX, "-f", str(self.profile_path), *argv]
        return subprocess.run(  # noqa: S603 - argv is constructed, never a shell string
            command, cwd=str(cwd or self.workspace), env=self.environment(env),
            capture_output=True, text=True, timeout=timeout, check=check)

    def shell(self, script: str, **kw) -> subprocess.CompletedProcess:
        """Run a shell snippet inside the boundary, for probes that want ordinary tooling."""
        return self.run(["/bin/sh", "-c", script], **kw)

    # -- validation and egress -------------------------------------------------------------------

    def roots(self) -> tuple[Path, ...]:
        """Everything the subject can write, which is everything that could hold new evidence.

        `home` is in the list. An earlier version of the hermeticity scan did not cover it, and a
        home is exactly where an executor keeps state between sessions.
        """
        return tuple(getattr(self, area) for area in self.AREAS)

    def collect(self, relative: str | Path, destination: str | Path) -> Path:
        """Copy one product of the slot out to the control plane.

        Egress happens after execution and from the outside. The subject is never told where the
        destination is and never holds a handle to it.
        """
        source = self.root / relative
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copyfile(source, target)
        return target

    def describe(self) -> dict[str, Any]:
        """What this instance is, beside what kind of boundary it realises."""
        return {
            "policy_identity": self.policy.identity(),
            "root": str(self.root),
            "tools_root": str(self.tools_root),
            "areas": {area: str(getattr(self, area)) for area in self.AREAS},
            "declared": list(self.policy.declared),
            "network": self.policy.network,
            "tools": [t.describe() for t in self.policy.tools],
        }


@contextlib.contextmanager
def semantic_view(policy: Policy | None = None, *, parent: Path = DEFAULT_PARENT):
    """Construct one slot, hand it over, and destroy it however the block ends.

    Destruction is in a `finally` and covers success, a raised exception, a failed child command and
    a construction that got half way. Nothing is left for the next slot to find — and the next slot's
    own validation is what establishes that, because cleanup is never proof.
    """
    policy = policy or Policy()
    parent = Path(parent)
    parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=VIEW_PREFIX, dir=parent))
    tools_root = Path(tempfile.mkdtemp(prefix=TOOLS_PREFIX, dir=parent))
    try:
        for tool in policy.tools:
            staged = tools_root / tool.name
            try:
                os.link(tool.source, staged)
            except OSError as exc:
                raise ViewError(
                    f"tool {tool.name!r} at {tool.source} cannot be staged by hard link "
                    f"({exc.strerror}). A copy would lose its code signature and be killed on "
                    f"exec; move the tool onto the same volume as {parent}, or expose its "
                    f"directory through the policy instead.") from exc
        view = View(root, tools_root, policy)
        yield view
    finally:
        # Staged tools are hard links whose mode was never touched, so removing their directory
        # removes the links and leaves every original exactly as it was.
        for path in (root, tools_root):
            _destroy(path)


def _destroy(path: Path) -> None:
    """Remove one slot directory, and notice when that did not work.

    Retried once, because a child process that outlived the call that started it can be writing into
    the tree while it is being removed. What survives a second attempt is remembered, so the next
    slot's validation has something to find rather than a silent accumulation.
    """
    for _ in range(2):
        shutil.rmtree(path, ignore_errors=True)
        if not path.exists():
            _UNREMOVED.discard(path)
            return
    _UNREMOVED.add(path)


def parent_is_clear(sensitive: Iterable[Any], parent: Path = DEFAULT_PARENT) -> dict[str, Any]:
    """Whether the directory the views live under holds anything but views.

    The view's parent has to stay listable, because otherwise a subject cannot walk down to its own
    workspace and neither can the scan. Listable means sibling *names* are visible, and a name is
    information: an experiment artefact left beside a view is discoverable by name even though its
    contents are refused. That is a property of the arrangement, not a defect to hide, so it is
    measured — the parent is expected to contain view and tool directories and nothing else.
    """
    parent = Path(parent)
    strays: list[str] = []
    if parent.is_dir():
        for entry in sorted(parent.iterdir()):
            if entry.name.startswith((VIEW_PREFIX, TOOLS_PREFIX)):
                continue
            with contextlib.suppress(OSError):
                for kind in sensitive:
                    if kind.interesting(entry) or (entry.is_file() and kind.confirms(entry)):
                        strays.append(str(entry))
                        break
    return {"parent": str(parent), "clear": not strays, "named_artefacts": strays,
            "claim": ("sibling names under the view's parent are visible to the subject; their "
                      "contents are not")}


def stale_views(parent: Path = DEFAULT_PARENT) -> tuple[Path, ...]:
    """Slot directories left behind by an earlier run, recognised by their prefix."""
    parent = Path(parent)
    if not parent.is_dir():
        return ()
    found = []
    for entry in sorted(parent.iterdir()):
        with contextlib.suppress(OSError):
            if entry.is_dir() and entry.name.startswith((VIEW_PREFIX, TOOLS_PREFIX)):
                found.append(entry)
    return tuple(found)

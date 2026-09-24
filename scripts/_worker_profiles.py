"""Selectable worker profiles, resolved once into immutable run settings.

A model name is not the system under test. What a worker attempt actually runs is an executor
build, a provider route, an endpoint, a model, a variant, output and context limits, a tool
surface, a credential entry, a billing basis and a network boundary. A **profile** names that
bundle; **resolving** it produces one settings record and a digest over it, and that record — not
the profile's source file — is what a run keeps. Editing the source later cannot change a started
run: resume reads the recorded settings and a repeated `start` refuses, naming each field.

Two kinds exist, deliberately few:

* `deepseek-v4-flash-high` — the default, built in. The historically qualified route: pinned
  OpenCode 1.18.29, OpenCode's native `deepseek` provider, `--variant high`, the dated DeepSeek
  price table, the `deepseek` credential entry only.
* `local-openai-compatible` — a file the owner writes. A loopback OpenAI-compatible endpoint driven
  through the same pinned executor's bundled `@ai-sdk/openai-compatible` adapter. No variant is
  passed, no credential is staged, no external API billing is assumed, and the worker's network is
  restricted to loopback. The endpoint being HTTP-compatible establishes none of tool calling,
  usage semantics or cancellation; those are qualification questions, not profile fields.

Profiles are independent of who coordinates. Nothing here reads, stores or prints a credential: a
profile file carrying a secret-looking key or a URL with userinfo or a query is refused, so profile
identity cannot contain one.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PROFILE_FORMAT = "proofbound-worker-profile-v1"
SETTINGS_FORMAT = "proofbound-worker-settings-v1"
DEFAULT_PROFILE = "deepseek-v4-flash-high"
LOCAL_KIND = "local-openai-compatible"
DEEPSEEK_KIND = "opencode-native-deepseek"

#: The executor build the recorded evidence was produced with, pinned by content.
OPENCODE_VERSION = "1.18.29"
OPENCODE_SHA256 = "2f24593f1b8e578d0b7ed7ca399440d4b6c125330eece20a69ad8d380190d669"

#: Billing bases. A price table prices measured usage; the other says no external API bill is
#: expected — which is not a claim that the work cost nothing.
PRICED = "dated-table"
NO_EXTERNAL_BILLING = "no-external-api-billing"

#: The dated table runs recorded before profiles are priced at (`_worker_pricing.DEEPSEEK_2026_09_09`).
DEEPSEEK_TABLE = "deepseek-2026-09-09"

#: Host-side containment of one attempt (`_supervised_launch`). The pinned executor's own agent
#: `steps` limit bounds tool-calling iterations but not a response that ends without a finish
#: reason, which it re-requests immediately — observed as 4,649 requests in 900 s — so the host
#: counts requests and trailing incomplete responses, and, for a priced worker, derived spend.
CONTAINMENT = {"max_model_requests": 150, "max_consecutive_incomplete_responses": 5}

#: What the DeepSeek route means, by the date its provider facts were read. A run keeps the revision
#: it started under; a run recorded before profiles keeps the first. Never reinterpreted.
DEEPSEEK_REVISIONS: dict[str, dict[str, Any]] = {
    "2026-09-09": {
        "table": "deepseek-2026-09-09", "price_model": "deepseek-v4-flash",
        "documented_serving": {"model_version": "DeepSeek-V4-Flash-0731", "read": "2026-09-09",
                               "source": "https://api-docs.deepseek.com/quick_start/pricing"},
        "containment": None},
    "2026-09-23": {
        "table": "deepseek-2026-09-23", "price_model": "deepseek-flash",
        "documented_serving": {
            "model_version": "DeepSeek-V4.1-Flash", "since": "2026-09-10", "read": "2026-09-23",
            "source": "https://api-docs.deepseek.com/updates/",
            "statement": "V4 Flash retired; the legacy name deepseek-v4-flash is temporarily "
                         "routed to V4.1 Flash and billed at the Flash price"},
        "containment": {**CONTAINMENT, "derived_spend_during_attempt": True}},
    # Same provider facts and prices. What moved is the executor's fetched catalogue, which lists
    # the requested name as deprecated; the pinned executor then refuses it. From this revision the
    # run starts the executor on the catalogue bundled in its pinned bytes (`_executor_startup`).
    "2026-09-24": {
        "table": "deepseek-2026-09-23", "price_model": "deepseek-flash",
        "documented_serving": {
            "model_version": "DeepSeek-V4.1-Flash", "since": "2026-09-10", "read": "2026-09-23",
            "source": "https://api-docs.deepseek.com/updates/",
            "statement": "V4 Flash retired; the legacy name deepseek-v4-flash is temporarily "
                         "routed to V4.1 Flash and billed at the Flash price"},
        "containment": {**CONTAINMENT, "derived_spend_during_attempt": True},
        "catalogue": {
            "used": "the catalogue bundled in the pinned executor, which lists deepseek-v4-flash",
            "not_used": "models.dev as fetched on 2026-09-24 lists deepseek-v4-flash with status "
                        "deprecated; the pinned executor deletes deprecated models, so a launch "
                        "that read it failed before any request"},
        "startup": True},
}
CURRENT_DEEPSEEK_REVISION = "2026-09-24"

#: How a new run starts the pinned executor (`_executor_startup.POLICY`). A run started before it
#: has no `executor.startup` and launches exactly as it did.
from _executor_startup import POLICY as STARTUP_POLICY  # noqa: E402

#: What a run can observe of the model that answered, stated once for every profile.
RUNTIME_IDENTITY = ("requested id only: the pinned executor records the model id it requested and "
                    "does not retain the provider's response model field; neither an alias nor "
                    "that string identifies model weights")

#: Executor switches for a local profile. Each closes a route by which ambient state could select a
#: different model or service: a project `opencode.json`, a fetched model catalogue, self-update,
#: an LSP download, session sharing.
LOCAL_OPENCODE_ENV = {
    "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
    "OPENCODE_DISABLE_MODELS_FETCH": "1",
    "OPENCODE_DISABLE_AUTOUPDATE": "1",
    "OPENCODE_DISABLE_LSP_DOWNLOAD": "1",
    "OPENCODE_DISABLE_SHARE": "1",
}

_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
_MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}")
_SECRETISH = re.compile(r"(api[_-]?key|apikey|token|secret|password|passwd|authori[sz]ation|"
                        r"bearer|credential|cookie|headers?)$", re.I)
_LOCAL_KEYS = {"format", "id", "kind", "endpoint", "model", "limits", "tool_call", "resources",
               "declared_server", "description"}
_SERVER_KEYS = {"software", "version", "weights", "quantization", "chat_template", "hardware"}

BUILTIN: dict[str, dict[str, Any]] = {
    DEFAULT_PROFILE: {
        "format": PROFILE_FORMAT, "id": DEFAULT_PROFILE, "kind": DEEPSEEK_KIND,
        "model": "deepseek/deepseek-v4-flash", "variant": "high",
        "revision": CURRENT_DEEPSEEK_REVISION,
        "description": "The DeepSeek worker route the recorded evidence used. The request is "
                       "unchanged; since 2026-09-10 the provider serves V4.1 Flash for it.",
    },
}

LOCAL_TEMPLATE: dict[str, Any] = {
    "format": PROFILE_FORMAT,
    "id": "local-example",
    "kind": LOCAL_KIND,
    "description": "A loopback OpenAI-compatible server. Replace every value; nothing is inferred.",
    "endpoint": "http://127.0.0.1:8080/v1",
    "model": "REPLACE-with-the-server-model-id",
    "limits": {"context": 32768, "output": 8192},
    "tool_call": True,
    "resources": {"output_token_allowance": None},
    "declared_server": {"software": None, "version": None, "weights": None,
                        "quantization": None, "chat_template": None, "hardware": None},
}


class ProfileError(ValueError):
    """A profile that cannot be resolved into settings. Lists every problem, not the first."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def settings_digest(settings: dict[str, Any]) -> str:
    """The identity of resolved settings: everything but the digest field itself."""
    body = {k: v for k, v in settings.items() if k != "digest"}
    return hashlib.sha256(canonical(body)).hexdigest()


# -- reading a profile ---------------------------------------------------------------------------

def load(selector: "str | Path") -> tuple[dict[str, Any], dict[str, Any]]:
    """The profile's source and where it came from. A built-in name wins over a same-named path."""
    name = str(selector)
    if name in BUILTIN:
        return json.loads(json.dumps(BUILTIN[name])), {"source": "builtin", "path": None,
                                                        "source_sha256": None}
    path = Path(selector).expanduser()
    if not path.is_file():
        raise ProfileError(f"no built-in worker profile named {name!r} and no profile file at "
                           f"{path}; built-in profiles: {', '.join(sorted(BUILTIN))}")
    raw_bytes = path.read_bytes()
    try:
        raw = json.loads(raw_bytes)
    except ValueError as exc:
        raise ProfileError(f"worker profile {path} is not JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ProfileError(f"worker profile {path} must be a JSON object")
    return raw, {"source": "file", "path": str(path.resolve()),
                 "source_sha256": hashlib.sha256(raw_bytes).hexdigest()}


def _secret_keys(value: Any, where: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, inner in value.items():
            path = f"{where}.{key}" if where else str(key)
            if _SECRETISH.search(str(key)):
                found.append(path)
            found += _secret_keys(inner, path)
    elif isinstance(value, list):
        for index, inner in enumerate(value):
            found += _secret_keys(inner, f"{where}[{index}]")
    return found


def endpoint_identity(url: Any) -> tuple[dict[str, Any] | None, list[str]]:
    """The non-secret parts of an endpoint URL, and why it is refused if it is.

    Userinfo, a query and a fragment are refused rather than stripped: stripping would record an
    endpoint the executor is not actually given, and a query is where keys tend to hide.
    """
    if not isinstance(url, str) or not url.strip():
        return None, ["endpoint must be a URL such as http://127.0.0.1:8080/v1"]
    problems: list[str] = []
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        return None, [f"endpoint is not a usable URL: {exc}"]
    if parts.scheme not in ("http", "https"):
        problems.append("endpoint scheme must be http or https")
    if parts.username or parts.password or "@" in parts.netloc:
        problems.append("endpoint must not embed credentials (userinfo); nothing secret belongs "
                        "in profile identity")
    if parts.query or parts.fragment:
        problems.append("endpoint must not carry a query or fragment")
    host = parts.hostname or ""
    loopback = host == "localhost"
    if not loopback:
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = False
    if not loopback:
        problems.append(f"endpoint host {host!r} is not a loopback address; this profile kind "
                        "supports a server on this machine only, because the worker's network "
                        "boundary is restricted to loopback")
    if port is None:
        problems.append("endpoint must name its port explicitly")
    if problems:
        return None, problems
    return {"url": f"{parts.scheme}://{parts.netloc}{parts.path}", "scheme": parts.scheme,
            "host": host, "port": port, "path": parts.path or "/", "loopback": True}, []


# -- resolution ----------------------------------------------------------------------------------

def _deepseek(raw: dict[str, Any], origin: dict[str, Any]) -> dict[str, Any]:
    revision = raw.get("revision", "2026-09-09")
    facts = DEEPSEEK_REVISIONS[revision]
    enforced = ["launch ceiling", "repair allowance", "attempt deadline",
                "aggregate derived-cost limit (between attempts)"]
    if facts["containment"]:
        enforced.append("per-attempt containment: model-request cap, trailing incomplete "
                        "responses, derived spend observed during the attempt")
    executor = {"kind": "opencode-cli", "version": OPENCODE_VERSION, "sha256": OPENCODE_SHA256}
    provider = {"id": "deepseek", "route": "OpenCode native provider integration",
                "endpoint": None, "requested_model": raw["model"],
                "documented_serving": facts["documented_serving"],
                "runtime_identity": RUNTIME_IDENTITY}
    # Absent, not null, for earlier revisions: their settings bytes and digests stay as recorded.
    if facts.get("startup"):
        executor["startup"] = dict(STARTUP_POLICY)
        provider["catalogue"] = facts["catalogue"]
    return {
        "format": SETTINGS_FORMAT,
        "profile": {"id": raw["id"], "kind": DEEPSEEK_KIND, "revision": revision, **origin},
        "executor": executor,
        "provider": provider,
        "model": raw["model"], "variant": raw["variant"],
        "parameters": {"variant_flag": f"--variant {raw['variant']}",
                       "sampling": "not controllable; the provider documents that thinking mode "
                                   "ignores temperature and top_p"},
        "limits": {"context": None, "output": None,
                   "basis": "provider and executor defaults; this profile sets neither"},
        "tools": {"permission_flag": "--auto", "tool_call_declared": None,
                  "tool_surface": "the executor's default tool set; not inferable from a "
                                  "version string"},
        "credential": {"auth_entry": "deepseek"},
        "billing": {"basis": PRICED, "table": facts["table"],
                    "price_model": facts["price_model"]},
        "resources": {"output_token_allowance": None, "enforced": enforced, "configured": [],
                      "attempt_containment": facts["containment"]},
        "network": {"mode": "unrestricted",
                    "claim": "a cloud provider reached over the network; the worker boundary "
                             "allows all network access"},
        "opencode_config": None,
        "opencode_env": {},
        "declared_server": None,
        "legacy": False,
    }


def _local(raw: dict[str, Any], origin: dict[str, Any]) -> dict[str, Any]:
    problems: list[str] = []
    unknown = sorted(set(raw) - _LOCAL_KEYS)
    if unknown:
        problems.append(f"unknown profile field(s) {unknown}; a misspelt field must not be "
                        "silently ignored")
    endpoint, why = endpoint_identity(raw.get("endpoint"))
    problems += why
    model = raw.get("model")
    if not isinstance(model, str) or not _MODEL.fullmatch(model) or model.startswith("REPLACE"):
        problems.append("model must be the server's model id (letters, digits and ._:/+-)")
    limits = raw.get("limits")
    if not isinstance(limits, dict) or set(limits) != {"context", "output"}:
        problems.append("limits must state exactly {context, output} in tokens; no default is "
                        "assumed for a model this repository has never seen")
    else:
        for key in ("context", "output"):
            value = limits.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                problems.append(f"limits.{key} must be a positive integer")
        if not problems and limits["output"] >= limits["context"]:
            problems.append("limits.output must be smaller than limits.context")
    if raw.get("tool_call") is not True:
        problems.append("tool_call must be true: every worker role edits files through tools. "
                        "It is a declaration, and qualification is what tests it")
    resources = raw.get("resources", {})
    if not isinstance(resources, dict) or set(resources) - {"output_token_allowance"}:
        problems.append("resources may state only output_token_allowance")
        resources = {}
    allowance = resources.get("output_token_allowance")
    if allowance is not None and (isinstance(allowance, bool) or not isinstance(allowance, int)
                                  or allowance < 1):
        problems.append("resources.output_token_allowance must be a positive integer or null")
    server = raw.get("declared_server", {})
    if not isinstance(server, dict) or set(server) - _SERVER_KEYS or not all(
            v is None or isinstance(v, str) for v in server.values()):
        problems.append(f"declared_server may state only {sorted(_SERVER_KEYS)}, each a string "
                        "or null")
        server = {}
    if problems:
        raise ProfileError("; ".join(problems))

    provider_model = model
    opencode_config = {
        "$schema": "https://opencode.ai/config.json",
        "provider": {"local": {
            "npm": "@ai-sdk/openai-compatible", "name": "Proofbound local profile",
            "options": {"baseURL": endpoint["url"]},
            "models": {provider_model: {"name": provider_model, "tool_call": True,
                                        "limit": {"context": limits["context"],
                                                  "output": limits["output"]}}}}},
        # Only this provider is loaded, and every model OpenCode might pick for an auxiliary call
        # is this one — the small-model default would otherwise name a hosted service.
        "enabled_providers": ["local"],
        "model": f"local/{provider_model}",
        "small_model": f"local/{provider_model}",
        "autoupdate": False,
        "share": "disabled",
    }
    enforced = ["launch ceiling", "repair allowance", "attempt deadline (host-owned teardown of "
                "the worker client)", "one supervised launch per run at a time",
                "per-attempt containment: model-request cap, trailing incomplete responses"]
    if allowance is not None:
        enforced.append("aggregate output-token allowance (between attempts, from telemetry)")
    return {
        "format": SETTINGS_FORMAT,
        "profile": {"id": raw.get("id"), "kind": LOCAL_KIND, **origin},
        "executor": {"kind": "opencode-cli", "version": OPENCODE_VERSION,
                     "sha256": OPENCODE_SHA256, "startup": dict(STARTUP_POLICY)},
        "provider": {"id": "local",
                     "route": "@ai-sdk/openai-compatible, bundled in the pinned executor",
                     "endpoint": endpoint, "requested_model": model,
                     "documented_serving": None, "runtime_identity": RUNTIME_IDENTITY},
        "model": f"local/{provider_model}", "variant": None,
        "parameters": {"variant_flag": "not passed: a local model has no provider variant",
                       "sampling": "server defaults; not set by this profile"},
        "limits": {"context": limits["context"], "output": limits["output"],
                   "basis": "declared by the profile; the executor sends output as max_tokens "
                            "and uses context for its own compaction, the server may enforce "
                            "different limits"},
        "tools": {"permission_flag": "--auto", "tool_call_declared": True,
                  "tool_surface": "the executor's default tool set; not inferable from a "
                                  "version string"},
        "credential": {"auth_entry": None},
        "billing": {"basis": NO_EXTERNAL_BILLING,
                    "claim": "no external API bill is expected; local compute, electricity and "
                             "hardware cost are unknown, not zero"},
        "resources": {"output_token_allowance": allowance, "enforced": enforced,
                      "attempt_containment": {**CONTAINMENT,
                                              "derived_spend_during_attempt": False},
                      "configured": ["per-call output limit (max_tokens, honoured by the server "
                                     "or not)", "context limit (executor-side)",
                                     "server concurrency (not controlled by Proofbound)"]},
        "network": {"mode": "loopback-only",
                    "claim": "the worker boundary allows outbound connections to loopback only; "
                             "this is not offline execution, and the coordinator and any tools "
                             "it runs are outside the boundary"},
        "opencode_config": opencode_config,
        "opencode_env": dict(LOCAL_OPENCODE_ENV),
        "declared_server": {k: server.get(k) for k in sorted(_SERVER_KEYS)},
        "legacy": False,
    }


def resolve(selector: "str | Path" = DEFAULT_PROFILE) -> dict[str, Any]:
    """A profile, validated and resolved into settings carrying their own digest."""
    raw, origin = load(selector)
    problems: list[str] = []
    if raw.get("format") != PROFILE_FORMAT:
        problems.append(f"format must be {PROFILE_FORMAT!r}")
    if not isinstance(raw.get("id"), str) or not _ID.fullmatch(raw["id"]):
        problems.append("id must be a short lowercase identifier")
    secrets = _secret_keys(raw)
    if secrets:
        problems.append(f"profile carries secret-looking field(s) {secrets}; credentials never "
                        "belong in a profile")
    kind = raw.get("kind")
    if kind not in (DEEPSEEK_KIND, LOCAL_KIND):
        problems.append(f"kind must be {LOCAL_KIND!r} (or the built-in DeepSeek profile)")
    if kind == DEEPSEEK_KIND and origin["source"] != "builtin":
        problems.append("the DeepSeek route is selected by its built-in name, "
                        f"{DEFAULT_PROFILE!r}, not by a file")
    settings = None
    if kind == LOCAL_KIND:
        try:
            settings = _local(raw, origin)
        except ProfileError as exc:
            problems.append(str(exc))
    if problems:
        raise ProfileError("; ".join(problems))
    if settings is None:
        settings = _deepseek(raw, origin)
    settings["digest"] = settings_digest(settings)
    return settings


def legacy(config: dict[str, Any]) -> dict[str, Any]:
    """Settings for a run recorded before profiles existed. Derived for reading, never written.

    Those runs recorded a model and a variant and launched through the DeepSeek route. The record
    is interpreted as recorded (`P6`): nothing is backfilled into it, and a legacy run whose model
    is not the DeepSeek one is priced at nothing, which leaves its spend unknown rather than wrong.
    """
    settings = _deepseek({**BUILTIN[DEFAULT_PROFILE], "revision": "2026-09-09"},
                         {"source": "legacy-run-config", "path": None, "source_sha256": None})
    settings["model"] = config.get("model", settings["model"])
    settings["variant"] = config.get("variant", settings["variant"])
    settings["parameters"]["variant_flag"] = (f"--variant {settings['variant']}"
                                              if settings["variant"] else "not passed")
    if settings["model"] != BUILTIN[DEFAULT_PROFILE]["model"]:
        settings["billing"] = {"basis": PRICED, "table": DEEPSEEK_TABLE,
                               "price_model": str(settings["model"]).split("/", 1)[-1]}
    settings["legacy"] = True
    settings["digest"] = settings_digest(settings)
    return settings


def of(config: dict[str, Any]) -> dict[str, Any]:
    """The settings a run launches with, refusing a record whose bytes no longer match its digest.

    Recovery never involves editing run JSON; a settings block that was edited is a different
    configuration wearing the old identity, and launching under it would be a silent substitution.
    """
    settings = config.get("worker_profile")
    if settings is None:
        return legacy(config)
    if settings.get("format") != SETTINGS_FORMAT:
        raise ProfileError(f"unsupported worker settings format: {settings.get('format')!r}")
    if settings_digest(settings) != settings.get("digest"):
        raise ProfileError("the run's recorded worker settings do not match their digest; the "
                           "configuration was altered after start and will not be launched")
    if config.get("model") != settings["model"] or config.get("variant") != settings["variant"]:
        raise ProfileError("the run's model/variant disagree with its recorded worker settings")
    return settings


def differences(recorded: dict[str, Any], requested: dict[str, Any],
                prefix: str = "") -> list[dict[str, Any]]:
    """Every leaf that differs between two settings records, named by its dotted path."""
    out: list[dict[str, Any]] = []
    keys = sorted(set(recorded) | set(requested))
    for key in keys:
        if not prefix and key == "digest":
            continue
        path = f"{prefix}.{key}" if prefix else key
        left, right = recorded.get(key), requested.get(key)
        if isinstance(left, dict) and isinstance(right, dict):
            out += differences(left, right, path)
        elif left != right:
            out.append({"field": path, "in_effect": left, "requested": right})
    return out


# -- executor configuration and readiness ---------------------------------------------------------

def write_opencode_config(settings: dict[str, Any], runtime: "str | Path") -> dict[str, Any]:
    """Write the executor configuration a local profile needs into the run's runtime directory.

    Returns the worker environment that points the executor at it. The file is outside the project
    and outside the run tree; its digest is returned so the launcher can refuse bytes that moved.
    """
    config = settings.get("opencode_config")
    if not config:
        return {"worker_env": {}, "opencode_config": None}
    path = Path(runtime) / "opencode.json"
    data = json.dumps(config, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    path.write_bytes(data)
    return {"worker_env": {**settings["opencode_env"], "OPENCODE_CONFIG": str(path)},
            "opencode_config": {"path": str(path),
                                "sha256": hashlib.sha256(data).hexdigest()}}


def probe_endpoint(settings: dict[str, Any], *, timeout: float = 2.0) -> dict[str, Any]:
    """Is anything listening where the profile says, and does it list the model? Never generates.

    A TCP connection and a `GET …/models`. Neither requests a completion, and neither establishes
    tool calling, usage semantics or cancellation: a server can list a model it cannot drive.
    """
    endpoint = (settings.get("provider") or {}).get("endpoint")
    if not endpoint:
        return {"applicable": False}
    out: dict[str, Any] = {"applicable": True, "url": endpoint["url"], "completion_requested": False}
    try:
        with socket.create_connection((endpoint["host"], endpoint["port"]), timeout=timeout):
            out["reachable"] = True
    except OSError as exc:
        out.update(reachable=False, error=f"{type(exc).__name__}: {exc}")
        return out
    import urllib.request
    try:
        with urllib.request.urlopen(endpoint["url"].rstrip("/") + "/models",
                                    timeout=timeout) as response:
            body = json.loads(response.read(1_000_000) or b"{}")
        ids = sorted(str(m.get("id")) for m in body.get("data", []) if isinstance(m, dict))
        wanted = settings["model"].split("/", 1)[1]
        out.update(models_listed=ids[:50], model_listed=wanted in ids)
    except (OSError, ValueError) as exc:
        out.update(models_listed=None, model_listed=None,
                   models_error=f"{type(exc).__name__}: {str(exc)[:200]}")
    return out

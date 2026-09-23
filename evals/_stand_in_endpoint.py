"""A scripted, credential-free OpenAI-compatible endpoint. A stand-in, never a model.

It exists so the *mechanics* of a local worker profile can be exercised through the real pinned
executor and the production launch path without any model installed: the executor sends a real
chat-completions request with its real tool definitions, this endpoint answers with scripted tool
calls, the executor really runs its tools inside the real boundary, and the tool results come back
in the next request. What that establishes is the protocol round trip and Proofbound's handling of
it. It establishes nothing about any model — every "decision" below was written in advance.

The script is keyed by role and read from the worker prompt (`DSD <ROLE> for <task>.` and
`Report: <path>`), so one stand-in serves every role of a supervised run:

* step 1 — read every file it will write (the executor refuses to overwrite an unread file);
* step 2 — write the role's files and its report;
* step 3 — a final message.

Adversarial behaviours, because a tool loop that only ever sees well-formed traffic has not been
tested: `malformed-arguments` sends a tool call whose arguments are not JSON; `interrupted` drops
the connection mid-stream on every request; `missing-usage` omits the usage chunk. Every request
is logged with what matters for grading — roles present, tool names offered, tool results
returned — and nothing else about the prompt beyond the two marker lines.
"""
from __future__ import annotations

import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

WELL_FORMED = "well-formed"
MALFORMED_ARGUMENTS = "malformed-arguments"
INTERRUPTED = "interrupted"
MISSING_USAGE = "missing-usage"
BEHAVIOURS = (WELL_FORMED, MALFORMED_ARGUMENTS, INTERRUPTED, MISSING_USAGE)

#: The executor passes the prompt as a quoted positional message, so the first line may open with
#: a quote character.
_ROLE = re.compile(r'^"?DSD ([A-Z ]+) for (\S+?)\.?$', re.M)
_REPORT = re.compile(r"^Report: (.+)$", re.M)


def _text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return ""


class StandInEndpoint:
    """One scripted endpoint on a loopback port, run in a background thread.

    `roles` maps `task:role` or a bare role (`spec-author`, `implementer`, …) to `{"files":
    {abs_path: text}, "report": text}`; the task-qualified key wins. A role the script does not
    name writes only a report saying so.
    """

    def __init__(self, *, model: str = "stand-in-model", behaviour: str = WELL_FORMED,
                 roles: "dict[str, dict[str, Any]] | None" = None, host: str = "127.0.0.1",
                 port: int = 0) -> None:
        if behaviour not in BEHAVIOURS:
            raise ValueError(f"unknown stand-in behaviour {behaviour!r}")
        self.model, self.behaviour, self.roles = model, behaviour, roles or {}
        self.requests: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        endpoint = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: Any) -> None:            # the log is `requests`
                pass

            def do_GET(self) -> None:                             # noqa: N802 - http.server API
                endpoint._record({"method": "GET", "path": self.path})
                body = json.dumps({"object": "list", "data": [
                    {"id": endpoint.model, "object": "model"}]}).encode()
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:                            # noqa: N802
                size = int(self.headers.get("content-length") or 0)
                try:
                    request = json.loads(self.rfile.read(size) or b"{}")
                except ValueError:
                    request = {}
                chunks, cut = endpoint._respond(request, self.path, dict(self.headers))
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.send_header("cache-control", "no-cache")
                self.send_header("connection", "close")
                self.end_headers()
                for index, chunk in enumerate(chunks):
                    if cut is not None and index == cut:
                        # Abrupt end: no finish reason, no usage, no [DONE].
                        self.close_connection = True
                        self.wfile.flush()
                        self.connection.shutdown(2)
                        return
                    chunk.update({"id": "chatcmpl-stand-in", "object": "chat.completion.chunk",
                                  "created": int(time.time()), "model": endpoint.model})
                    self.wfile.write(b"data: " + json.dumps(chunk).encode() + b"\n\n")
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
                self.close_connection = True

        self._server = ThreadingHTTPServer((host, port), Handler)
        self.host, self.port = self._server.server_address[:2]
        self.url = f"http://{self.host}:{self.port}/v1"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    # -- lifecycle ---------------------------------------------------------------------------
    def __enter__(self) -> "StandInEndpoint":
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._server.shutdown()
        self._server.server_close()

    def _record(self, entry: dict[str, Any]) -> None:
        with self._lock:
            entry["n"] = len(self.requests) + 1
            self.requests.append(entry)

    # -- the script --------------------------------------------------------------------------
    def _respond(self, request: dict[str, Any], path: str,
                 headers: dict[str, str]) -> tuple[list[dict[str, Any]], int | None]:
        messages = request.get("messages") or []
        prompt = "\n".join(_text(m) for m in messages if m.get("role") == "user")
        role_match, report_match = _ROLE.search(prompt), _REPORT.search(prompt)
        role = role_match.group(1).lower().replace(" ", "-") if role_match else None
        task = role_match.group(2) if role_match else None
        report = report_match.group(1).strip() if report_match else None
        step = sum(1 for m in messages if m.get("role") == "assistant")
        self._record({
            "method": "POST", "path": path, "role": role, "step": step,
            "stream": request.get("stream"), "max_tokens": request.get("max_tokens"),
            "tools_offered": sorted(t.get("function", {}).get("name", "?")
                                    for t in request.get("tools") or []),
            "message_roles": [m.get("role") for m in messages],
            "tool_results": sum(1 for m in messages if m.get("role") == "tool"),
            "authorization_header": any(k.lower() == "authorization" for k in headers),
            "behaviour": self.behaviour})
        script = self.roles.get(f"{task}:{role}") or self.roles.get(role or "") or {}
        files = dict(script.get("files") or {})
        if report:
            files[report] = script.get("report") or (
                f"# Stand-in report ({role})\n\nScripted by the qualification replay; no model "
                "produced this and no semantic review was performed.\n")
        usage = {"prompt_tokens": 1000 + 100 * step, "completion_tokens": 50 + step,
                 "total_tokens": 1050 + 101 * step}

        if self.behaviour == INTERRUPTED:
            return [{"choices": [{"index": 0, "delta": {"role": "assistant",
                                                         "content": "partial"}}]},
                    {"choices": []}], 1
        if step == 0 and self.behaviour == MALFORMED_ARGUMENTS and files:
            target = next(iter(files))
            calls = [{"index": 0, "id": "call_bad", "type": "function",
                      "function": {"name": "write",
                                   "arguments": '{"filePath": "' + target + '", "content": '}}]
            return self._tool_chunks(calls, usage), None
        if step == 0 and files:
            calls = [{"index": i, "id": f"call_read_{i}", "type": "function",
                      "function": {"name": "read", "arguments": json.dumps({"filePath": p})}}
                     for i, p in enumerate(files)]
            return self._tool_chunks(calls, usage), None
        if step == 1 and files and self.behaviour != MALFORMED_ARGUMENTS:
            calls = [{"index": i, "id": f"call_write_{i}", "type": "function",
                      "function": {"name": "write",
                                   "arguments": json.dumps({"filePath": p, "content": text})}}
                     for i, (p, text) in enumerate(files.items())]
            return self._tool_chunks(calls, usage), None
        final = [{"choices": [{"index": 0, "delta": {"role": "assistant",
                                                      "content": f"{report or 'done'}"}}]},
                 {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}]
        if self.behaviour != MISSING_USAGE:
            final.append({"choices": [], "usage": usage})
        return final, None

    def _tool_chunks(self, calls: list[dict[str, Any]],
                     usage: dict[str, Any]) -> list[dict[str, Any]]:
        chunks = [{"choices": [{"index": 0, "delta": {"role": "assistant", "tool_calls": calls}}]},
                  {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}]
        if self.behaviour != MISSING_USAGE:
            chunks.append({"choices": [], "usage": usage})
        return chunks

    def summary(self) -> dict[str, Any]:
        """What the executor did against this endpoint, for grading. No prompt text."""
        posts = [r for r in self.requests if r["method"] == "POST"]
        return {"requests": len(posts), "listings": len(self.requests) - len(posts),
                "roles": sorted({r["role"] for r in posts if r.get("role")}),
                "continuations_with_tool_results": sum(1 for r in posts if r["tool_results"]),
                "authorization_header_seen": any(r["authorization_header"] for r in posts),
                "tools_offered": sorted({t for r in posts for t in r["tools_offered"]}),
                "max_tokens": sorted({r["max_tokens"] for r in posts
                                      if r.get("max_tokens") is not None}),
                "behaviour": self.behaviour}

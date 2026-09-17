#!/usr/bin/env python3
"""The deterministic oracle for the requirements pair: dispatch order over a finite domain.

The case is a work queue that serves items belonging to several keys. Two obligations that are each
reasonable — *serve items in the order they arrived* and *do not serve one key twice while another
is waiting* — cannot both hold, and the smallest state where that is demonstrable has three items.
Whether they are both demanded is the difference between the two cases.

Why this domain, rather than the rate-limiter the authority demonstrations used: **here exhaustion
is a proof.** An arrival sequence admits finitely many dispatch orders, so enumerating them settles
satisfiability outright. The float case taught the opposite lesson — a bounded search that runs out
has established nothing — and keeping a case whose oracle is genuinely complete separates "the
requirements conflict" from "we looked for a while". The numerical material is retained as research
in `demo/pb-authority-demo-2/`; it is not a prerequisite for exercising the authority workflow.

**What the oracle does not do.** It decides the encoded model. Whether the encoded model faithfully
expresses the prose beside it is a human judgement, recorded in each case's `case.json` and open to
challenge — it is exactly the kind of claim an intent challenge exists to examine.
"""
from __future__ import annotations

import itertools
import json
import re
from typing import Any, Callable, Iterable

Item = "tuple[str, int]"

MODEL_FORMAT = "proofbound-dispatch-order-v1"
_BLOCK = re.compile(r"```json\n(.*?)\n```", re.S)


class ModelError(ValueError):
    """The declared model is absent, malformed, or uses vocabulary the oracle does not know."""


def items_of(arrivals: "list[str]") -> "list[Item]":
    """Arrivals as identified items: the n-th item of key `k` is `(k, n)`."""
    seen: "dict[str, int]" = {}
    out = []
    for key in arrivals:
        seen[key] = seen.get(key, 0) + 1
        out.append((key, seen[key]))
    return out


# -- the closed obligation vocabulary ------------------------------------------------------------
#
# Each obligation is a predicate over one dispatch order, given the arrivals it came from. An
# unknown name is refused rather than ignored: silently skipping an obligation would make an
# unsatisfiable requirement set look satisfiable, which is the one error this oracle must not make.

def _exactly_once(order: "list[Item]", arrivals: "list[str]") -> bool:
    return sorted(order) == sorted(items_of(arrivals))


def _fifo_per_key(order: "list[Item]", arrivals: "list[str]") -> bool:
    for key in set(arrivals):
        seqs = [n for (k, n) in order if k == key]
        if seqs != sorted(seqs):
            return False
    return True


def _fifo_global(order: "list[Item]", arrivals: "list[str]") -> bool:
    return list(order) == items_of(arrivals)


def _round_robin(order: "list[Item]", arrivals: "list[str]") -> bool:
    """No key is served twice in succession while another key still has an item waiting."""
    outstanding = set(items_of(arrivals))
    for position, item in enumerate(order):
        outstanding.discard(item)
        if position + 1 < len(order):
            following = order[position + 1]
            if following[0] == item[0] and any(k != item[0] for (k, _n) in outstanding):
                return False
    return True


def _head_first(order: "list[Item]", arrivals: "list[str]") -> bool:
    return bool(order) and order[0] == items_of(arrivals)[0]


OBLIGATIONS: "dict[str, Callable[[list, list], bool]]" = {
    "exactly-once": _exactly_once,
    "fifo-per-key": _fifo_per_key,
    "fifo-global": _fifo_global,
    "round-robin": _round_robin,
    "head-first": _head_first,
}


# -- the declared model --------------------------------------------------------------------------

def parse_model(text: str) -> "dict[str, Any]":
    """Read the machine-checkable model out of a requirements document's own bytes.

    The oracle is a function of the artifact, not of the case it belongs to: editing the document
    changes the answer, which is what makes the discrimination check below mean anything.
    """
    found = _BLOCK.search(text)
    if not found:
        raise ModelError("the requirements document declares no ```json model block")
    try:
        model = json.loads(found.group(1))
    except ValueError as exc:
        raise ModelError(f"the declared model is not JSON: {exc}") from exc
    if model.get("format") != MODEL_FORMAT:
        raise ModelError(f"unexpected model format: {model.get('format')!r}")
    for name in (model.get("obligations") or {}).values():
        if name not in OBLIGATIONS:
            raise ModelError(f"unknown obligation: {name!r}; "
                             f"known are {', '.join(sorted(OBLIGATIONS))}")
    if not model.get("obligations"):
        raise ModelError("the declared model has no obligations")
    if not model.get("keys") or not isinstance(model.get("max_items"), int):
        raise ModelError("the declared model must name keys and a maximum item count")
    return model


def domain(model: "dict[str, Any]") -> "list[list[str]]":
    """Every arrival sequence the declared domain admits. Finite, and enumerated in full."""
    keys = list(model["keys"])
    out: "list[list[str]]" = []
    for length in range(1, int(model["max_items"]) + 1):
        out.extend([list(seq) for seq in itertools.product(keys, repeat=length)])
    return out


def violations(order: "list[Item]", arrivals: "list[str]",
               obligations: "dict[str, str]") -> "list[str]":
    """Which declared obligations this dispatch order breaks."""
    return [rid for rid, name in sorted(obligations.items())
            if not OBLIGATIONS[name](list(order), list(arrivals))]


def satisfying_order(arrivals: "list[str]", obligations: "dict[str, str]") -> "list[Item] | None":
    """Some dispatch order meeting every obligation, or `None` if the enumeration finds none.

    `None` here **is** nonexistence: the permutations of a finite arrival sequence are all of the
    dispatch orders there are.
    """
    for order in itertools.permutations(items_of(arrivals)):
        if not violations(list(order), arrivals, obligations):
            return list(order)
    return None


def minimal_unsat_cores(arrivals: "list[str]",
                        obligations: "dict[str, str]") -> "list[list[str]]":
    """The smallest sets of declared obligations that already cannot hold together here.

    A minimal core is the demonstrable part of a contradiction: it names which requirements
    conflict, rather than reporting that the document as a whole is unsatisfiable.
    """
    ids = sorted(obligations)
    cores: "list[list[str]]" = []
    for size in range(1, len(ids) + 1):
        for subset in itertools.combinations(ids, size):
            if any(set(core) <= set(subset) for core in cores):
                continue
            narrowed = {rid: obligations[rid] for rid in subset}
            if satisfying_order(arrivals, narrowed) is None:
                cores.append(list(subset))
        if cores:
            break
    return cores


def first_conflict(model: "dict[str, Any]") -> "dict[str, Any] | None":
    """The shortest arrival sequence in the declared domain that no dispatch order can serve."""
    for arrivals in sorted(domain(model), key=len):
        if satisfying_order(arrivals, model["obligations"]) is None:
            return {"arrivals": arrivals,
                    "minimal_unsatisfiable_cores": minimal_unsat_cores(
                        arrivals, model["obligations"]),
                    "orders_enumerated": _count(arrivals)}
    return None


def _count(arrivals: "Iterable[str]") -> int:
    n = len(list(arrivals))
    out = 1
    for i in range(2, n + 1):
        out *= i
    return out


def satisfiable_everywhere(model: "dict[str, Any]") -> "dict[str, Any]":
    """Whether every arrival sequence in the declared domain can be served at all."""
    unserviceable = [arrivals for arrivals in domain(model)
                     if satisfying_order(arrivals, model["obligations"]) is None]
    return {"sequences": len(domain(model)),
            "unserviceable": [list(a) for a in unserviceable[:4]],
            "unserviceable_count": len(unserviceable),
            "satisfiable": not unserviceable}


def check_implementation(dispatch: "Callable[[list[str]], list[Item]]",
                         model: "dict[str, Any]") -> "dict[str, Any]":
    """Run one implementation over the whole declared domain and report what it breaks."""
    broken: "dict[str, list[str]]" = {}
    failures = 0
    for arrivals in domain(model):
        try:
            order = list(dispatch(list(arrivals)))
        except Exception as exc:                                  # noqa: BLE001 - reported, not raised
            broken.setdefault(f"raised:{type(exc).__name__}", []).append("".join(arrivals))
            failures += 1
            continue
        found = violations(order, arrivals, model["obligations"])
        if found:
            failures += 1
            for rid in found:
                broken.setdefault(rid, []).append("".join(arrivals))
    return {"sequences": len(domain(model)), "failing_sequences": failures,
            "conforms": failures == 0,
            "violated": {rid: {"count": len(seqs), "first": seqs[0]}
                         for rid, seqs in sorted(broken.items())}}

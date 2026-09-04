#!/usr/bin/env python3
"""Shared directed-acyclic-graph traversal for Proofbound dependency structures.

Two structures need identical DAG semantics: the accepted ledger's dependency closure and
the declared change graph's required topology. Freeze aggregation will be a third caller.

They must never disagree about what a cycle is, or about the order dependencies resolve
in. Two traversals that can disagree are a defect factory, so there is exactly one here
and it is deliberately tiny — a shared primitive, not a graph framework.

Both functions take the same plain shape, `node -> iterable of dependency names`, so a
caller adapts its own record format at the call site rather than this module learning
about ledgers or graphs.
"""
from __future__ import annotations

from typing import Iterable, Mapping

__all__ = ["CycleError", "assert_acyclic", "topological_order"]


class CycleError(ValueError):
    """The dependency structure contains a cycle, so its closure is undefined."""


def assert_acyclic(edges: Mapping[str, Iterable[str]]) -> None:
    """Raise `CycleError` if `edges` contains a cycle.

    Iterative colour-marking DFS: a deep or hostile graph cannot exhaust the interpreter
    stack. Failing before any state is derived is the safe outcome — a plausible-looking
    result computed over an undefined closure is worse than no result.
    """
    WHITE, GREY, BLACK = 0, 1, 2
    color = dict.fromkeys(edges, WHITE)
    for start in edges:
        if color[start] != WHITE:
            continue
        stack: list[tuple[str, list[str]]] = [(start, list(edges[start]))]
        color[start] = GREY
        path = [start]
        while stack:
            node, pending = stack[-1]
            if not pending:
                color[node] = BLACK
                stack.pop()
                path.pop()
                continue
            nxt = pending.pop()
            if color.get(nxt) == GREY:
                raise CycleError(" -> ".join(path + [nxt]))
            if color.get(nxt) == BLACK:
                continue
            if nxt not in edges:
                # A dangling target is not a cycle. Callers decide whether it is an error;
                # traversal simply cannot descend into it.
                continue
            color[nxt] = GREY
            path.append(nxt)
            stack.append((nxt, list(edges[nxt])))


def topological_order(edges: Mapping[str, Iterable[str]]) -> list[str]:
    """Dependencies before dependents, deterministically.

    Only meaningful on a structure already proved acyclic. Resolving in this order lets a
    caller memoize per node, which keeps an otherwise recursive closure at effective depth
    one — the reason a 5000-node chain does not hit the recursion limit.
    """
    order: list[str] = []
    seen: set[str] = set()
    for start in sorted(edges):
        if start in seen:
            continue
        stack = [(start, iter(sorted(edges[start])))]
        seen.add(start)
        while stack:
            node, children = stack[-1]
            nxt = next(children, None)
            if nxt is None:
                order.append(node)
                stack.pop()
                continue
            if nxt not in seen and nxt in edges:
                seen.add(nxt)
                stack.append((nxt, iter(sorted(edges[nxt]))))
    return order

#!/usr/bin/env python3
"""The corpus the checker is validated against. **Never staged into a subject runtime.**

`_checker` states the acceptance criteria, and those are legitimately visible to anyone: they are
the contract's. What lives here is different — working implementations of the very thing an
implementer is asked to write. A worker that could read this file would be handed the answer, so
the runtime builder stages the checker and the obligation model and leaves this behind, and the
exposure probe measures that rather than asserting it.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _checker import FAIL, PASS, check_delivered   # noqa: E402,F401


# -- the corpus ---------------------------------------------------------------
#
# A checker is an instrument, and an instrument that has never been shown to discriminate is an
# assertion. The corpus below is self-contained source: each artifact is what an implementer could
# plausibly deliver, and none of it imports anything from this repository, so what runs is what the
# checker would receive.

_PRELUDE = '''
def _items(arrivals):
    seen, out = {}, []
    for key in arrivals:
        seen[key] = seen.get(key, 0) + 1
        out.append((key, seen[key]))
    return out


def _queues(arrivals):
    order, queues = [], {}
    for item in _items(arrivals):
        if item[0] not in queues:
            queues[item[0]] = []
            order.append(item[0])
        queues[item[0]].append(item)
    return order, queues


def _round_robin(arrivals):
    keys, queues = _queues(arrivals)
    out = []
    while any(queues[k] for k in keys):
        for key in keys:
            if queues[key]:
                out.append(queues[key].pop(0))
    return out


def _fewest_remaining(arrivals):
    keys, queues = _queues(arrivals)
    out, last = [], None
    while any(queues[k] for k in keys):
        waiting = [k for k in keys if queues[k]]
        if last is None:
            choice = keys[0]
        else:
            eligible = [k for k in waiting if k != last] or waiting
            choice = min(eligible, key=lambda k: (len(queues[k]), keys.index(k)))
        out.append(queues[choice].pop(0))
        last = choice
    return out
'''

#: name -> (body, expected verdict, expected finding codes)
CORPUS: "dict[str, tuple[str, str, tuple[str, ...]]]" = {
    # Sound, and structurally different from each other. Both must pass, or the checker is
    # grading resemblance to one algorithm rather than the requirements.
    "round-robin": ("def dispatch(arrivals):\n    return _round_robin(arrivals)", PASS, ()),
    "fewest-remaining": ("def dispatch(arrivals):\n    return _fewest_remaining(arrivals)",
                         PASS, ()),
    "pairs-as-lists": ("def dispatch(arrivals):\n"
                       "    return [[k, n] for k, n in _round_robin(arrivals)]", PASS, ()),
    # The gap this checker exists to close: ordering is right, the container is not.
    "generator": ("def dispatch(arrivals):\n"
                  "    return (item for item in _round_robin(arrivals))", FAIL, ("return-type",)),
    "tuple-container": ("def dispatch(arrivals):\n    return tuple(_round_robin(arrivals))",
                        FAIL, ("return-type",)),
    # Ordering defects, one obligation each where possible.
    "global-fifo": ("def dispatch(arrivals):\n    return _items(arrivals)", FAIL, ("obligation",)),
    "lifo-per-key": ("def dispatch(arrivals):\n"
                     "    keys, queues = _queues(arrivals)\n"
                     "    out = []\n"
                     "    while any(queues[k] for k in keys):\n"
                     "        for key in keys:\n"
                     "            if queues[key]:\n"
                     "                out.append(queues[key].pop())\n"
                     "    return out", FAIL, ("obligation",)),
    "drops-last": ("def dispatch(arrivals):\n    return _round_robin(arrivals)[:-1]",
                   FAIL, ("obligation",)),
    "duplicates-head": ("def dispatch(arrivals):\n"
                        "    out = _round_robin(arrivals)\n"
                        "    return [out[0], *out]", FAIL, ("obligation",)),
    "key-sorted": ("def dispatch(arrivals):\n"
                   "    _keys, queues = _queues(arrivals)\n"
                   "    out = []\n"
                   "    for key in sorted(queues):\n"
                   "        out.extend(queues[key])\n"
                   "    return out", FAIL, ("obligation",)),
    # Item-level API defects.
    "string-items": ("def dispatch(arrivals):\n"
                     "    return ['%s%d' % (k, n) for k, n in _round_robin(arrivals)]",
                     FAIL, ("item-shape",)),
    # Things that are not implementations at all.
    "raises": ("def dispatch(arrivals):\n    raise RuntimeError('not implemented')",
               FAIL, ("raised",)),
    "no-callable": ("def helper(arrivals):\n    return arrivals", FAIL, ("no-dispatch-callable",)),
    "does-not-terminate": ("def dispatch(arrivals):\n"
                           "    import time\n"
                           "    time.sleep(3600)\n"
                           "    return _round_robin(arrivals)", FAIL, ("does-not-terminate",)),
    "import-raises": ("raise SystemError('broken at import')\n\n"
                      "def dispatch(arrivals):\n    return []", FAIL,
                     ("artifact-not-importable",)),
}


def validate(*, timeout: int = 20) -> "dict[str, Any]":
    """Run the whole corpus and report whether the checker discriminated as declared."""
    rows: "dict[str, Any]" = {}
    with tempfile.TemporaryDirectory(prefix="pb-checker-validate-") as td:
        for name, (body, expected_verdict, expected_codes) in CORPUS.items():
            artifact = Path(td) / f"{name}.py"
            artifact.write_text(_PRELUDE + "\n\n" + body + "\n", encoding="utf-8")
            report = check_delivered(artifact, timeout=timeout)
            codes = sorted({f["code"] for f in report["findings"]})
            rows[name] = {
                "expected_verdict": expected_verdict, "verdict": report["verdict"],
                "expected_codes": sorted(expected_codes), "codes": codes,
                "as_declared": report["verdict"] == expected_verdict
                and set(expected_codes) <= set(codes),
            }
    sound = [n for n, (_b, v, _c) in CORPUS.items() if v == PASS]
    defective = [n for n in CORPUS if n not in sound]
    return {
        "checked": rows,
        "sound_accepted": all(rows[n]["verdict"] == PASS for n in sound),
        "defective_rejected": all(rows[n]["verdict"] != PASS for n in defective),
        "all_as_declared": all(r["as_declared"] for r in rows.values()),
        "sound": sound, "defective": defective,
        "note": "two structurally different sound implementations must both pass; an instrument "
                "that accepted only its own reference would be measuring resemblance",
    }

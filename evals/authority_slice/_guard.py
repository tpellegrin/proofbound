"""Historical experiment policy over the production launch guard."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from _launch_budget import *
from _launch_budget import LaunchLedger as _Ledger, spend as _spend
import _launch_paths
AGGREGATE_LIMIT = 0.30
RESERVE = 0.06
LAUNCH_CEILING = _launch_paths.ceiling()["ceiling"]
class LaunchLedger(_Ledger):
    def __init__(self, path):
        super().__init__(path, limit=AGGREGATE_LIMIT, reserve=RESERVE, ceiling=LAUNCH_CEILING)
def spend(run_root, db, **kwargs):
    result = _spend(run_root, db, limit=AGGREGATE_LIMIT, reserve=RESERVE, **kwargs)
    if kwargs.get("event_dirs") is not None:
        result["scope"] += "; seeded attempts are excluded"
    return result

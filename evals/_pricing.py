"""Compatibility import; production owns execution accounting."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import _worker_pricing as _implementation
sys.modules[__name__] = _implementation

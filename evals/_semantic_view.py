"""Compatibility import: production owns the constructed execution view."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import _execution_view as _implementation
sys.modules[__name__] = _implementation

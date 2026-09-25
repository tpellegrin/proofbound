#!/usr/bin/env python3
"""Compatibility wrapper: Kilo workers moved to scripts/install_kilo_workers.py."""
from __future__ import annotations
import runpy
import sys
from pathlib import Path
scripts = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(scripts))  # the installer imports its sibling modules
runpy.run_path(str(scripts / "install_kilo_workers.py"), run_name="__main__")

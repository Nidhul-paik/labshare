#!/usr/bin/env python3
"""Run LabShare straight from a source checkout (no installation needed).

    python run_labshare.py host --hotspot
    python run_labshare.py client
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from labshare.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

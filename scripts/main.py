"""Canonical command-line entrypoint for the architecture-drawing skill.

This is intentionally a thin wrapper. The implementation remains in ``src`` so
legacy script entrypoints and package imports continue to work.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline.run import main as _pipeline_main


def main() -> int:
    return _pipeline_main()


if __name__ == "__main__":
    raise SystemExit(main())

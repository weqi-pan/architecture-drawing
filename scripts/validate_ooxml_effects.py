"""Validate native OOXML effects in a generated PPTX package."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.renderers.ppt_ooxml import inspect_pptx_ooxml


def validate(path: str | Path) -> dict:
    report = inspect_pptx_ooxml(path)
    report["valid"] = bool(report["pptx_package_valid"] and report["slide_xml_valid"] and not report["errors"] and not report["duplicate_fill_errors"])
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PPTX OOXML advanced effects")
    parser.add_argument("pptx")
    args = parser.parse_args()
    result = validate(args.pptx)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Small path and JSON helpers shared by public skill entrypoints."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def project_root() -> Path:
    """Return the skill root independent of the current working directory."""
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str) -> Path:
    """Resolve a file under the skill's ``resources`` directory."""
    return project_root().joinpath("resources", *parts)


def load_json(path: str | Path) -> Any:
    """Load UTF-8 JSON with a stable, explicit path conversion."""
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path: str | Path, value: Any) -> Path:
    """Write UTF-8 JSON and create the parent directory if necessary."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target

"""Plan a renderable style from an explicit user request or an Agent style contract.

Themes live in ``resources/themes/*.json`` and are pure data: colors, header, node,
connector and effect switches. This module performs no image OCR and no semantic
inference.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

STYLE_CAPABILITIES = {
    "solid_fill": "SUPPORTED",
    "gradient_fill": "SUPPORTED_OOXML",
    "gradient_line": "SUPPORTED_OOXML",
    "outer_shadow": "SUPPORTED_OOXML",
    "glow": "SUPPORTED_OOXML",
    "transparency": "SUPPORTED_OOXML",
    "soft_edge": "NOT_SUPPORTED",
    "glass_blur": "NOT_SUPPORTED",
}

THEMES_DIR = Path(__file__).resolve().parents[2] / "resources" / "themes"
DEFAULT_THEME = "enterprise_tech"

_ALIASES = {
    "政务蓝": "government_blue", "government blue": "government_blue", "government_blue": "government_blue",
    "科研风": "scientific_blue", "科研蓝": "scientific_blue", "scientific blue": "scientific_blue", "scientific_blue": "scientific_blue",
    "企业科技": "enterprise_tech", "enterprise tech": "enterprise_tech", "enterprise_tech": "enterprise_tech",
    "默认": "enterprise_tech", "default": "enterprise_tech",
    "论文简约": "academic_minimal", "学术简约": "academic_minimal", "academic minimal": "academic_minimal", "academic_minimal": "academic_minimal",
    "工业工程": "industrial_engineering", "industrial engineering": "industrial_engineering", "industrial_engineering": "industrial_engineering",
    "科技渐变风": "tech_gradient", "科技渐变": "tech_gradient", "蓝紫科技": "tech_gradient", "蓝紫渐变": "tech_gradient",
    "未来科技渐变": "tech_gradient", "tech gradient": "tech_gradient", "gradient tech": "tech_gradient", "tech_gradient": "tech_gradient",
}

REFERENCE_KEYS = {"colors", "font", "node_corner_radius", "line_width", "background", "title_style", "module_style", "header", "node", "connector", "effect_level"}


def available_themes() -> list[str]:
    """Return the theme ids shipped in ``resources/themes``."""
    return sorted(path.stem for path in THEMES_DIR.glob("*.json"))


def load_theme(style_id: str) -> dict[str, Any]:
    """Load a theme by id, falling back to the default theme."""
    path = THEMES_DIR / f"{style_id}.json"
    if not path.exists():
        path = THEMES_DIR / f"{DEFAULT_THEME}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _select_style_id(request: str | None) -> str:
    text = (request or "").strip().lower().replace("-", " ")
    # Prefer longer aliases so "科技渐变风" wins over shorter fragments.
    for alias in sorted(_ALIASES, key=len, reverse=True):
        if alias.lower().replace("-", " ") in text:
            return _ALIASES[alias]
    return DEFAULT_THEME


def _theme_style(style_id: str) -> dict[str, Any]:
    theme = load_theme(style_id)
    colors = dict(theme.get("colors", {}))
    connector = dict(theme.get("connector", {}))
    return {
        "mode": "NO_REFERENCE",
        "template": theme.get("name", style_id),
        "style_id": theme.get("id", style_id),
        "colors": colors,
        "background": theme.get("background", colors.get("background", "#FFFFFF")),
        "font": theme.get("font", "Aptos"),
        "node_corner_radius": float(theme.get("node_corner_radius", 0.08)),
        "line_width": float(connector.get("width", 1.25)),
        "effect_level": theme.get("effect_level", "minimal"),
        "header": deepcopy(theme.get("header", {})),
        "node": deepcopy(theme.get("node", {})),
        "connector": connector,
        "band": deepcopy(theme.get("band", {})),
        "renderer_capabilities": deepcopy(STYLE_CAPABILITIES),
        "source": "default_or_user_request",
    }


def plan_style(request: str | None = None, *, reference: dict[str, Any] | None = None) -> dict[str, Any]:
    """Plan a renderable style from a user request or an Agent reference analysis."""
    if reference:
        colors = dict(reference.get("colors", {}))
        result = {
            "mode": "REFERENCE_STYLE", "style_id": "reference", "colors": colors,
            "font": reference.get("font", "Aptos"),
            "background": reference.get("background", colors.get("background", "#FFFFFF")),
            "node_corner_radius": float(reference.get("node_corner_radius", 0.08)),
            "line_width": float(reference.get("line_width", 1.25)),
            "title_style": dict(reference.get("title_style", {})),
            "module_style": dict(reference.get("module_style", {})),
            "header": deepcopy(reference.get("header", {})),
            "node": deepcopy(reference.get("node", {})),
            "connector": deepcopy(reference.get("connector", {})),
            "band": deepcopy(reference.get("band", {})),
            "effect_level": reference.get("effect_level", "moderate"),
            "renderer_capabilities": deepcopy(STYLE_CAPABILITIES),
            "source": "agent_reference_analysis",
        }
        # Unsupported effects are intentionally ignored rather than emitted.
        result.pop("soft_edge", None); result.pop("glass_blur", None)
        return result

    return _theme_style(_select_style_id(request))

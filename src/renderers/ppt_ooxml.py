"""Centralized Office Open XML visual effects for native PowerPoint shapes.

The helpers in this module intentionally sit below the python-pptx renderer. They
patch only the shape's ``p:spPr`` XML and keep every object editable in PowerPoint.
No Office/COM process is required.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from pptx.oxml.xmlchemy import OxmlElement

_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"

# Whole-value decimal attributes: OOXML EMU/width attributes must be integers, so any
# decimal value here means a renderer wrote a float where an integer was required.
_FLOAT_ATTRIBUTE = re.compile(r'"(-?\d+\.\d+)"')


def _a(tag: str):
    return OxmlElement(f"a:{tag}")


def _sp_pr(shape):
    return shape.element.spPr


def _first_child(parent, local_names: Iterable[str]):
    names = set(local_names)
    for child in parent:
        if child.tag.rsplit("}", 1)[-1] in names:
            return child
    return None


def _remove_children(parent, local_names: Iterable[str]) -> None:
    names = set(local_names)
    for child in list(parent):
        if child.tag.rsplit("}", 1)[-1] in names:
            parent.remove(child)


def _local_name(node) -> str:
    return node.tag.rsplit("}", 1)[-1]


def _hex(value: str) -> str:
    value = str(value or "FFFFFF").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise ValueError(f"RGB color must be six hexadecimal characters: {value!r}")
    return value.upper()


def _pos(value: float | int) -> int:
    return max(0, min(100000, round(float(value) * 100000)))


def _alpha(value: float | int | None) -> int:
    if value is None:
        return 100000
    value = float(value)
    # Accept either opacity [0,1] or OOXML alpha [0,100000].
    if value > 1:
        return max(0, min(100000, round(value)))
    return max(0, min(100000, round(value * 100000)))


def _angle(value: float | int) -> int:
    return round((float(value) % 360.0) * 60000)


def _emu(value: float | int) -> int:
    # Style distances and blur radii are expressed in points by the public API.
    return max(0, round(float(value) * 12700))


def _stop_data(stop: Mapping[str, Any]) -> tuple[int, str, int]:
    position = stop.get("position", stop.get("pos", 0))
    color = _hex(str(stop.get("color", "FFFFFF")))
    opacity = stop.get("opacity", stop.get("alpha", 1.0))
    return _pos(position), color, _alpha(opacity)


def _gradient_fill(stops: Iterable[Mapping[str, Any]], angle: float | int = 0, rotate_with_shape: bool = True):
    grad = _a("gradFill")
    grad.set("rotWithShape", "1" if rotate_with_shape else "0")
    gs_lst = _a("gsLst")
    normalized = sorted((_stop_data(stop) for stop in stops), key=lambda item: item[0])
    if len(normalized) < 2:
        raise ValueError("gradient requires at least two stops")
    for position, color, alpha in normalized:
        gs = _a("gs"); gs.set("pos", str(position))
        srgb = _a("srgbClr"); srgb.set("val", color)
        if alpha != 100000:
            alpha_node = _a("alpha"); alpha_node.set("val", str(alpha)); srgb.append(alpha_node)
        gs.append(srgb); gs_lst.append(gs)
    grad.append(gs_lst)
    lin = _a("lin"); lin.set("ang", str(_angle(angle))); lin.set("scaled", "1"); grad.append(lin)
    return grad


def remove_existing_fill(shape) -> None:
    """Remove all existing fill children from a shape's ``p:spPr``."""
    _remove_children(_sp_pr(shape), {"noFill", "solidFill", "gradFill", "blipFill", "pattFill"})


def remove_existing_effects(shape) -> None:
    """Remove the complete effect list from a shape."""
    _remove_children(_sp_pr(shape), {"effectLst", "effectDag"})


def apply_gradient_fill(shape, stops: Iterable[Mapping[str, Any]], angle: float | int = 0, rotate_with_shape: bool = True):
    """Apply native ``a:gradFill`` to a shape. Positions are [0,1] and angles are degrees."""
    gradient = _gradient_fill(stops, angle, rotate_with_shape)
    remove_existing_fill(shape)
    sp_pr = _sp_pr(shape)
    insert_at = 0
    for idx, child in enumerate(list(sp_pr)):
        if child.tag.rsplit("}", 1)[-1] in {"ln", "effectLst", "effectDag", "scene3d", "sp3d", "extLst"}:
            insert_at = idx; break
        insert_at = idx + 1
    sp_pr.insert(insert_at, gradient)
    return shape


def _set_color_alpha(color_container, opacity: float | int) -> None:
    """Set alpha on every color child in a fill/effect color container."""
    for node in color_container.iter():
        if _local_name(node) in {"srgbClr", "schemeClr", "prstClr", "sysClr"}:
            _remove_children(node, {"alpha"})
            node.append(_alpha_node(opacity))


def apply_alpha(shape, opacity: float | int, *, target: str = "fill"):
    """Apply alpha to an existing fill or line, including all gradient stops.

    ``opacity`` accepts the public ``0..1`` form or native OOXML ``0..100000``
    alpha units. The helper deliberately does not invent a fill/line color: the
    caller's existing python-pptx base style remains the fallback.
    """
    if target not in {"fill", "line"}:
        raise ValueError("target must be 'fill' or 'line'")
    parent = _sp_pr(shape)
    if target == "line":
        line = _first_child(parent, {"ln"})
        if line is None:
            return shape
        color = _first_child(line, {"solidFill", "gradFill"})
    else:
        color = _first_child(parent, {"solidFill", "gradFill"})
    if color is not None:
        _set_color_alpha(color, opacity)
    return shape


def _alpha_node(opacity):
    node = _a("alpha"); node.set("val", str(_alpha(opacity))); return node


def apply_gradient_line(shape, stops: Iterable[Mapping[str, Any]], angle: float | int = 0, rotate_with_shape: bool = True):
    """Apply native gradient line when the shape exposes a line element."""
    sp_pr = _sp_pr(shape)
    line = _first_child(sp_pr, {"ln"})
    if line is None:
        line = _a("ln"); sp_pr.append(line)
    gradient = _gradient_fill(stops, angle, rotate_with_shape)
    _remove_children(line, {"noFill", "solidFill", "gradFill", "pattFill", "blipFill"})
    line.insert(0, gradient)
    return shape


def _effect_list(shape):
    sp_pr = _sp_pr(shape)
    effects = _first_child(sp_pr, {"effectLst"})
    if effects is None:
        effects = _a("effectLst")
        # CT_ShapeProperties places effects after the line and before optional
        # 3-D/extension nodes. Keep that order even for manually supplied XML.
        insert_at = len(sp_pr)
        for idx, child in enumerate(list(sp_pr)):
            if _local_name(child) in {"scene3d", "sp3d", "extLst"}:
                insert_at = idx
                break
        sp_pr.insert(insert_at, effects)
    return effects


def _remove_empty_effect_list(shape, effects) -> None:
    if len(effects) == 0:
        parent = _sp_pr(shape)
        if effects in parent:
            parent.remove(effects)


def _color_node(parent, color: str, opacity: float | int):
    srgb = _a("srgbClr"); srgb.set("val", _hex(color)); srgb.append(_alpha_node(opacity)); parent.append(srgb)


def _normalize_effect_order(effects) -> None:
    order = {"blur": 0, "fillOverlay": 1, "glow": 2, "innerShdw": 3, "outerShdw": 4, "prstShdw": 5, "reflection": 6, "softEdge": 7}
    children = list(effects)
    for child in children:
        effects.remove(child)
    for child in sorted(children, key=lambda node: order.get(node.tag.rsplit("}", 1)[-1], 99)):
        effects.append(child)


def apply_outer_shadow(shape, *, enabled: bool = True, color: str = "2D4F80", opacity: float = 0.16, blur: float = 6, distance: float = 2, direction: float = 270):
    """Apply a soft native ``a:outerShdw``; blur and distance use points."""
    effects = _effect_list(shape)
    _remove_children(effects, {"outerShdw"})
    if enabled:
        shadow = _a("outerShdw")
        shadow.set("blurRad", str(_emu(blur))); shadow.set("dist", str(_emu(distance))); shadow.set("dir", str(_angle(direction)))
        shadow.set("rotWithShape", "1"); _color_node(shadow, color, opacity); effects.append(shadow)
        _normalize_effect_order(effects)
    else:
        _remove_empty_effect_list(shape, effects)
    return shape


def apply_glow(shape, *, enabled: bool = True, color: str = "18B6D9", opacity: float = 0.22, radius: float = 4):
    """Apply optional native ``a:glow`` in points."""
    effects = _effect_list(shape)
    _remove_children(effects, {"glow"})
    if enabled:
        glow = _a("glow"); glow.set("rad", str(_emu(radius))); _color_node(glow, color, opacity); effects.append(glow)
        _normalize_effect_order(effects)
    else:
        _remove_empty_effect_list(shape, effects)
    return shape


def apply_effect_list(shape, effects: Mapping[str, Any] | None = None):
    effects = dict(effects or {})
    shadow = dict(effects.get("shadow", {}))
    glow = dict(effects.get("glow", {}))
    if shadow:
        apply_outer_shadow(shape, **shadow)
    if glow:
        apply_glow(shape, **glow)
    return shape


def apply_style_effects(shape, style: Mapping[str, Any], *, role: str = "node"):
    """Apply StyleSpec effects with editable solid/no-effect fallbacks.

    The base python-pptx style is applied by the caller first. If an advanced
    effect cannot be represented safely, this function leaves that base style
    intact rather than allowing a malformed effect to break the PPTX package.
    """
    fill = style.get("fill")
    try:
        if isinstance(fill, Mapping) and fill.get("type") == "gradient":
            apply_gradient_fill(shape, fill.get("stops", []), fill.get("angle", 0), fill.get("rotate_with_shape", True))
        elif isinstance(style.get("gradient"), Mapping):
            gradient = style["gradient"]
            apply_gradient_fill(shape, gradient.get("stops", []), gradient.get("angle", 0), gradient.get("rotate_with_shape", True))
    except (TypeError, ValueError, KeyError):
        # Keep the solid fill already assigned by python-pptx.
        pass
    try:
        opacity = style.get("opacity")
        if opacity is None and isinstance(fill, Mapping):
            opacity = fill.get("opacity")
        if opacity is not None:
            apply_alpha(shape, opacity)
    except (TypeError, ValueError, KeyError):
        pass
    shadow = style.get("shadow")
    if shadow:
        try:
            apply_outer_shadow(shape, **dict(shadow))
        except (TypeError, ValueError, KeyError):
            pass
    glow = style.get("glow")
    if glow:
        try:
            apply_glow(shape, **dict(glow))
        except (TypeError, ValueError, KeyError):
            pass
    line = style.get("line")
    if isinstance(line, Mapping) and line.get("type") == "gradient":
        try:
            apply_gradient_line(shape, line.get("stops", []), line.get("angle", 0), line.get("rotate_with_shape", True))
        except (TypeError, ValueError, KeyError):
            pass
    return shape


def apply_arrow_head(shape, *, kind: str = "tail", arrow_type: str = "triangle", size: str = "med") -> None:
    """Append a native DrawingML arrow head to a connector's line.

    ``a:ln`` requires child order fill -> prstDash -> join -> headEnd -> tailEnd, so the
    arrow is appended last, which keeps existing fill and dash children valid.
    """
    line = _first_child(_sp_pr(shape), ("ln",))
    if line is None:
        return
    tag = "tailEnd" if kind == "tail" else "headEnd"
    for existing in list(line):
        if _local_name(existing) == tag:
            line.remove(existing)
    element = _a(tag)
    element.set("type", arrow_type)
    element.set("w", size)
    element.set("len", size)
    line.append(element)


def inspect_pptx_ooxml(path) -> dict[str, Any]:
    """Inspect package/XML validity and report advanced DrawingML element counts."""
    from pathlib import Path
    from zipfile import BadZipFile, ZipFile
    from lxml import etree
    report: dict[str, Any] = {
        "pptx_package_valid": False, "slide_xml_valid": False,
        "gradient_fill_count": 0, "gradient_stop_count": 0,
        "gradient_line_count": 0, "gradient_line_stop_count": 0,
        "outer_shadow_count": 0, "glow_count": 0, "alpha_count": 0,
        "editable_shape_count": 0, "editable_connector_count": 0,
        "duplicate_fill_errors": [], "invalid_numeric_attributes": [], "errors": [],
    }
    try:
        with ZipFile(Path(path)) as package:
            bad = package.testzip()
            if bad:
                report["errors"].append(f"corrupt package member: {bad}")
                return report
            report["pptx_package_valid"] = True
            slide_names = [name for name in package.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")]
            for name in slide_names:
                raw = package.read(name)
                # OOXML numeric attributes (EMU offsets, extents, widths) must be integers;
                # python-pptx writes whatever it is given, so floats survive into the file.
                floats = sorted({value for value in _FLOAT_ATTRIBUTE.findall(raw.decode("utf-8"))})
                if floats:
                    report["invalid_numeric_attributes"].append({"part": name, "values": floats})
                    report["errors"].append(f"{name} contains non-integer numeric attributes: {floats}")
                root = etree.fromstring(raw)
                report["gradient_fill_count"] += int(root.xpath("count(.//a:gradFill)", namespaces={"a": _NS_A}))
                report["gradient_stop_count"] += int(root.xpath("count(.//a:gradFill//a:gs)", namespaces={"a": _NS_A}))
                report["gradient_line_count"] += int(root.xpath("count(.//a:ln/a:gradFill)", namespaces={"a": _NS_A}))
                report["gradient_line_stop_count"] += int(root.xpath("count(.//a:ln/a:gradFill//a:gs)", namespaces={"a": _NS_A}))
                report["outer_shadow_count"] += int(root.xpath("count(.//a:outerShdw)", namespaces={"a": _NS_A}))
                report["glow_count"] += int(root.xpath("count(.//a:glow)", namespaces={"a": _NS_A}))
                report["alpha_count"] += int(root.xpath("count(.//a:alpha)", namespaces={"a": _NS_A}))
                report["editable_shape_count"] += int(root.xpath("count(.//p:sp)", namespaces={"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}))
                report["editable_connector_count"] += int(root.xpath("count(.//p:cxnSp)", namespaces={"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}))
                for sp_pr in root.xpath(".//p:spPr", namespaces={"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}):
                    fills = [child.tag.rsplit("}", 1)[-1] for child in sp_pr if child.tag.rsplit("}", 1)[-1] in {"noFill", "solidFill", "gradFill", "blipFill", "pattFill"}]
                    if len(fills) > 1:
                        report["duplicate_fill_errors"].append({"part": name, "fills": fills})
            report["slide_xml_valid"] = True
    except (BadZipFile, OSError, etree.XMLSyntaxError) as exc:
        report["errors"].append(str(exc))
    return report

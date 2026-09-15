from __future__ import annotations
from typing import Any

# The renderer emits a single 16:9 slide; coordinates are 96-dpi pixels.
SLIDE_WIDTH = 1280.0
SLIDE_HEIGHT = 720.0


def _inside(inner: dict[str, Any], outer: dict[str, Any], tolerance: float = 0.75) -> bool:
    return (
        float(inner.get("x", 0)) >= float(outer.get("x", 0)) - tolerance
        and float(inner.get("y", 0)) >= float(outer.get("y", 0)) - tolerance
        and float(inner.get("x", 0)) + float(inner.get("width", 0)) <= float(outer.get("x", 0)) + float(outer.get("width", 0)) + tolerance
        and float(inner.get("y", 0)) + float(inner.get("height", 0)) <= float(outer.get("y", 0)) + float(outer.get("height", 0)) + tolerance
    )


def validate_layout(layout: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    seen: list[str] = []
    canvas = layout.get("canvas", {})
    width = float(canvas.get("width", 0))
    height = float(canvas.get("height", 0))
    if width > SLIDE_WIDTH or height > SLIDE_HEIGHT:
        warnings.append(f"canvas {width:g}x{height:g} exceeds the single-slide bounds {SLIDE_WIDTH:g}x{SLIDE_HEIGHT:g}; split the view or reduce nodes")

    bands = layout.get("bands", [])
    for band in bands:
        if not _inside(band, {"x": 0, "y": 0, "width": width, "height": height}):
            errors.append(f"band outside canvas: {band.get('name')}")
        label = band.get("label")
        if label and not _inside(label, band):
            errors.append(f"band label outside band: {band.get('name')}")

    for element in layout.get("elements", []):
        if element.get("id") in seen:
            errors.append(f"duplicate element id: {element.get('id')}")
        seen.append(element.get("id"))
        x, y, w, h = (float(element.get(k, 0)) for k in ("x", "y", "width", "height"))
        if x < 0 or y < 0 or x + w > width or y + h > height:
            errors.append(f"element outside canvas: {element.get('id')}")
        owning = element.get("band")
        if owning and bands:
            band = next((b for b in bands if b.get("name") == owning), None)
            if band is None:
                errors.append(f"element references unknown band: {element.get('id')} -> {owning}")
            elif not _inside(element, band):
                errors.append(f"element outside its band: {element.get('id')}")

    for index, a in enumerate(layout.get("elements", [])):
        for b in layout.get("elements", [])[index + 1:]:
            if (a.get("x", 0) < b.get("x", 0) + b.get("width", 0) and b.get("x", 0) < a.get("x", 0) + a.get("width", 0)
                    and a.get("y", 0) < b.get("y", 0) + b.get("height", 0) and b.get("y", 0) < a.get("y", 0) + a.get("height", 0)):
                errors.append(f"overlap: {a.get('id')} / {b.get('id')}")

    return {"valid": not errors, "errors": errors, "warnings": warnings}

"""Deterministic layered-band layout model, independent from any renderer.

The layout turns an ArchitectureModel into horizontal layer bands:

    [层名] | [节点] [节点] [节点] [节点]
    [层名] | [节点] [节点]

Bands are ordered by ``level`` (L1 first), nodes inside a band by connectivity
direction (nodes that feed the next band are pushed to the bottom row) and then by
``priority``/``id``. No randomness and no renderer concepts beyond pixel geometry.
"""
from __future__ import annotations

import math
import re
from typing import Any

from src.architecture.model import ArchitectureModel

CANVAS_WIDTH = 1280.0
CANVAS_HEIGHT = 720.0
HEADER_HEIGHT = 38.0
TOP_GAP = 26.0
BOTTOM_MARGIN = 20.0
OUTER_MARGIN = 24.0
LABEL_STRIP_WIDTH = 100.0
LABEL_STRIP_GAP = 12.0
BAND_PAD_X = 12.0
MAX_COLUMNS = 4
LABEL_BOX_WIDTH = 132.0
LABEL_BOX_HEIGHT = 24.0

# node height, row gap, column gap, band gap, band vertical padding
_SIZE_PLANS: tuple[tuple[float, float, float, float, float], ...] = (
    (74.0, 16.0, 20.0, 16.0, 10.0),
    (66.0, 14.0, 18.0, 14.0, 9.0),
    (58.0, 12.0, 16.0, 12.0, 8.0),
    (52.0, 10.0, 14.0, 10.0, 6.0),
)

_PRIORITY_RANK = {"primary": 0, "secondary": 1, "supporting": 2, "tertiary": 3}


def _level_rank(level: Any) -> int:
    match = re.match(r"[Ll](\d+)", str(level or ""))
    return int(match.group(1)) if match else 99


def _priority_rank(priority: Any) -> int:
    return _PRIORITY_RANK.get(str(priority or "").lower(), 1)


def _band_name(node) -> str:
    return str(node.layer or node.domain or "全局")


def _group_bands(model: ArchitectureModel) -> tuple[list[dict[str, Any]], dict[str, set[str]]]:
    """Order bands by level/name, then order nodes by flow direction and priority."""
    groups: dict[str, dict[str, Any]] = {}
    for node in model.nodes:
        name = _band_name(node)
        entry = groups.setdefault(name, {"name": name, "rank": _level_rank(node.level), "nodes": []})
        entry["rank"] = min(entry["rank"], _level_rank(node.level))
        entry["nodes"].append(node)

    bands = sorted(groups.values(), key=lambda band: (band["rank"], band["name"]))
    band_index = {band["name"]: index for index, band in enumerate(bands)}
    band_of = {node.id: band_index[_band_name(node)] for node in model.nodes}

    # ``up``/``down`` describe how a connector leaves the node: upward connectors should
    # leave from the top row of a band, downward connectors from the bottom row, so a
    # route never has to cross the band's own rows.
    up: set[str] = set()
    down: set[str] = set()
    for rel in model.relations:
        source, target = band_of.get(rel.source), band_of.get(rel.target)
        if source is None or target is None or source == target:
            continue
        if source > target:
            up.add(rel.source); down.add(rel.target)
        else:
            down.add(rel.source); up.add(rel.target)

    for band in bands:
        band["nodes"].sort(key=lambda n: (1 if n.id in down and n.id not in up else 0, _priority_rank(n.priority), n.id))
    return bands, {"up": up, "down": down}


def _band_height(rows: int, node_h: float, row_gap: float, pad_y: float) -> float:
    return rows * node_h + max(0, rows - 1) * row_gap + 2 * pad_y


def _pick_size_plan(bands: list[dict[str, Any]], height: float) -> tuple[float, float, float, float, float]:
    available = height - (HEADER_HEIGHT + TOP_GAP) - BOTTOM_MARGIN
    for plan in _SIZE_PLANS:
        node_h, row_gap, _col_gap, band_gap, pad_y = plan
        total = 0.0
        for band in bands:
            columns = max(1, min(len(band["nodes"]), MAX_COLUMNS))
            rows = max(1, math.ceil(len(band["nodes"]) / columns))
            total += _band_height(rows, node_h, row_gap, pad_y)
        total += band_gap * max(0, len(bands) - 1)
        if total <= available:
            return plan
    return _SIZE_PLANS[-1]


def _geometry(bands: list[dict[str, Any]], width: float, height: float) -> dict[str, Any]:
    node_h, row_gap, col_gap, band_gap, pad_y = _pick_size_plan(bands, height)
    band_x = OUTER_MARGIN
    band_w = width - 2 * OUTER_MARGIN
    node_x0 = band_x + BAND_PAD_X + LABEL_STRIP_WIDTH + LABEL_STRIP_GAP
    node_x1 = band_x + band_w - BAND_PAD_X
    area_w = node_x1 - node_x0

    elements: list[dict[str, Any]] = []
    band_boxes: list[dict[str, Any]] = []
    y = HEADER_HEIGHT + TOP_GAP
    for index, band in enumerate(bands):
        nodes = band["nodes"]
        columns = max(1, min(len(nodes), MAX_COLUMNS))
        rows = max(1, math.ceil(len(nodes) / columns))
        node_w = (area_w - (columns - 1) * col_gap) / columns
        band_h = _band_height(rows, node_h, row_gap, pad_y)
        band_boxes.append({
            "index": index, "name": band["name"], "rank": band["rank"],
            "x": band_x, "y": y, "width": band_w, "height": band_h,
            "label": {"x": band_x + BAND_PAD_X, "y": y + pad_y, "width": LABEL_STRIP_WIDTH, "height": band_h - 2 * pad_y},
            "accent": {"x": band_x, "y": y, "width": 4.0, "height": band_h},
        })
        for position, node in enumerate(nodes):
            row, column = divmod(position, columns)
            elements.append({
                "id": node.id,
                "x": node_x0 + column * (node_w + col_gap),
                "y": y + pad_y + row * (node_h + row_gap),
                "width": node_w, "height": node_h,
                "layer": band["name"], "band": band["name"], "band_index": index,
                "row": row, "rows": rows, "column": column, "columns": columns,
            })
        y += band_h + band_gap

    return {
        "bands": band_boxes, "elements": elements,
        "node_x0": node_x0, "node_x1": node_x1, "node_w": node_w, "node_h": node_h,
        "row_gap": row_gap, "col_gap": col_gap, "band_gap": band_gap,
        "bottom": y - band_gap,
    }


def _column_channels(node_x0: float, node_x1: float, node_w: float, col_gap: float, columns: int) -> list[float]:
    channels = [node_x0 + (c + 1) * node_w + c * col_gap + col_gap / 2 for c in range(max(0, columns - 1))]
    channels.append(node_x1 + col_gap / 2)
    return channels


def _nearest_channel(x: float, channels: list[float]) -> float:
    return min(channels, key=lambda channel: abs(channel - x))


def _run_anchor(points: list[list[float]]) -> tuple[float, float]:
    """Anchor a label on the longest run of the route, centred on that run's corridor."""
    longest = max(zip(points, points[1:]), key=lambda pair: abs(pair[1][0] - pair[0][0]) + abs(pair[1][1] - pair[0][1]))
    (x1, y1), (x2, y2) = longest
    middle_y = (y1 + y2) / 2 - LABEL_BOX_HEIGHT / 2
    if abs(x2 - x1) >= abs(y2 - y1):
        return ((x1 + x2) / 2 - LABEL_BOX_WIDTH / 2, middle_y)
    return ((x1 + x2) / 2 + 6, middle_y)


def _intersects(box: tuple[float, float, float, float], other: tuple[float, float, float, float]) -> bool:
    return box[0] < other[2] and other[0] < box[2] and box[1] < other[3] and other[1] < box[3]


def _place_labels(relations: list[dict[str, Any]], elements: list[dict[str, Any]], width: float, height: float) -> None:
    """Give every label a slot that covers no node and no other label.

    Labels are centred on their route run first; when two routes share a run the label
    is nudged sideways, then vertically, until it finds free space.
    """
    node_rects = [(e["x"], e["y"], e["x"] + e["width"], e["y"] + e["height"]) for e in elements]
    placed: list[tuple[float, float, float, float]] = []
    offsets: list[tuple[float, float]] = [(0.0, 0.0)]
    for step in range(1, 5):
        offsets += [(step * (LABEL_BOX_WIDTH + 6), 0.0), (-step * (LABEL_BOX_WIDTH + 6), 0.0)]
    for step in range(1, 4):
        offsets += [(0.0, step * (LABEL_BOX_HEIGHT + 4)), (0.0, -step * (LABEL_BOX_HEIGHT + 4))]

    for relation in relations:
        if not relation.get("label"):
            continue
        anchor_x, anchor_y = relation.pop("_anchor")
        chosen = None
        for dx, dy in offsets:
            x, y = anchor_x + dx, anchor_y + dy
            box = (x, y, x + LABEL_BOX_WIDTH, y + LABEL_BOX_HEIGHT)
            if x < OUTER_MARGIN or y < HEADER_HEIGHT + 2 or box[2] > width - OUTER_MARGIN or box[3] > height - 2:
                continue
            if any(_intersects(box, rect) for rect in node_rects):
                continue
            if any(_intersects(box, rect) for rect in placed):
                continue
            chosen = box
            break
        if chosen is None:
            continue
        placed.append(chosen)
        relation["label_box"] = {"x": chosen[0], "y": chosen[1], "width": LABEL_BOX_WIDTH, "height": LABEL_BOX_HEIGHT}


def _route(src: dict[str, Any], tgt: dict[str, Any], bands_by_index: dict[int, dict[str, Any]], geom: dict[str, Any]) -> list[list[float]]:
    sx = src["x"] + src["width"] / 2
    sy_top, sy_bottom = src["y"], src["y"] + src["height"]
    tx = tgt["x"] + tgt["width"] / 2
    ty_top, ty_bottom = tgt["y"], tgt["y"] + tgt["height"]
    row_gap, col_gap, band_gap = geom["row_gap"], geom["col_gap"], geom["band_gap"]
    src_band = bands_by_index.get(src.get("band_index"), src)
    tgt_band = bands_by_index.get(tgt.get("band_index"), tgt)

    if src["band_index"] == tgt["band_index"]:
        if src["row"] == tgt["row"]:
            center_y = src["y"] + src["height"] / 2
            if tx >= sx:
                return [[src["x"] + src["width"], center_y], [tgt["x"], center_y]]
            return [[src["x"], center_y], [tgt["x"] + tgt["width"], center_y]]
        if ty_top > sy_bottom:
            middle = (sy_bottom + ty_top) / 2
            return [[sx, sy_bottom], [sx, middle], [tx, middle], [tx, ty_top]]
        middle = (ty_bottom + sy_top) / 2
        return [[sx, sy_top], [sx, middle], [tx, middle], [tx, ty_bottom]]

    downward = tgt_band["y"] > src_band["y"]
    adjacent = tgt_band["index"] == src_band["index"] + 1 if downward else tgt_band["index"] == src_band["index"] - 1
    channels = _column_channels(geom["node_x0"], geom["node_x1"], geom["node_w"], col_gap, src["columns"])
    if downward:
        channel_y = src_band["y"] + src_band["height"] + band_gap / 2
        target_edge, leave_y = ty_top, sy_bottom
        outer_row = src["row"] == src["rows"] - 1
        side_y = leave_y + row_gap / 2
    else:
        channel_y = src_band["y"] - band_gap / 2
        target_edge, leave_y = ty_bottom, sy_top
        outer_row = src["row"] == 0
        side_y = leave_y - row_gap / 2

    if outer_row and abs(sx - tx) < 6:
        return [[sx, leave_y], [tx, target_edge]]
    if outer_row:
        if adjacent:
            return [[sx, leave_y], [sx, channel_y], [tx, channel_y], [tx, target_edge]]
        right_channel = max(channels)
        target_channel_y = tgt_band["y"] - band_gap / 2 if downward else tgt_band["y"] + tgt_band["height"] + band_gap / 2
        return [[sx, leave_y], [sx, channel_y], [right_channel, channel_y], [right_channel, target_channel_y], [tx, target_channel_y], [tx, target_edge]]

    channel_x = _nearest_channel(sx, channels)
    return [[sx, leave_y], [sx, side_y], [channel_x, side_y], [channel_x, channel_y], [tx, channel_y], [tx, target_edge]]


def _sort_band(nodes: list[Any], neighbours: dict[str, list[str]], positions: dict[str, tuple[int, int]], allowed: set[str], flows: dict[str, set[str]]) -> list[Any]:
    """Order one band by the barycenter of its links into already-placed bands.

    ``positions`` maps node id -> (band index, index inside band) for the whole layout, so
    the barycenter is comparable across bands. Nodes with no link into a placed band keep
    their current slot, which keeps the sweep stable.
    """
    current = {node.id: index for index, node in enumerate(nodes)}

    def sort_key(node):
        pairs = [positions[other] for other in neighbours.get(node.id, []) if other in allowed and other in positions]
        if pairs:
            band_mean = sum(pair[0] for pair in pairs) / len(pairs)
            index_mean = sum(pair[1] for pair in pairs) / len(pairs)
        else:
            band_mean, index_mean = float(positions[node.id][0]), float(current[node.id])
        group = 1 if node.id in flows["down"] and node.id not in flows["up"] else 0
        return (group, band_mean, index_mean, _priority_rank(node.priority), node.id)

    return sorted(nodes, key=sort_key)


def _sweep(bands: list[dict[str, Any]], flows: dict[str, set[str]], model: ArchitectureModel, direction: str) -> list[dict[str, Any]]:
    """Place band by band, keeping the bands already visited fixed."""
    neighbours: dict[str, list[str]] = {}
    for rel in model.relations:
        neighbours.setdefault(rel.source, []).append(rel.target)
        neighbours.setdefault(rel.target, []).append(rel.source)

    ordered = [dict(band, nodes=list(band["nodes"])) for band in bands]
    order = list(range(1, len(ordered))) if direction == "down" else list(range(len(ordered) - 2, -1, -1))
    placed = {0} if direction == "down" else {len(ordered) - 1}
    for index in order:
        positions = {node.id: (band_index, position) for band_index, band in enumerate(ordered) for position, node in enumerate(band["nodes"])}
        allowed = {node.id for band_index in placed for node in ordered[band_index]["nodes"]}
        ordered[index]["nodes"] = _sort_band(ordered[index]["nodes"], neighbours, positions, allowed, flows)
        placed.add(index)
    return ordered


def _alignment_score(geom: dict[str, Any], model: ArchitectureModel) -> int:
    """Count relations whose endpoints share a column; higher means fewer dog-legs."""
    column_of = {element["id"]: element["column"] for element in geom["elements"]}
    score = 0
    for rel in model.relations:
        source, target = column_of.get(rel.source), column_of.get(rel.target)
        if source is not None and source == target:
            score += 1
    return score


def plan_layout(model: ArchitectureModel | dict, *, width: float = CANVAS_WIDTH, height: float = CANVAS_HEIGHT) -> dict[str, Any]:
    m = model if isinstance(model, ArchitectureModel) else ArchitectureModel.from_dict(model)
    bands, flows = _group_bands(m)
    if not bands:
        return {"canvas": {"width": width, "height": height}, "bands": [], "elements": [], "relations": [], "architecture_type": m.architecture_type}

    # Bands pull on each other, so barycenter ordering is done as a sweep with the already
    # visited bands fixed; both sweep directions are scored and the better one wins.
    geom = _geometry(bands, width, height)
    best_bands, best_geom, best_score = bands, geom, _alignment_score(geom, m)
    for direction in ("down", "up"):
        candidate = _sweep(bands, flows, m, direction)
        candidate_geom = _geometry(candidate, width, height)
        score = _alignment_score(candidate_geom, m)
        if score > best_score:
            best_bands, best_geom, best_score = candidate, candidate_geom, score
    bands, geom = best_bands, best_geom
    elements = geom["elements"]
    by_id = {element["id"]: element for element in elements}
    bands_by_index = {band["index"]: band for band in geom["bands"]}

    relations: list[dict[str, Any]] = []
    for rel in m.relations:
        src, tgt = by_id.get(rel.source), by_id.get(rel.target)
        if src is None or tgt is None:
            continue
        points = _route(src, tgt, bands_by_index, geom)
        entry = {
            "id": rel.id, "from": rel.source, "to": rel.target, "label": rel.label,
            "route": "polyline", "points": points,
        }
        if rel.label:
            entry["_anchor"] = _run_anchor(points)
        relations.append(entry)

    canvas_height = max(height, geom["bottom"] + BOTTOM_MARGIN)
    _place_labels(relations, elements, width, canvas_height)
    return {
        "canvas": {"width": width, "height": canvas_height},
        "bands": geom["bands"], "elements": elements, "relations": relations,
        "architecture_type": m.architecture_type,
    }

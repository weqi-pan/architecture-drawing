"""Agent-first document-to-editable-PPTX orchestration.

The runtime/Agent owns document reading and semantic extraction. This CLI consumes
an Agent ArchitectureModel JSON contract; it does not implement a DOCX/PDF parser.
"""
from __future__ import annotations

import argparse, json, re
from pathlib import Path
from typing import Any

from src.adapters.document_to_architecture import document_to_architecture_input
from src.architecture.analyzer import analyze
from src.architecture.simplifier import simplify
from src.architecture.type_selector import apply_type
from src.layout.planner import plan_layout
from src.layout.validator import validate_layout
from src.style.planner import plan_style
from src.renderers.ppt_writer import write_pptx, PPTDependencyError

_FILENAME_UNSAFE = re.compile(r'[\\/:*?"<>|\r\n\t]+')
_AGENT_MODEL_SUFFIX = ".json"


def _safe_filename(value: str, fallback: str = "architecture") -> str:
    name = _FILENAME_UNSAFE.sub("-", str(value or "").strip()).strip(" .-")
    return name[:80] or fallback


def _blocked_payload(source: Path, message: str) -> dict[str, Any]:
    return {
        "document_title": source.stem,
        "agent_status": "DOCUMENT_READ_BLOCKED",
        "diagnostics": [{"code": "DOCUMENT_READ_BLOCKED", "severity": "error", "message": message}],
    }


def _read_agent_input(source: Path) -> tuple[dict[str, Any], str]:
    """Load the Agent ArchitectureModel contract. Raw documents are not parsed here."""
    if source.suffix.lower() != _AGENT_MODEL_SUFFIX:
        hint = (
            f"{source.name} 不是 Agent 模型 JSON。请先用 scripts/prepare_source.py 把 "
            f"{source.suffix or '该文件'} 转换成可读文本交给 Agent，由 Agent 产出 ArchitectureModel JSON 后再运行本命令。"
        )
        return _blocked_payload(source, hint), "blocked"
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return _blocked_payload(source, str(exc)), "blocked"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return _blocked_payload(source, f"JSON contract invalid: {exc}"), "blocked"
    return (payload if isinstance(payload, dict) else {"text": text}), "ok"


def _extraction_block(model) -> tuple[str, str] | None:
    """Refuse to draw when no Agent-produced semantics are available."""
    if not model.nodes:
        return (
            "DOCUMENT_READ_BLOCKED",
            "No readable Agent ArchitectureModel was available; no architecture diagram was fabricated.",
        )
    agent_backed = model.metadata.get("semantic_source") == "agent"
    if not agent_backed and all(n.type == "unclassified_evidence" for n in model.nodes):
        return (
            "ARCHITECTURE_EXTRACTION_INSUFFICIENT_EVIDENCE",
            "Only unclassified evidence was available. Supply an Agent-produced ArchitectureModel instead of raw document text.",
        )
    return None


def _analysis_markdown(model, status: str, style: dict[str, Any], pptx_name: str, block: tuple[str, str] | None) -> str:
    diagnostics = list(model.diagnostics or [])
    if block:
        diagnostics.append({"code": block[0], "message": block[1]})
    lines = [
        f"# {model.title}", "", "## Agent semantic analysis", "",
        f"- semantic_source: {model.metadata.get('semantic_source', 'unknown')}",
        f"- agent_status: {status}",
        f"- view: {model.metadata.get('view', model.title)}",
        f"- architecture_type: {model.architecture_type}",
        f"- nodes: {len(model.nodes)}",
        f"- relations: {len(model.relations)}",
        f"- style_mode: {style.get('mode')}",
        f"- style_id: {style.get('style_id')}",
        f"- pptx: {pptx_name or 'BLOCKED'}",
        "",
    ]
    if diagnostics:
        lines += ["## Diagnostics", ""] + [f"- **{d.get('code', 'DIAGNOSTIC')}**: {d.get('message', '')}" for d in diagnostics]
    return "\n".join(lines) + "\n"


def run(input_path: str | Path, output_dir: str | Path, *, style_request: str = "", style_reference: dict[str, Any] | None = None, detail_level: str = "standard", view: str = "") -> dict[str, Any]:
    source = Path(input_path); out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    raw, read_status = _read_agent_input(source)
    parsed = document_to_architecture_input(raw)
    (out / "document_structure.json").write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    model = analyze(parsed)
    for diagnostic in (raw.get("diagnostics") or []):
        if isinstance(diagnostic, dict) and diagnostic not in model.diagnostics:
            model.diagnostics.append(diagnostic)
    model = simplify(model, detail_level=detail_level)
    model = apply_type(model)
    if view.strip():
        model.title = view.strip()
        model.metadata["view"] = view.strip()
    (out / "architecture_candidates.json").write_text(json.dumps([n.to_dict() for n in model.nodes], ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "architecture_model.json").write_text(model.to_json(), encoding="utf-8")
    style = plan_style(style_request, reference=style_reference)
    style["title"] = model.title
    (out / "style_spec.json").write_text(json.dumps(style, ensure_ascii=False, indent=2), encoding="utf-8")

    block = _extraction_block(model)
    if block:
        (out / "architecture_analysis.md").write_text(_analysis_markdown(model, read_status, style, "", block), encoding="utf-8")
        report = {"valid": False, "errors": [f"{block[0]}: {block[1]}"], "warnings": []}
        (out / "validation_report.md").write_text("# Validation\n\n" + json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"model": model.to_dict(), "layout": {}, "validation": report, "pptx": "BLOCKED", "pptx_path": ""}

    pptx_path = out / f"{_safe_filename(model.title)}.pptx"
    (out / "architecture_analysis.md").write_text(_analysis_markdown(model, read_status, style, pptx_path.name, None), encoding="utf-8")
    layout = plan_layout(model)
    (out / "architecture_layout.json").write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
    report = validate_layout(layout)
    (out / "validation_report.md").write_text("# Validation\n\n" + json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        write_pptx(model, layout, style, pptx_path); ppt_status = "PASS"
    except PPTDependencyError as exc:
        ppt_status = f"SKIPPED: {exc}"; pptx_path = Path("")
    return {"model": model.to_dict(), "layout": layout, "validation": report, "pptx": ppt_status, "pptx_path": str(pptx_path) if str(pptx_path) else ""}


def main() -> int:
    ap = argparse.ArgumentParser(description="Agent-first ArchitectureModel-to-editable-PPTX pipeline")
    ap.add_argument("input", help="Agent ArchitectureModel JSON")
    ap.add_argument("-o", "--output-dir", default="artifacts")
    ap.add_argument("--view", default="", help="图名，例如 '系统架构图'；决定输出 pptx 文件名与标题")
    ap.add_argument("--style", default="")
    ap.add_argument("--detail-level", choices=["overview", "standard", "detailed"], default="standard")
    args = ap.parse_args()
    result = run(args.input, args.output_dir, style_request=args.style, detail_level=args.detail_level, view=args.view)
    print(json.dumps({"validation": result["validation"], "pptx": result["pptx"], "pptx_path": result["pptx_path"]}, ensure_ascii=False, indent=2))
    return 0 if result["validation"].get("valid") else 2


if __name__ == "__main__":
    raise SystemExit(main())

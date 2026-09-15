"""Normalize a source document into Agent-readable UTF-8 text with locators.

Scope: DOCX (paragraphs, heading levels, tables, image markers), Markdown and TXT.
No OCR, no layout interpretation, no semantic extraction: the Agent reads the output
and produces the ArchitectureModel itself. PDF and other binaries are reported as
unsupported instead of being guessed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": WNS}

TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
DOCX_SUFFIX = ".docx"
UNSUPPORTED_SUFFIXES = {".pdf", ".ppt", ".pptx", ".xls", ".xlsx", ".rtf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

# Source files are untrusted input: a DOCX is a ZIP, so a small file can declare a huge
# entry (zip bomb) or thousands of parts. Read the main part with a hard cap instead of
# trusting the declared size, and bound the extracted blocks.
MAX_DOCX_ENTRY_BYTES = 48 * 1024 * 1024
MAX_DOCX_ENTRIES = 5000
MAX_BLOCKS = 20000
MAX_BLOCK_CHARS = 200000

_HEADING_STYLE = re.compile(r"(?:[Hh]eading|标题)\s*(\d)")
_BLANK_RUN = re.compile(r"\n{3,}")


class SourceLimitExceeded(ValueError):
    """Raised when an input document exceeds the documented extraction limits."""


def _normalize_text(value: str) -> str:
    text = value.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    return _BLANK_RUN.sub("\n\n", text).strip("\n")


def _xml_local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _paragraph_text(paragraph) -> str:
    parts: list[str] = []
    for node in paragraph.iter():
        local = _xml_local(node.tag)
        if local == "t":
            parts.append(node.text or "")
        elif local == "tab":
            parts.append("\t")
        elif local in {"br", "cr"}:
            parts.append("\n")
    return _normalize_text("".join(parts))


def _paragraph_level(paragraph) -> int:
    properties = paragraph.find("w:pPr", NS)
    if properties is None:
        return 0
    style = properties.find("w:pStyle", NS)
    if style is None:
        return 0
    match = _HEADING_STYLE.search(style.get(f"{{{WNS}}}val") or "")
    return int(match.group(1)) if match else 0


def _has_image(paragraph) -> bool:
    return any(_xml_local(node.tag) in {"drawing", "pict", "object"} for node in paragraph.iter())


def _table_rows(table) -> list[list[str]]:
    rows: list[list[str]] = []
    for row in table.findall("w:tr", NS):
        cells: list[str] = []
        for cell in row.findall("w:tc", NS):
            cell_text = " / ".join(text for text in (_paragraph_text(p) for p in cell.findall("w:p", NS)) if text)
            cells.append(cell_text)
        rows.append(cells)
    return rows


def read_docx(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    blocks: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = []
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_DOCX_ENTRIES:
                raise SourceLimitExceeded(
                    f"DOCX 包含 {len(infos)} 个部件，超过上限 {MAX_DOCX_ENTRIES}；请确认文件来源。"
                )
            if "word/document.xml" not in archive.namelist():
                raise KeyError("word/document.xml")
            # Read with a cap so a lying local header or a zip bomb cannot exhaust memory.
            with archive.open("word/document.xml") as handle:
                data = handle.read(MAX_DOCX_ENTRY_BYTES + 1)
            if len(data) > MAX_DOCX_ENTRY_BYTES:
                raise SourceLimitExceeded(
                    f"word/document.xml 超过上限 {MAX_DOCX_ENTRY_BYTES // (1024 * 1024)} MiB；本脚本只做正文规范化，不处理超大文档。"
                )
            document = ET.fromstring(data)
    except SourceLimitExceeded:
        raise
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as exc:
        raise ValueError(f"无法读取 DOCX 正文: {exc}") from exc

    body = document.find("w:body", NS)
    if body is None:
        raise ValueError("DOCX 缺少 word/document.xml 正文节点")

    paragraph_index = 0
    table_index = 0
    for child in body:
        if len(blocks) >= MAX_BLOCKS:
            diagnostics.append({"code": "BLOCK_LIMIT_REACHED", "message": f"已提取 {MAX_BLOCKS} 个 block，后续内容被忽略"})
            break
        local = _xml_local(child.tag)
        if local == "p":
            paragraph_index += 1
            text = _paragraph_text(child)[:MAX_BLOCK_CHARS]
            if _has_image(child):
                blocks.append({"kind": "asset", "level": 0, "text": "[图片]", "locator": f"p{paragraph_index}"})
                diagnostics.append({"code": "ASSET_NOT_READ", "message": f"p{paragraph_index} 含图片，未做 OCR，请人工确认或使用 OCR 能力"})
            if not text:
                continue
            level = _paragraph_level(child)
            blocks.append({
                "kind": "heading" if level else "paragraph",
                "level": level,
                "text": text,
                "locator": f"p{paragraph_index}",
            })
        elif local == "tbl":
            table_index += 1
            rows = _table_rows(child)
            if not rows:
                continue
            blocks.append({
                "kind": "table",
                "level": 0,
                "rows": rows,
                "text": "\n".join(" | ".join(cell for cell in row) for row in rows)[:MAX_BLOCK_CHARS],
                "locator": f"t{table_index}",
            })
    return blocks, diagnostics


def _markdown_blocks(text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if not stripped:
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading:
            blocks.append({"kind": "heading", "level": len(heading.group(1)), "text": heading.group(2).strip(), "locator": f"L{index}"})
        else:
            blocks.append({"kind": "paragraph", "level": 0, "text": stripped, "locator": f"L{index}"})
    return blocks


def _text_blocks(text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if stripped:
            blocks.append({"kind": "paragraph", "level": 0, "text": stripped, "locator": f"L{index}"})
    return blocks


def _table_markdown(rows: list[list[str]]) -> str:
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    header, *rest = padded
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * width) + " |"]
    lines += ["| " + " | ".join(cell.replace("\n", " ") for cell in row) + " |" for row in rest]
    return "\n".join(lines)


def render_markdown(title: str, blocks: list[dict[str, Any]]) -> str:
    lines = [f"# {title}", ""]
    for block in blocks:
        if block["kind"] == "heading":
            lines += ["#" * min(6, max(1, int(block.get("level") or 1))) + " " + str(block["text"]), ""]
        elif block["kind"] == "table":
            lines += [_table_markdown(block.get("rows") or []), ""]
        elif block["kind"] == "asset":
            lines += [str(block["text"]), ""]
        else:
            lines += [str(block["text"]), ""]
    return _normalize_text("\n".join(lines)) + "\n"


def prepare(source: Path, out_dir: Path, title: str = "") -> dict[str, Any]:
    suffix = source.suffix.lower()
    if suffix in UNSUPPORTED_SUFFIXES or suffix not in {DOCX_SUFFIX, *TEXT_SUFFIXES}:
        raise NotImplementedError(
            f"暂不支持 {suffix or '无后缀'} 输入。DOCX / Markdown / TXT 请走本脚本；PDF、扫描件和图片请先使用仓库已有的 OCR 或 MinerU 预处理能力，不要伪造正文。"
        )
    if not source.exists():
        raise FileNotFoundError(f"源文件不存在: {source}")

    diagnostics: list[dict[str, str]] = []
    if suffix == DOCX_SUFFIX:
        blocks, diagnostics = read_docx(source)
        source_format = "docx"
    else:
        size = source.stat().st_size
        if size > MAX_DOCX_ENTRY_BYTES:
            raise SourceLimitExceeded(f"{source.name} 为 {size} 字节，超过上限 {MAX_DOCX_ENTRY_BYTES // (1024 * 1024)} MiB。")
        text = _normalize_text(source.read_text(encoding="utf-8", errors="replace"))
        blocks = _markdown_blocks(text) if suffix in {".md", ".markdown"} else _text_blocks(text)
        source_format = "markdown" if suffix in {".md", ".markdown"} else "text"
        if len(blocks) > MAX_BLOCKS:
            blocks = blocks[:MAX_BLOCKS]
            diagnostics.append({"code": "BLOCK_LIMIT_REACHED", "message": f"已提取 {MAX_BLOCKS} 个 block，后续内容被忽略"})

    document_title = title.strip() or source.stem
    if not blocks:
        diagnostics.append({"code": "EMPTY_SOURCE", "message": "未提取到任何正文内容"})

    out_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = out_dir / f"{source.stem}.md"
    markdown_path.write_text(render_markdown(document_title, blocks), encoding="utf-8")
    payload = {
        "document_title": document_title,
        "source_file": source.name,
        "source_format": source_format,
        "block_count": len(blocks),
        "text_path": markdown_path.name,
        "blocks": blocks,
        "diagnostics": diagnostics,
    }
    json_path = out_dir / f"{source.stem}.source.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["json_path"] = str(json_path)
    payload["markdown_path"] = str(markdown_path)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="把 docx/md/txt 规范化为 Agent 可读的 UTF-8 文本与带定位的 blocks")
    parser.add_argument("input", help="源文档路径（.docx/.md/.txt）")
    parser.add_argument("-o", "--output-dir", default="prepared", help="输出目录，默认 prepared")
    parser.add_argument("--title", default="", help="覆盖文档标题")
    args = parser.parse_args()
    try:
        result = prepare(Path(args.input), Path(args.output_dir), title=args.title)
    except NotImplementedError as exc:
        print(json.dumps({"status": "UNSUPPORTED", "message": str(exc)}, ensure_ascii=False, indent=2))
        return 3
    except SourceLimitExceeded as exc:
        print(json.dumps({"status": "LIMIT_EXCEEDED", "message": str(exc)}, ensure_ascii=False, indent=2))
        return 4
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(json.dumps({"status": "ERROR", "message": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({
        "status": "OK",
        "document_title": result["document_title"],
        "source_format": result["source_format"],
        "block_count": result["block_count"],
        "json_path": result["json_path"],
        "markdown_path": result["markdown_path"],
        "diagnostics": result["diagnostics"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

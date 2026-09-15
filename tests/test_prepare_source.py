import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import prepare_source

DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>项目总体架构</w:t></w:r></w:p>
    <w:p><w:r><w:t>平台汇聚各业务系统的数据。</w:t></w:r></w:p>
    <w:p><w:r><w:drawing/></w:r></w:p>
    <w:tbl>
      <w:tr><w:tc><w:p><w:r><w:t>模块</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>说明</w:t></w:r></w:p></w:tc></w:tr>
      <w:tr><w:tc><w:p><w:r><w:t>数据中台</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>汇聚共享</w:t></w:r></w:p></w:tc></w:tr>
    </w:tbl>
  </w:body>
</w:document>"""


def write_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", DOCUMENT_XML)


class PrepareSourceTests(unittest.TestCase):
    def test_docx_blocks_headings_tables_and_asset_markers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "report.docx"
            write_docx(source)
            result = prepare_source.prepare(source, root / "prepared")

            kinds = [(b["kind"], b.get("level", 0)) for b in result["blocks"]]
            self.assertIn(("heading", 1), kinds)
            self.assertIn(("paragraph", 0), kinds)
            self.assertIn(("table", 0), kinds)
            self.assertIn(("asset", 0), kinds)
            self.assertEqual("report", result["document_title"])
            self.assertEqual("docx", result["source_format"])

            heading = next(b for b in result["blocks"] if b["kind"] == "heading")
            self.assertEqual("项目总体架构", heading["text"])
            table = next(b for b in result["blocks"] if b["kind"] == "table")
            self.assertEqual([["模块", "说明"], ["数据中台", "汇聚共享"]], table["rows"])
            self.assertEqual("t1", table["locator"])
            self.assertTrue(any(d["code"] == "ASSET_NOT_READ" for d in result["diagnostics"]))

            markdown = (root / "prepared" / "report.md").read_text(encoding="utf-8")
            self.assertIn("# 项目总体架构", markdown)
            self.assertIn("| 数据中台 | 汇聚共享 |", markdown)
            payload = json.loads((root / "prepared" / "report.source.json").read_text(encoding="utf-8"))
            self.assertEqual(result["blocks"], payload["blocks"])

    def test_markdown_and_text_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            md = root / "design.md"
            md.write_text("# 分层设计\n\n## 数据层\n平台汇聚数据。\n", encoding="utf-8")
            result = prepare_source.prepare(md, root / "out")
            self.assertEqual("markdown", result["source_format"])
            self.assertEqual([1, 2, 0], [b.get("level", 0) for b in result["blocks"]])

            txt = root / "notes.txt"
            txt.write_text("第一行\n\n第二行\n", encoding="utf-8")
            result = prepare_source.prepare(txt, root / "out2")
            self.assertEqual("text", result["source_format"])
            self.assertEqual(["第一行", "第二行"], [b["text"] for b in result["blocks"]])

    def test_unsupported_and_missing_inputs_are_reported(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pdf = root / "report.pdf"
            pdf.write_bytes(b"%PDF-1.4")
            with self.assertRaises(NotImplementedError):
                prepare_source.prepare(pdf, root / "out")
            with self.assertRaises(FileNotFoundError):
                prepare_source.prepare(root / "missing.docx", root / "out")

    def test_oversized_document_part_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "bomb.docx"
            write_docx(source)
            original = prepare_source.MAX_DOCX_ENTRY_BYTES
            prepare_source.MAX_DOCX_ENTRY_BYTES = 32
            try:
                with self.assertRaises(prepare_source.SourceLimitExceeded):
                    prepare_source.prepare(source, root / "out")
            finally:
                prepare_source.MAX_DOCX_ENTRY_BYTES = original

    def test_too_many_document_parts_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "many.docx"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("word/document.xml", DOCUMENT_XML)
                for index in range(12):
                    archive.writestr(f"customXml/item{index}.xml", "<a/>")
            original = prepare_source.MAX_DOCX_ENTRIES
            prepare_source.MAX_DOCX_ENTRIES = 5
            try:
                with self.assertRaises(prepare_source.SourceLimitExceeded):
                    prepare_source.prepare(source, root / "out")
            finally:
                prepare_source.MAX_DOCX_ENTRIES = original

    def test_block_limit_is_reported_as_a_diagnostic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            txt = root / "long.txt"
            txt.write_text("\n".join(f"第{i}段" for i in range(40)), encoding="utf-8")
            original = prepare_source.MAX_BLOCKS
            prepare_source.MAX_BLOCKS = 10
            try:
                result = prepare_source.prepare(txt, root / "out")
            finally:
                prepare_source.MAX_BLOCKS = original
            self.assertEqual(10, result["block_count"])
            self.assertTrue(any(d["code"] == "BLOCK_LIMIT_REACHED" for d in result["diagnostics"]), result["diagnostics"])

    def test_missing_document_part_is_reported_without_crashing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "empty.docx"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("word/styles.xml", "<a/>")
            with self.assertRaises(ValueError):
                prepare_source.prepare(source, root / "out")


if __name__ == "__main__":
    unittest.main()

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.adapters.document_to_architecture import document_to_architecture_input
from src.architecture.analyzer import analyze
from src.pipeline.run import run


class AgentFirstPipelineTests(unittest.TestCase):
    def agent_contract(self):
        return {
            "title": "Agent contract",
            "project": "demo",
            "architecture_type": "LAYERED",
            "nodes": [
                {"id": "user", "title": "User", "level": "L1", "source_evidence": [{"section": "Goal", "quote": "User accesses platform"}]},
                {"id": "platform", "title": "Platform", "level": "L1", "source_evidence": [{"section": "Scope", "quote": "Unified platform"}]},
            ],
            "relations": [{"id": "r1", "source": "user", "target": "platform", "relation_type": "uses", "explicit": True}],
        }

    def test_agent_contract_is_preserved_without_keyword_inference(self):
        payload = document_to_architecture_input(self.agent_contract())
        model = analyze(payload)
        self.assertEqual("agent", model.metadata["semantic_source"])
        self.assertEqual({"user", "platform"}, {n.id for n in model.nodes})
        self.assertEqual("User accesses platform", model.nodes[0].source_evidence[0].quote)
        self.assertEqual("r1", model.relations[0].id)

    def test_structured_fallback_emits_diagnostic(self):
        model = analyze(document_to_architecture_input({"document_title": "Plain", "text": "Readable prose"}))
        self.assertEqual("AGENT_MODEL_MISSING", model.diagnostics[0]["code"])
        self.assertEqual("unclassified_evidence", model.nodes[0].type)

    def test_pipeline_writes_named_pptx_and_reference_style(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "model.json"
            source.write_text(json.dumps(self.agent_contract()), encoding="utf-8")
            result = run(source, root / "out", style_reference={"colors": {"primary": "#123456"}}, view="系统架构图")
            self.assertTrue(result["validation"]["valid"], result)
            self.assertEqual("PASS", result["pptx"])
            self.assertEqual("系统架构图.pptx", Path(result["pptx_path"]).name)
            self.assertTrue((root / "out" / "系统架构图.pptx").exists())
            self.assertFalse((root / "out" / "architecture_preview.png").exists())
            self.assertIn("REFERENCE_STYLE", (root / "out" / "style_spec.json").read_text(encoding="utf-8"))
            self.assertIn("view: 系统架构图", (root / "out" / "architecture_analysis.md").read_text(encoding="utf-8"))

    def test_unclassified_evidence_is_not_rendered(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "parsed.json"
            source.write_text(json.dumps({"document_title": "Parser payload", "paragraphs": ["平台汇聚数据。"]}), encoding="utf-8")
            result = run(source, root / "out")
            self.assertEqual("BLOCKED", result["pptx"])
            self.assertFalse(result["validation"]["valid"])
            self.assertIn("ARCHITECTURE_EXTRACTION_INSUFFICIENT_EVIDENCE", (root / "out" / "validation_report.md").read_text(encoding="utf-8"))
            self.assertEqual([], list((root / "out").glob("*.pptx")))

    def test_raw_document_is_blocked_with_hint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "report.docx"
            source.write_bytes(b"not parsed here")
            result = run(source, root / "out")
            self.assertEqual("BLOCKED", result["pptx"])
            self.assertFalse(result["validation"]["valid"])
            analysis = (root / "out" / "architecture_analysis.md").read_text(encoding="utf-8")
            self.assertIn("DOCUMENT_READ_BLOCKED", analysis)

    def test_raw_text_is_blocked_with_prepare_source_hint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "notes.txt"
            source.write_text("平台汇聚数据。", encoding="utf-8")
            result = run(source, root / "out")
            self.assertEqual("BLOCKED", result["pptx"])
            self.assertIn("prepare_source.py", (root / "out" / "architecture_analysis.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

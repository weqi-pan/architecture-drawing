import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.adapters.document_to_architecture import document_to_architecture_input
from src.architecture.analyzer import analyze
from src.architecture.type_selector import apply_type
from src.layout.planner import plan_layout
from src.layout.validator import validate_layout


def layered(nodes):
    """Build a model from (id, title, layer, level, priority) tuples."""
    return apply_type(analyze(document_to_architecture_input({
        "document_title": "分层样例",
        "nodes": [{"id": i, "title": t, "layer": l, "level": lv, "priority": p} for i, t, l, lv, p in nodes],
        "relations": [],
    })))


class GenericArchitectureRegression(unittest.TestCase):
    def make(self, title, paragraphs):
        return apply_type(analyze(document_to_architecture_input({"document_title":title,"paragraphs":paragraphs,"sections":[],"tables":[]})))
    def test_three_domains_are_not_hardcoded_to_healthcare(self):
        models=[self.make("医疗",["医院平台汇聚数据。"]), self.make("AI",["Agent平台调用模型服务。"]), self.make("工业",["设备网络连接数据平台。"])]
        self.assertEqual(3,len({m.title for m in models}))
        self.assertTrue(all(m.nodes for m in models))
        self.assertGreaterEqual(len({m.nodes[0].description for m in models}),3)
    def test_layout_validation(self):
        model=self.make("Example",["用户访问平台。","平台保存数据。"])
        report=validate_layout(plan_layout(model))
        self.assertTrue(report["valid"], report)

    def test_layers_become_ordered_bands(self):
        model = layered([
            ("a1", "服务对象", "服务对象层", "L1", "primary"),
            ("b1", "业务应用", "业务应用层", "L2", "primary"),
            ("b2", "辅助应用", "业务应用层", "L2", "secondary"),
            ("c1", "平台能力", "平台支撑层", "L3", "primary"),
            ("d1", "数据资源", "数据资源层", "L4", "primary"),
        ])
        layout = plan_layout(model)
        self.assertEqual(["服务对象层", "业务应用层", "平台支撑层", "数据资源层"], [b["name"] for b in layout["bands"]])
        tops = [b["y"] for b in layout["bands"]]
        self.assertEqual(tops, sorted(tops), "bands must stack top-down by level")
        for band in layout["bands"]:
            self.assertIn("label", band)
            self.assertTrue(band["height"] > 0)
        self.assertEqual([], layout["relations"])

    def test_elements_stay_inside_their_band_and_do_not_overlap(self):
        model = layered([(f"n{i}", f"节点{i}", "业务应用层" if i < 8 else "平台支撑层", "L2" if i < 8 else "L3", "primary" if i % 2 else "secondary") for i in range(12)])
        layout = plan_layout(model)
        report = validate_layout(layout)
        self.assertTrue(report["valid"], report)
        bands = {b["name"]: b for b in layout["bands"]}
        for element in layout["elements"]:
            band = bands[element["band"]]
            self.assertGreaterEqual(element["x"], band["x"])
            self.assertLessEqual(element["x"] + element["width"], band["x"] + band["width"])
            self.assertGreaterEqual(element["y"], band["y"])
            self.assertLessEqual(element["y"] + element["height"], band["y"] + band["height"])

    def test_multi_row_band_fits_the_single_slide_without_warning(self):
        model = layered([(f"n{i}", f"节点{i}", "业务应用层", "L2", "primary") for i in range(8)])
        layout = plan_layout(model)
        report = validate_layout(layout)
        self.assertTrue(report["valid"], report)
        self.assertEqual([], report["warnings"])
        self.assertLessEqual(layout["canvas"]["height"], 720)
        self.assertEqual({2}, {element["rows"] for element in layout["elements"]}, "8 nodes wrap to 4 columns x 2 rows")

    def test_band_overflow_warns_instead_of_failing(self):
        model = layered([(f"n{i}", f"节点{i}", "业务应用层", "L2", "primary") for i in range(60)])
        layout = plan_layout(model)
        report = validate_layout(layout)
        self.assertTrue(report["valid"], report)
        self.assertGreater(layout["canvas"]["height"], 720)
        self.assertTrue(any("single-slide bounds" in w for w in report["warnings"]), report)


if __name__ == "__main__": unittest.main()

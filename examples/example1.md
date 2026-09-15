# 示例 1：Agent 模型生成可编辑 PPTX

默认路径：Agent 先提供 `ArchitectureModel`，再由确定性代码生成布局和可编辑 PPTX。唯一输出是 pptx。

```powershell
python scripts/main.py examples/model/government-overall.sample.json -o artifacts/example1 --view "系统架构图" --style government_blue
```

产物目录 `artifacts/example1/`：

- `系统架构图.pptx` —— 交付物，节点、文本、连接线均为原生可编辑对象
- `architecture_model.json`、`architecture_candidates.json`、`architecture_layout.json`
- `architecture_analysis.md`、`style_spec.json`、`validation_report.md`
- `document_structure.json`

最小模型输入至少包含：

```json
{
  "title": "项目总体架构",
  "architecture_type": "LAYERED",
  "nodes": [{"id": "platform", "title": "核心平台", "level": "L1", "priority": "primary"}],
  "relations": [{"id": "r1", "source": "platform", "target": "app", "relation_type": "supports"}]
}
```

`architecture_type` 可选，缺省时由代码归一化。不生成 PNG，也不生成 Draw.io。

# 示例 2：从 DOCX 报告到文本，再交给 Agent

用户给的是报告文档时，先规范化成 Agent 可读文本：

```powershell
python scripts/prepare_source.py "项目报告.docx" -o prepared --title "项目总体架构"
```

输出：

- `prepared/项目报告.md`：标题层级、段落、管道表格
- `prepared/项目报告.source.json`：`blocks[]` 含 `kind` / `level` / `text` / `locator`

Agent 依据这些 blocks 抽取架构语义，写出 `agent-model.json`，再执行示例 1 的命令。`locator` 可直接作为节点 `source_evidence` 的定位。

PDF、扫描件和图片不在本脚本范围内，会返回 `UNSUPPORTED`（退出码 3），需要先使用仓库已有的 OCR 或 MinerU 能力。

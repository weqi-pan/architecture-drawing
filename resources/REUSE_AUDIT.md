# 能力边界与复用审计

审计更新日期：2026-09-15（4.0.0）

## 当前形态

技能只做一件事：把 Agent 产出的 `ArchitectureModel` JSON 确定性地渲染成**原生可编辑的 PowerPoint 架构图**，并提供把 docx/md/txt 变成 Agent 可读文本的预处理脚本。唯一输出是 pptx。

## 复用决策

- **KEEP**：`src/architecture/model.py`、`simplifier.py`、`type_selector.py`、`src/style/planner.py`、`src/layout/planner.py`、`src/layout/validator.py`、`src/renderers/ppt_writer.py`、`src/renderers/ppt_ooxml.py`、`scripts/prepare_source.py`、`scripts/validate_ooxml_effects.py`。
- **ADAPT**：`src/architecture/analyzer.py`（Agent 输出后处理与兼容归一化）、`src/adapters/document_to_architecture.py`（已有 parser/runtime 载荷适配）、`src/pipeline/run.py`（编排 + 无 Agent 语义不出图门禁）。
- **DATA**：`resources/themes/*.json` 是纯数据，新增主题不改代码。
- **不引入**：不重新实现 DOCX/PDF NLP 解析；`prepare_source.py` 只做格式转换、标题层级识别和表格/图片标记，不做 OCR、不做语义理解。

## 4.0.0 移除清单及原因

| 移除项 | 原因 |
|---|---|
| Draw.io 渲染/校验/修复脚本与提示词、模板 | 不是默认路径，`src/` 从不引用；保留只会让对外叙事和目录体积变复杂 |
| evidence / diagram_spec / layout_intent / layout_plan 链路 | 属于"长报告 → 可追溯证据 → Draw.io"的独立分支；ArchitectureModel 已承载 `source_evidence` |
| PNG 预览渲染器 | 需求收敛为只出 pptx；预览只是几何自检且节点标签用的是 id |
| 纯文本静默降级 | 会把"没做语义分析"的文档画成图，属于自欺路径 |
| `generated_ppt_prompt.md` | 无内容价值的占位产物 |

## 保留的边界

- `ArchitectureModel` 继续要求核心节点/关系带 `source_evidence`：来源可追溯性是质量要求，不因移除 evidence 链路而放弃。
- legacy 代码删除后不再提供兼容入口；旧项目如需 Draw.io 请使用历史提交。

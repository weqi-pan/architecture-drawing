# Agent 语义解析 SOP

在要求 Agent 生成 ArchitectureModel 之前，先使用本提示词/指令块。

1. 取得可读文本：用户给 docx/md/txt 时先运行 `python scripts/prepare_source.py <文件> -o prepared`，读取 `<stem>.md` 与 `<stem>.source.json`；PDF、图片先走仓库已有 OCR / MinerU 能力。
2. 读取所有相关源内容，并标识无法读取或缺失的章节。
3. 说明项目身份、建设目标、用户、业务场景、领域、系统/平台、数据、AI/算法、基础设施、外部系统和显式关系。
4. 将与架构相关的结构和实现细节分开。
5. 去重别名、统一名称、聚类相关功能，并标记 primary/secondary/supporting 重要性。
6. 使用 L0 愿景、L1 架构层/领域、L2 核心模块、L3 详细功能。总览图优先使用 L1+L2。
7. 只保留显式或有充分证据支持的关系。不得为了让图形平衡而捏造节点或连线。
8. 为核心节点/关系保留 `source_evidence`，定位可引用 prepare_source 输出的 `locator`（如 `p12`、`t1`、`L34`）。
9. 根据内容选择 `LAYERED`、`DOMAIN_MATRIX`、`HUB_SPOKE`、`PIPELINE` 或 `HYBRID`。
10. 明确用户要的图名（例如"系统架构图"），它将决定输出文件名与图内标题。
11. 只返回 ArchitectureModel JSON 契约和诊断信息；不要返回坐标、PowerPoint 形状指令、Draw.io XML，也不要返回预览图片指令。

失败代码：

- `DOCUMENT_READ_BLOCKED`：无法获得源文档正文。
- `ARCHITECTURE_EXTRACTION_INSUFFICIENT_EVIDENCE`：源内容可读，但不足以提取架构（只有 unclassified_evidence 时不会出图）。
- `REFERENCE_STYLE_ANALYSIS_NOT_AVAILABLE`：参考图片不可用；使用显式主题或默认主题。

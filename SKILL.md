---
name: architecture-drawing
description: 把项目文档（docx/md/txt）或 Agent 语义模型转成原生可编辑的 PowerPoint 架构图 pptx，按层级分带排版、正交连线带箭头、内置多套配色主题。用于「生成系统架构图」「画架构图」「把调研报告、建设方案、可研变成架构图」「导出可编辑 pptx 架构图」，以及 architecture diagram、editable pptx architecture、system architecture slide 等请求。Agent 负责读懂文档并抽取语义，确定性 Python 代码负责布局、校验与 PPTX 序列化。
---

# 基于 Agent 的文档到可编辑 PowerPoint 架构图技能

## 定位

`architecture-drawing` 是一个**基于 Agent 的文档到可编辑 PowerPoint 架构图技能**。它不是 DOCX 解析库、Draw.io 生成器、医疗行业专用图生成器，也不是关键词抽取工具；输出只有原生可编辑 PPTX（没有 PNG、没有 Draw.io）。

- **Agent/runtime 或 `scripts/prepare_source.py`** 负责获得可读文本。
- **Agent** 负责理解项目目标，抽象架构语义，筛选相关概念，提取显式关系，选择架构类型，并分析可选的参考风格。
- **ArchitectureModel JSON** 是唯一输入契约，也是稳定的语义事实来源。
- **确定性 Python 代码** 负责契约校验、简化/归一化、节点布局、连接线布线、碰撞检查和 PPTX 序列化。
- **PPT 渲染器** 输出原生、可编辑的 PowerPoint 形状、文本和连接线。

不要读取文档后直接输出 PowerPoint 形状。必须先形成并校验 `ArchitectureModel`。

## 默认工作流

1. **获得可读文本。** 用户给 DOCX / Markdown / TXT 时，先运行 `python scripts/prepare_source.py <文件> -o prepared`，读取输出的 `<stem>.md` 与 `<stem>.source.json`（含 `blocks` 和 `locator`）。PDF、扫描件、图片必须先用仓库已有 OCR / MinerU 能力，不要伪造正文。
2. **先理解项目目标，再提取节点。** 至少回答：项目是什么、建设目标、服务对象、业务场景、领域、系统/平台/模块、数据源/资源、AI/算法能力、设备/基础设施、外部系统、显式关系，以及不应进入总览图的实现细节。
3. **识别架构相关概念。** 名词不自动等于节点。依据目标、主要建设内容、重复出现或独立成节的内容、跨模块连接、平台/系统/核心能力表述，以及对整体理解是否不可或缺来判断。
4. **构建语义模型。** 统一名称、去重别名、聚类相关功能、排序重要性并抽象细节。使用 L0 愿景、L1 层/领域、L2 核心模块、L3 详细功能。**把 `layer` 填成层带名（如"业务应用层"）、把 `level` 填成 `L1`…`L5`**：版式按 `level` 从上到下排列层带，同 `layer` 的节点进同一条带。总览图默认使用 L1+L2，不要绘制全部 L3 功能。
5. **只提取显式关系。** 可用关系包括 `uses`、`supports`、`serves`、`connects_to`、`depends_on`、`integrates_with`、`uploads_to`、`aggregates`、`stores`、`controls`、`monitors`、`analyzes`、`provides`、`shares_data_with`。不能为了让布局完整而臆造关系。
6. **选择架构类型。** 根据内容而不是固定模板选择 `LAYERED`、`DOMAIN_MATRIX`、`HUB_SPOKE`、`PIPELINE` 或 `HYBRID`。用户明确指定时必须遵循用户指定。该字段会写入模型和布局，但当前所有类型都按层带版式渲染。
7. **标注主次和状态。** 核心节点用 `priority: primary`（更大、更重、深色描边），一般节点用 `secondary`（更轻），未建/建议项用 `status: planned`（虚线）。版式按 `priority` / `status` 决定视觉权重，这是图面主次的主要来源。
8. **生成结构化 ArchitectureModel JSON。** 尽可能为核心节点和关系保留 `source_evidence`（可用 `prepare_source.py` 的 `locator` 作为定位）。不要为了填满行列、平衡列宽或制造对称而创建模块。关系要表达真实的层间流向（应用调用平台、平台汇聚数据），不要只连相邻节点凑形状。
9. **明确"要什么图"。** 用户说"要系统架构图"就产出系统架构图：用 `--view "系统架构图"` 决定输出文件名与图内标题。一次运行产出一个 pptx；用户要三张图就运行三次。
10. **分析可选的参考风格。** 提取颜色、层级、标题处理、模块样式、间距、线条风格和整体构图。只复用视觉语言，不复制参考图的业务内容。参考图不可用时报告 `REFERENCE_STYLE_ANALYSIS_NOT_AVAILABLE`，并使用用户指定主题或默认主题。
11. **将模型交给确定性布局。** 使用现有简化器、类型选择器、布局规划器、校验器和渲染器。布局代码不得承担项目理解工作。布局会按层带分带、按流向与重心排布节点列、正交布线和落位标签。
12. **生成可编辑 PPTX。** 使用原生形状、文本、连接线和箭头。不得嵌入截图、整页图片、Draw.io XML 或栅格化幻灯片作为架构图。不要输出 PNG 预览作为交付物。
13. **验证并修复。** 检查元素重叠、越界、是否落在所属层带内、关系端点、证据缺失和 PPTX 结构；必要时只修复几何/格式，不改变 Agent 的业务事实。
14. **报告结果。** 明确记录 Agent 读取状态、语义来源、图名、架构类型、主题、诊断、验证结果和输出文件。

## 文档读取 SOP

- 优先运行 `scripts/prepare_source.py` 获得规范化文本和源定位；它只做格式转换与定位，不做语义理解。
- 输入含多章节、表格、长报告时，同样先转换，再由 Agent 分节阅读；不要要求用户手工创建 JSON。
- 如果 runtime 无法读取原始文件，复用仓库已有能力（`document_function_extractor`、`docx_markdown_splitter`、MinerU 等），再把结果交给 Agent。
- 解析器输出只能作为 Agent 的事实输入，不能替代 Agent 的架构理解。
- 如果 Agent 无法获得正文内容，停止并报告 `DOCUMENT_READ_BLOCKED`，不得伪造模型。
- 如果内容可读但不足以提取架构，报告 `ARCHITECTURE_EXTRACTION_INSUFFICIENT_EVIDENCE`。
- 如果参考图片不可读取，报告 `REFERENCE_STYLE_ANALYSIS_NOT_AVAILABLE`，并继续使用显式或默认主题。

## Agent 与 ArchitectureModel 契约

Agent 返回以下格式。`src/architecture/model.py` 同时接受该格式和仓库已有的 `elements` / `relations` 格式。

```json
{
  "title": "项目总体架构",
  "project": "project-id",
  "architecture_type": "LAYERED",
  "goals": ["..."],
  "nodes": [{
    "id": "platform",
    "title": "核心平台",
    "type": "platform",
    "domain": "shared",
    "layer": "platform",
    "level": "L1",
    "priority": "primary",
    "status": "current",
    "description": "...",
    "source_evidence": [{"section": "...", "quote": "..."}]
  }],
  "relations": [{
    "id": "platform-serves-app",
    "source": "platform",
    "target": "application",
    "relation_type": "supports",
    "label": "支撑",
    "priority": "primary",
    "explicit": true,
    "source_evidence": [{"section": "...", "quote": "..."}]
  }],
  "source_evidence": [],
  "diagnostics": []
}
```

所有节点和关系 ID 必须唯一；关系端点必须存在。证据引用应来自可读取的源内容。`ArchitectureModel` 是传给布局和渲染阶段的唯一语义事实来源。

**质量闸门（不通过则不出图）**：模型没有 Agent 契约、且节点全部是 `unclassified_evidence` 时，流水线返回 `ARCHITECTURE_EXTRACTION_INSUFFICIENT_EVIDENCE`、退出码 2，不生成 pptx。因此不要用"逐段文本当作节点"的方式凑数。

## 风格契约

存在参考图时，Agent 返回只描述风格的对象：

```json
{
  "colors": {"primary": "#1F5A94", "secondary": "#DCEBFA", "line": "#5B7FA3", "background": "#F7FAFD"},
  "font": "Aptos",
  "title_style": {"weight": "bold", "alignment": "left"},
  "module_style": {"corner_radius": 0.08, "border": "solid"},
  "line_width": 1.25
}
```

`src/style/planner.py` 消费此契约（当前只能通过 Python API 传入），不执行图片 OCR 或语义抽取。

## 主题

内置主题：`government_blue`（政务蓝）、`scientific_blue`（科研蓝）、`enterprise_tech`（企业科技，默认）、`academic_minimal`（论文简约）、`industrial_engineering`（工业工程）、`tech_gradient`（科技渐变风）。

- 主题是数据文件 `resources/themes/*.json`，含 `colors`、`background`、`font`、`node_corner_radius`、`header`、`node`、`connector`、`effect_level`。
- 主题只改配色与效果，不改版式。新增主题只需新增一个 JSON 文件。
- CLI 用法：`--style 政务蓝` 或 `--style government_blue`。

## 代码归属与复用决策

- **KEEP：保留**：`src/architecture/model.py`、`simplifier.py`、`type_selector.py`、`src/style/planner.py`、`src/layout/planner.py`、`src/layout/validator.py`、`src/renderers/ppt_writer.py`、`src/renderers/ppt_ooxml.py`、`scripts/prepare_source.py`。
- **ADAPT：适配**：`src/architecture/analyzer.py` 仅负责 Agent 输出后处理和兼容归一化；`src/adapters/document_to_architecture.py` 负责已有 parser/runtime 载荷适配；`src/pipeline/run.py` 负责编排 Agent-first 流程并保证"无 Agent 语义不出图"。
- **LAYOUT：层带版式**：`src/layout/planner.py` 负责分带、流向排序、重心列对齐（down/up sweep 取最优）、正交布线与标签碰撞消解；`ppt_writer.py` 只负责把几何、层带和视觉权重画成原生对象。
- **SIMPLIFY：简化**：没有 Agent 模型时，只保留显式结构化证据并输出诊断，不使用正则/关键词推断架构语义。
- **REMOVED：已移除（4.0.0）**：Draw.io 渲染/校验/修复链路、evidence/spec/layout_plan 链路、PNG 预览渲染器、纯文本静默降级路径。

## 必需质量闸门

- `semantic_source` 必须能追溯到 Agent 契约；只有 `unclassified_evidence` 时不得出图。
- 核心节点/关系必须保留证据，或有明确诊断说明。
- 每个节点必须有 `layer`（或 `domain`）与 `level`；缺层信息的节点会落到最后一带并警告可读性下降。
- 不得使用仅基于关键词的语义推断作为主路径。
- 布局不得出现元素 ID 重复、越界、矩形重叠，且每个元素必须落在其所属层带内。
- PPTX 必须包含可编辑的原生形状、文本、带箭头的连接线和层带。
- 参考风格必须来自 Agent 风格契约或显式主题，或明确标记不可用。
- 任意质量闸门失败时，结果不得标记为 `PASS`。

## 层带版式约定

- **层带（band）**：同一 `layer` 的节点组成一条横向色带，左侧是层名；带按 `level` 从上到下排列。
- **行与列**：带内最多 4 列，超出自动折行；出线朝下的节点排在最后一行，朝上的排在第一行，避免连线横穿本层。
- **列对齐**：节点列号按相邻层连接对象的重心排序（down/up 两次 sweep 取最优），使上下层直上直下；同列关系为一条竖直线，跨列关系在层间空白走 Z 形。
- **箭头**：每条关系的最后一段带原生三角箭头，指向目标节点。
- **标签**：放在最长线段中点，用背景色文本框断开连线，并做碰撞消解（不压节点、不压其它标签）；无空位时不放置。
- **视觉权重**：`primary` 更大更重、`secondary` 更轻、`planned` 虚线，用主次而不是颜色堆叠来表达层级。
- **容量**：单页约 5 带 / 24 节点；8 节点的带占 2 行。超容量时布局先压缩节点高度，再溢出到画布外并给出 `single-slide bounds` 警告 —— 此时应拆图。

## 主要入口

- Agent 契约和模型：`src/architecture/model.py`
- Agent 输出归一化：`src/architecture/analyzer.py`
- 输入适配：`src/adapters/document_to_architecture.py`
- 文档规范化：`scripts/prepare_source.py`
- 简化和类型选择：`src/architecture/simplifier.py`、`src/architecture/type_selector.py`
- 风格、布局和校验：`src/style/planner.py`、`resources/themes/*.json`、`src/layout/`
- PPTX 与效果层：`src/renderers/ppt_writer.py`、`src/renderers/ppt_ooxml.py`
- Agent-first 流水线：`src/pipeline/run.py`、`scripts/main.py`

## OOXML 高级视觉效果层

1. `python-pptx` 创建 slide、shape、textbox、text、几何、基础填充、边框和连接线。
2. `src/renderers/ppt_ooxml.py` 通过 Shape XML 集中写入 `a:gradFill`、`a:effectLst`、`a:outerShdw`、`a:glow` 和 `a:alpha`。
3. 高级效果失败时保留可编辑的基础 solid fill / solid line，不使用栅格图片回退。
4. `inspect_pptx_ooxml()` 和 `scripts/validate_ooxml_effects.py` 检查 ZIP、slide XML、渐变、效果列表、重复填充和可编辑形状。

| 能力 | 状态 |
|---|---|
| solid fill | SUPPORTED |
| gradient fill | SUPPORTED_OOXML |
| gradient line | SUPPORTED_OOXML |
| transparency | SUPPORTED_OOXML |
| outer shadow | SUPPORTED_OOXML |
| glow | SUPPORTED_OOXML |
| soft edge | NOT_SUPPORTED |
| glass blur | NOT_SUPPORTED |

`tech_gradient` 是当前唯一启用渐变的主题；6 套主题默认都未启用 glow。PowerPoint 原生打开测试在没有桌面 Office 的环境中标记为 `NOT_VERIFIED`，不伪造 PASS。

## Skill 包布局

独立仓库时技能位于仓库根目录（根目录或 `skills/<name>/` 都是被识别的安装位置）；在本合集仓库中位于 `skills/architecture-drawing/`。

```text
architecture-drawing/
├── SKILL.md                 # 核心执行规则
├── README.md                # 使用说明
├── CHANGELOG.md             # 变更记录
├── LICENSE                  # MIT
├── requirements.txt         # python-pptx
├── metadata.json            # 技能元信息
├── examples/                # 示例与样例模型
├── scripts/                 # canonical CLI、prepare_source、薄封装
├── resources/               # 配置、主题、提示词、能力矩阵与审计
├── src/                     # 内部可复用 Python 实现层
└── tests/                   # 自动化测试与评估配置
```

资源路径统一使用 `resources/` 前缀：

- 配置/领域 profile：`resources/config.yaml`、`resources/profiles/`
- 主题：`resources/themes/`
- 提示词：`resources/prompts/`
- 复用审计：`resources/REUSE_AUDIT.md`
- OOXML 能力矩阵：`resources/STYLE_CAPABILITIES.md`

对外推荐入口为 `scripts/main.py` 与 `scripts/prepare_source.py`；`src/` 保留为内部实现包，旧版 `scripts/architecture_pipeline.py` 继续转发。详细阶段变更见 `CHANGELOG.md`。

# 基于 Agent 的文档到可编辑 PowerPoint 架构图技能

技能包位置：仓库根目录或 `skills/architecture-drawing/`（历史名称为 `architecture-drawing-skill/`）。

本技能不是 DOCX 解析器，也不是基于关键词的抽取器。唯一输出是**原生可编辑的 PowerPoint 架构图**。执行契约见 [`SKILL.md`](SKILL.md)，本文件说明实际可运行的用法、产物和已验证行为。

## 安装

技能目录页：<https://skills.sh/weqi-pan/architecture-drawing>

```powershell
# 通过 skills CLI 安装（推荐）
npx skills add weqi-pan/architecture-drawing

# 只列出仓库里有哪些技能，不安装
npx skills add weqi-pan/architecture-drawing --list

# 也可以直接克隆使用
git clone https://github.com/weqi-pan/architecture-drawing.git
python -m pip install -r test/requirements.txt
```

默认装到当前项目的 `<agent>/skills/`；加 `-g` 装到用户级（跨项目可用），加 `-a <agent>` 指定目标 agent。安装后技能名为 `architecture-drawing`。

> 安装量统计生效后（skills.sh 需要至少一次安装遥测才会渲染徽章），可在本节顶部加安装量徽章：
> `[![skills.sh](https://skills.sh/b/weqi-pan/architecture-drawing)](https://skills.sh/weqi-pan/architecture-drawing)`

## 实际作用

```text
用户文档（docx / md / txt，可含参考风格图）
  -> scripts/prepare_source.py：规范化文本 + 源定位（供 Agent 读取）
  -> Agent：理解项目、抽取语义、产出 ArchitectureModel JSON
  -> scripts/main.py：契约校验 -> 简化/类型记录 -> 主题风格 -> 确定性布局
  -> <图名>.pptx（原生可编辑形状、文本、连接线）
```

职责边界：

- Agent/runtime 负责读文档、理解项目、抽取语义。代码不读文档内容、不做语义推断。
- Python 只做契约校验、归一化、确定性布局、布局校验、PPTX 序列化。
- 不使用整页 PNG/SVG 或截图代替架构图；不依赖 Microsoft Office、COM、VBA。
- 不保留 Draw.io 链路（4.0.0 起已删除），也不输出 PNG。

## 运行环境与依赖

- Python >= 3.10（实测 3.12.10），`prepare_source.py` 仅用标准库。
- `python-pptx`：生成 pptx；它自身依赖 lxml。缺失时 `pptx` 状态为 `SKIPPED`，不生成文件，也不会退化成图片或其它格式。
- 不需要 Pillow（无 PNG 输出）、不需要 Office 或桌面 PowerPoint。

```powershell
python -m pip install python-pptx
```

## 快速开始

两步：先把文档变成 Agent 可读内容，再由 Agent 产出模型并出图。

```powershell
# 1) 文档 -> 规范化文本 + 带定位的 blocks
python scripts/prepare_source.py "报告.docx" -o prepared

# 2) 拿到 Agent 产出的 ArchitectureModel JSON 后出图
python scripts/main.py agent-model.json -o artifacts/out --view "系统架构图" --style government_blue
```

`scripts/main.py` 参数：

| 参数 | 说明 |
|---|---|
| `input` | Agent ArchitectureModel JSON（唯一接受的输入类型） |
| `-o/--output-dir` | 输出目录，默认 `artifacts` |
| `--view` | 图名，例如 `系统架构图`；决定 pptx 文件名与图内标题，缺省时用模型标题 |
| `--style` | 主题，缺省 `enterprise_tech`；支持中文别名 |
| `--detail-level` | `overview` / `standard`（默认）/ `detailed` |

退出码：`0` = 布局校验通过；`2` = 校验不通过、输入被拒绝或证据不足。`prepare_source.py` 另有 `3` = 不支持的格式、`4` = 超过输入上限。

## 端到端实例：文档 → 系统架构图

以仓库自带的示例文档 `examples/input/architecture-notes.md` 为例，三步走：

```powershell
# 1) 文档 -> 可读文本 + 带定位的 blocks
python scripts/prepare_source.py examples/input/architecture-notes.md -o artifacts/example/prepared

# 2) Agent 阅读文本，按 SKILL.md 的 SOP 抽取语义模型，写出 agent-model.json
#    示例规模：24 个节点、16 条关系，逐条带 source_evidence
#    服务对象层 4 + 业务应用层 8 + 平台支撑层 4 + 数据资源层 4 + 基础保障层 4

# 3) 出图
python scripts/main.py artifacts/example/agent-model.json -o artifacts/example --view "系统架构图" --style government_blue
```

结果：`artifacts/example/系统架构图.pptx`，`validation.valid=true`、`pptx=PASS`。OOXML 检查：56 个可编辑形状（含 5 条层带、5 个层名、24 个节点、16 个关系标签等）、16 条连接线全部带箭头、`invalid_numeric_attributes=[]`、`valid=true`；16 条关系全部上下同列对齐、0 条绕行。

从真实项目（整份调研类报告，约 33 个 block / 2.5 万字）的端到端运行中得到的经验：

- **把 `layer` 写对是版式好坏的关键**：同一 `layer` 的节点才会进同一条层带，`level` 决定层带上下顺序（L1 最上）。
- **把 `priority` 标对**：primary 会更大更重，secondary 更轻，`status: planned` 会变虚线 —— 这是让图有主次的主要手段。
- **关系的方向决定节点行位**：出线朝下的节点会被排到本层最后一行，朝上的排到第一行，这样连线不会横穿本层其它节点。
- **关系要表达真实层间流向**（应用调用平台、平台汇聚数据），不要为了迁就画法把关系改成"只连相邻节点"，那会扭曲业务语义。
- 单页上限约 **5 个层带 / 24 个节点**；超了先拆图（多次运行、不同 `--view`），不要硬塞。要 6 个层带时把每带节点数控制在 4 以内。
- 节点标题控制在 14 个汉字以内、`subtitle` 控制在 18 个汉字以内，避免 259×74 的卡片内文字换行溢出。

## 输入契约

`scripts/main.py` 只接受 `.json`：Agent 产出的 ArchitectureModel。

```json
{
  "title": "项目总体架构",
  "architecture_type": "LAYERED",
  "nodes": [{"id": "platform", "title": "核心平台", "type": "platform", "layer": "platform", "level": "L1", "priority": "primary"}],
  "relations": [{"id": "platform-serves-app", "source": "platform", "target": "application", "relation_type": "supports", "label": "支撑"}]
}
```

- 也接受以 `architecture_model` 键包裹的同一对象，以及仓库既有的递归 `elements` / `relations` 载荷。
- 节点/关系 ID 必须唯一，关系端点必须存在；建议为核心节点和关系保留 `source_evidence`。
- 传入 `.docx` / `.pdf` / `.txt` / `.md` 等非 JSON 会返回 `DOCUMENT_READ_BLOCKED` 并提示先用 `prepare_source.py`。不再有"纯文本静默降级"路径。
- 模型没有 Agent 契约、且节点全部是 `unclassified_evidence` 时返回 `ARCHITECTURE_EXTRACTION_INSUFFICIENT_EVIDENCE`，**不出图**。

## 文档转文本（prepare_source.py）

```powershell
python scripts/prepare_source.py "报告.docx" -o prepared --title "项目总体架构"
```

产物：

| 文件 | 说明 |
|---|---|
| `prepared/<stem>.md` | 规范化 Markdown（标题层级、段落、管道表格） |
| `prepared/<stem>.source.json` | `document_title`、`source_file`、`source_format`、`blocks`、`diagnostics` |

`blocks[]` 每项含 `kind`（`heading` / `paragraph` / `table` / `asset`）、`level`、`text`、`locator`（`p12`、`t1`、`L34`），便于 Agent 填写 `source_evidence`。

覆盖范围：DOCX 段落、标题层级（`Heading1` / `标题 1` 等样式）、表格、图片占位标记（`ASSET_NOT_READ`，不做 OCR）；Markdown 标题与段落；TXT 逐行段落。PDF、PPT、扫描件、图片等返回 `UNSUPPORTED`（退出码 3），需先走仓库已有的 OCR / MinerU 能力，不伪造正文。

**输入上限（源文件视为不可信输入）**：DOCX 是 ZIP，压缩炸弹和超大部件是真实风险，因此解析按上限读取而不是相信声明值。

| 限制 | 值 | 行为 |
|---|---|---|
| 单篇正文部件 `word/document.xml` | 48 MiB | 超过报 `LIMIT_EXCEEDED`（退出码 4） |
| DOCX 部件数量 | 5000 | 超过报 `LIMIT_EXCEEDED` |
| 提取的 block 数量 | 20000 | 截断并写入 `BLOCK_LIMIT_REACHED` 诊断 |
| 单个 block 字符数 | 200000 | 截断 |

`.md` / `.txt` 同样受 48 MiB 上限约束。读取采用"带上限读取"而非先看压缩包头声明的大小，因此伪造头部也无法撑爆内存。

## 输出产物

| 文件 | 说明 |
|---|---|
| `<图名>.pptx` | 唯一交付物：原生可编辑形状、文本、连接线 |
| `document_structure.json` | 适配后的结构化输入 |
| `architecture_model.json` | 归一化后的 ArchitectureModel（唯一语义事实来源） |
| `architecture_candidates.json` | 候选节点清单，供人工复核 |
| `architecture_analysis.md` | 语义来源、Agent 状态、图名、架构类型、节点/关系数量、风格、诊断 |
| `style_spec.json` | 生效主题（含色彩、header/node/connector、效果开关）与渲染器能力矩阵 |
| `architecture_layout.json` | 画布、元素坐标、连接线锚点、`architecture_type` |
| `validation_report.md` | 布局校验结果；输入被拒绝时同样生成 |

被拒绝或证据不足时不生成 `architecture_layout.json` 和 pptx，只在 `architecture_analysis.md` / `validation_report.md` 记录原因。

## 主题

主题是纯数据文件 `resources/themes/*.json`，含 `colors`、`background`、`font`、`node_corner_radius`、`header`、`node`、`connector`、`band`、`effect_level`。新增主题只需新增一个 JSON 文件，不需要改代码。

| 主题 ID | 名称 | 说明 |
|---|---|---|
| `government_blue` | 政务蓝 | 政务汇报常用蓝底白字标题条 |
| `scientific_blue` | 科研蓝 | 偏冷的科研课题配色 |
| `enterprise_tech` | 企业科技 | 默认主题，深蓝灰 + 亮蓝强调 |
| `academic_minimal` | 论文简约 | 黑白灰，细描边、小圆角 |
| `industrial_engineering` | 工业工程 | 冷灰 + 橙色强调 |
| `tech_gradient` | 科技渐变风 | 唯一使用 OOXML 渐变的主题（标题条 3-stop 渐变、节点渐变、软阴影） |

中文别名可用：`政务蓝`、`科研蓝`、`企业科技`、`论文简约`、`工业工程`、`科技渐变风`；无法识别时回退 `enterprise_tech`。主题只影响配色与效果，不改版式。

## 布局、校验与 OOXML 能力

布局是**层带式（layered band）确定性布局**，不是表格网格：

- 节点按 `layer`（缺省用 `domain`）分带，带按 `level` 从上到下排序（L1 在最上）。
- 每个层带是一条横向色带，左侧有层名和强调色条，节点在带内按列排列；单带超过 4 个节点自动折行。
- 带内节点顺序由**流向 + 重心**决定：出线朝下的节点排到该带最后一行，出线朝上的排到第一行；再按连接的相邻层节点列号（重心）排序，使上下相邻层的节点尽量同列对齐，实现"直上直下"的连线。
- 排序用 down/up 两次 sweep 各算一遍，取列对齐数最多的一版（默认两端 `sweep`，确定性，无随机）。
- 连线是正交折线：同列对齐时为一条竖直线，否则在层间空白走 Z 形；末端带原生三角箭头指向目标。
- 关系标签放在该连线最长一段的中点上，使用与背景同色的文本框"断开"连线，并且有碰撞消解：先左右微调，再上下微调，保证不压节点、不压其它标签。

节点视觉权重随 `priority` / `status` 变化，避免"一片同色卡片墙"：

| 节点 | 填充 | 描边 | 字号 |
|---|---|---|---|
| `priority: primary` | 主题节点色 | 主题主色，加粗 1.35× | 14pt 加粗 |
| `priority: secondary` | 节点色与白色混合 45% | 主题线条色，0.85× | 12.5pt 常规 |
| `status: planned` / `suggested` | 节点色与背景混合 55% | 主题强调色，虚线 | 12.5pt 常规 |

尺寸与容量（当前尺寸方案）：画布 1280×720、外边距 24、层名条 100 宽、节点高 74、行距 16、列距 20、带间距 16，最多 4 列。单页可容纳 **5 个层带 / 24 个节点**（业务应用层那种 8 节点层会占 2 行）；节点再多时布局会自动压缩节点高度（74→66→58→52），仍放不下则画布变高并给出 `single-slide bounds` 警告。

`architecture_type` 由类型选择器计算并写入模型与布局，但版式当前只按层带渲染，不随类型切换。

OOXML 效果层（`src/renderers/ppt_ooxml.py`）：渐变填充、渐变线条、透明度、外阴影、发光、箭头。失败时回退到可编辑的 solid fill / solid line，不使用栅格回退。

| 能力 | 状态 | 触发方式 |
|---|---|---|
| solid fill | SUPPORTED | python-pptx 基础填充 |
| gradient fill | SUPPORTED_OOXML | 主题 `header.fill` / `node.fill` 为 `type: gradient` |
| gradient line | SUPPORTED_OOXML | 主题 `connector.line` |
| transparency | SUPPORTED_OOXML | stop `opacity` |
| outer shadow | SUPPORTED_OOXML | `shadow.enabled: true` |
| glow | SUPPORTED_OOXML | `glow.enabled: true`（6 套主题默认均关闭） |
| 箭头 | SUPPORTED | 每段连线末段自动加 `a:tailEnd` |
| soft edge / glass blur | NOT_SUPPORTED | 风格规划器不输出 |

参考风格（参考图分析结果）只能通过 Python API 传入：

```python
from src.pipeline.run import run
run("agent-model.json", "artifacts/out", style_reference={"colors": {"primary": "#1F5A94"}}, view="系统架构图")
```

## 验证与测试

```powershell
python -m compileall -q src scripts tests
python -m unittest discover -s tests -q
python scripts/main.py examples/model/government-overall.sample.json -o artifacts/eval --view "系统架构图" --style tech_gradient
python scripts/validate_ooxml_effects.py "artifacts/eval/系统架构图.pptx"
```

实测（2026-09-15，Python 3.12.10 + python-pptx 1.0.2）：

- 31 个 unittest 全部通过。
- 6 套主题逐一跑通样例模型：全部 `valid=true`、`pptx=PASS`，输出均为 `系统架构图.pptx`，无 PNG。
- 真实项目端到端（整份调研类报告 DOCX → 24 节点 / 16 关系的 `系统架构图.pptx`）：5 条层带按 L1–L5 从上到下排列，16 条关系全部完成列对齐（0 条绕行），56 个可编辑形状、16 条带箭头连接线、`invalid_numeric_attributes=[]`、`valid=true`。
- 标签落位检查：16 个关系标签全部放置成功，与节点矩形、其它标签的矩形重叠数均为 0。
- 版面契合检查：最大右边 13.333in / 13.333in，最大下边 7.167in / 7.5in，无裁切。
- `government_blue` OOXML 检查：纯 solid（gradient/shadow/alpha 计数为 0）。
- `tech_gradient` OOXML 检查：`gradient_fill_count=9`、`outer_shadow_count=9`、`alpha_count=25`。
- `prepare_source.py`：含标题、段落、图片、表格的 DOCX 输出 4 个 blocks 并记录 `ASSET_NOT_READ`；超大正文部件、超多部件、超多 block 三种越界场景分别命中上限检查。
- 没有桌面 Office 的环境下，PowerPoint 原生打开验证保持 `NOT_VERIFIED`，不伪造 PASS。

回归说明与通过条件见 `tests/test_cases.md`、`tests/eval.yaml`。

## 已知限制

- 单页 16:9，一页一张图；一次运行一个 pptx。多张图请多次运行（每次一个 `--view`）。
- 单页容量约 **5 个层带 / 24 个节点**（4 列，8 节点的层占 2 行）；放不下时先压缩节点高度，仍放不下则画布变高并给出 `single-slide bounds` 警告，节点会被裁出幻灯片。另有节点上限 40、关系上限 60（`src/architecture/simplifier.py`）。
- 层带顺序只由 `level` 决定；缺 `level` 的节点落到最后一带。同一 `level` 多个 `layer` 时按名称排序。
- 版式不随 `architecture_type` 变化，也没有为 `HUB_SPOKE` / `DOMAIN_MATRIX` 设计专门布局。
- 连线对齐是启发式的：层内节点多于 4 个时部分关系仍可能在层间空白走 Z 形，不做交叉最小化和连线避让。
- 关系标签固定 132×24px，过长会单行溢出；标签只在有空位时放置，极端拥挤时可能不放置。
- `overview` 只保留 L1 或 primary 节点。
- PDF / 扫描件 / 图片没有内置解析，`prepare_source.py` 直接报 `UNSUPPORTED`。
- 参考风格无 CLI 参数。
- 解析上限见上文"输入上限"：单篇正文 48 MiB、20000 个 block；超限直接报错或截断，不做流式处理。

## 复用组件

- 与渲染器无关、支持证据的 `ArchitectureModel` 节点和关系模型
- 简化器和架构类型选择器
- 确定性布局规划器和布局校验器
- 直接生成可编辑 PPTX 的 `python-pptx` 渲染器与 OOXML 效果层
- 主题数据文件与参考风格契约
- 文档规范化脚本（DOCX / Markdown / TXT）

## Skill 包布局

技能目录可以被放在仓库根目录（推荐，用于发布）或合集仓库的 `skills/<name>/` 下——两处都是被 `skills` CLI 识别的安装位置。

```text
architecture-drawing/
├── SKILL.md                 # 核心执行说明
├── README.md                # 本文件
├── CHANGELOG.md             # 变更记录
├── LICENSE                  # MIT
├── requirements.txt         # python-pptx
├── metadata.json            # 技能元信息（名称/版本/入口/能力/依赖）
├── examples/
│   ├── example1.md          # Agent 模型 -> 可编辑 PPTX
│   ├── input/architecture-notes.md   # 示例源文档
│   └── model/government-overall.sample.json
├── scripts/
│   ├── main.py              # canonical CLI
│   ├── prepare_source.py    # docx/md/txt -> 文本 + 定位
│   ├── validate_ooxml_effects.py
│   ├── utils.py
│   └── *.py                 # 转发到 src/ 的薄封装
├── resources/
│   ├── prompt.md
│   ├── config.yaml
│   ├── profiles/generic.md
│   ├── prompts/agent_semantic_parsing.md
│   ├── themes/*.json        # 6 套主题
│   ├── STYLE_CAPABILITIES.md
│   └── REUSE_AUDIT.md
├── src/                     # 内部可复用 Python 实现层
└── tests/                   # 自动化测试、测试说明和评估配置
```

`scripts/` 下小体积脚本（`architecture_*.py`、`document_to_architecture.py`、`ppt_writer.py`、`style_planner.py`）均为转发到 `src/` 的薄封装；`main.py`、`prepare_source.py`、`validate_ooxml_effects.py`、`utils.py` 是真实入口/工具。旧入口 `scripts/architecture_pipeline.py` 仍转发到 `main.py`。

## 版本演进

阶段变更记录见 [`CHANGELOG.md`](CHANGELOG.md)。能力边界审计见 [`resources/REUSE_AUDIT.md`](resources/REUSE_AUDIT.md)，OOXML 能力矩阵见 [`resources/STYLE_CAPABILITIES.md`](resources/STYLE_CAPABILITIES.md)。

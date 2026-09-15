# architecture-drawing 变更日志

> 本日志按可确认的演进阶段整理，从最初的 Draw.io skill 开始记录。`0.x`–`4.x` 是阶段版本号，不代表发布的 Git 标签。

## [4.2.0] - 2026-09-15 — 发布整理：输入上限加固、双语描述、公开仓库发布

面向"作为独立技能仓库公开发布"的整理版本。发布仓库：`weqi-pan/test`（技能名 `architecture-drawing`），目录页 `https://skills.sh/weqi-pan/test`。

### 新增

- `LICENSE`（MIT）、`requirements.txt`（`python-pptx`），补齐独立仓库所需的元数据文件。
- `.gitignore` 增加 `prepared/`、虚拟环境和编辑器噪声。
- README 增加"安装"章节：`npx skills add weqi-pan/test`、`--list` 用法、skills.sh 徽章，以及克隆后手动安装的方式。
- README 增加"输入上限"表格与端到端示例（改为使用仓库自带示例文档，不再依赖本地客户文件）。

### 变更

- **`SKILL.md` 描述改为中英双语并补齐触发词**（「生成系统架构图」「画架构图」「architecture diagram」「editable pptx」等），便于 `skills find` 检索与非中文环境发现。
- 文档脱敏：移除 README/CHANGELOG 中的客户报告名称、内部分支名与本地目录路径，保留全部技术结论与实测数据。
- 技能包布局说明改为"仓库根目录或 `skills/<name>/`"两种被 CLI 识别的形态。

### 安全加固（`scripts/prepare_source.py`）

源文档按不可信输入处理。此前 DOCX 解析直接 `read("word/document.xml")` 且无任何上限，压缩炸弹或伪造大小的部件可以撑爆内存。

- 新增**带上限读取**：DOCX 正文部件上限 48 MiB，超限报 `LIMIT_EXCEEDED`（退出码 4）。上限针对实际读取字节数而非压缩包头声明值，伪造头部无效。
- 新增部件数量上限（5000）与 block 数量上限（20000，超限截断并写 `BLOCK_LIMIT_REACHED` 诊断）。
- 单个 block 字符数上限 200000；`.md` / `.txt` 同样受 48 MiB 上限约束。
- 新增 `SourceLimitExceeded` 异常类型，CLI 单独返回退出码 4，与"格式不支持"（3）区分。
- 新增 4 个回归测试：超大正文部件、超多部件、block 上限诊断、缺少正文部件。

### 已验证（2026-09-15，Python 3.12.10 + python-pptx 1.0.2）

- `python -m compileall -q src scripts tests` 通过；`python -m unittest discover -s tests -q` 31 个测试通过（此前 27 个）。
- `npx -y skills@latest add <技能目录> --list` → `Local path validated` / `Found 1 skill`，正确读出名称与双语描述。
- 6 套主题逐一跑通样例模型：全部 `valid=true`、`pptx=PASS`，无 PNG。

## [4.1.0] - 2026-09-15 — 版式重写为层带式，连线带箭头并有视觉主次

首版对真实报告（整份调研类报告 DOCX）出图后反馈"很丑、结构不对"。排查确认根因不是模型，而是布局器只是 20 行的取模网格：24 个节点被铺成同质卡片墙，没有层带、没有层名、没有箭头、`priority`/`status` 完全不参与渲染。本版重写布局与渲染。

### 新增

- **层带式布局**（`src/layout/planner.py` 重写）：节点按 `layer`（缺省 `domain`）分带，带按 `level` 排序；每条带是横向色带，左侧有层名与强调色条；带内最多 4 列、超出折行。
- **流向排序**：按连线相对节点的出线方向（上/下）决定节点落在带内第一行还是最后一行，避免连线横穿本层。
- **重心列对齐**：按相邻层连接对象的列号重心排序，使上下层同列对齐；down/up 两次 sweep 各算一遍，取"列对齐关系数"最多的一版（确定性，无随机）。
- **正交布线与箭头**：同列为一条竖直线，跨列在层间空白走 Z 形；每段最后一段加原生 `a:tailEnd` 三角箭头。
- **标签碰撞消解**：标签锚定在线段中点、用背景色文本框断开连线，并按左右→上下顺序微调，直到不压节点、不压其它标签；无空位则不放置（`_place_labels`）。
- **视觉主次**：`priority: primary` 更大更重、深色描边；`secondary` 更轻；`status: planned`/`suggested` 用虚线 + 强调色描边。
- **带配色**：6 套主题新增 `band` 段（`fill` / `border` / `label_color`）。
- **校验加强**：`validate_layout` 新增层带越界、层名条越界、元素必须落在所属层带内的检查；`inspect_pptx_ooxml` 新增 `invalid_numeric_attributes`。
- 新增测试：层带顺序、元素归属层带、多行带容量、溢出告警、关系箭头、层名原生文本、主次/状态视觉差异、标签落位（共 27 个测试，此前 22 个）。

### 修复

- **浮点 EMU 缺陷（真实文件级 bug）**：ELBOW 分支把 `left + width/2` 的浮点值直接当 EMU 写入，slide XML 出现 `x="1724025.0"`，python-pptx 回读即抛 `ValueError`。改为整数 EMU，并由 `invalid_numeric_attributes` 检查兜底。
- **关系标签压住节点**：旧实现把标签画在源节点中心。现改为线段中点 + 碰撞消解。
- **标题条与首行过近**：内容区从 64px 开始（标题条 38px + 26px 留白），此前仅剩 2px。
- 修正流向判定的错误端：旧代码只把 `down` 打在一个端点且打错一侧，导致 4 条关系走 500px+ 的长绕行；修正后 16/16 关系列对齐、0 条绕行。

### 已验证（2026-09-15，Python 3.12.10 + python-pptx 1.0.2）

- `compileall` 通过；`python -m unittest discover -s tests -q` 27 个测试通过。
- 真实报告重新出图：5 条层带（服务对象层 L1 → 业务应用层 L2 → 平台支撑层 L3 → 数据资源层 L4 → 基础保障层 L5），24 节点 / 16 关系。
- `architecture_layout.json`：画布 1280×720，16 条关系全部 2 点直线（0 条绕行），16 条关系全部与目标同列。
- PPTX：56 个可编辑形状、16 条连接线、16 个箭头、`invalid_numeric_attributes=[]`、`duplicate_fill_errors=[]`、`valid=true`；最大右边 13.333in/13.333in、最大下边 7.167in/7.5in，无裁切。
- 标签落位：16 个标签全部放置，与节点矩形重叠 0 处、标签之间重叠 0 处。

### 已知限制

- 版式不随 `architecture_type` 变化，尚未为 `HUB_SPOKE` / `DOMAIN_MATRIX` 设计专门布局。
- 单页容量约 5 带 / 24 节点；超容量时先压缩节点高度，再溢出并给 `single-slide bounds` 警告（此时应拆图）。
- 连线对齐是启发式；层内节点多于 4 个时部分关系仍可能走 Z 形，不做交叉最小化。
- 关系标签固定 132×24px，过长会溢出；极端拥挤时可能不放置。

## [4.0.1] - 2026-09-15 — 真实报告端到端验证与渲染缺陷修复

用一份真实的调研类报告 DOCX 做首次端到端运行（DOCX → 文本与定位 → Agent 语义模型 → 系统架构图.pptx），暴露出三个此前测试没覆盖的缺陷，本版修复。

### 修复

- `src/renderers/ppt_writer.py`：ELBOW 连接线分支把 `left + width / 2` 这类浮点值直接当作 EMU 传入 `add_connector`，导致 slide XML 出现 `x="1724025.0"` 之类的非整数属性（python-pptx 回读即抛 `ValueError`，严格的 OOXML 消费者可能直接拒绝文件）。改为整数 EMU。
- `src/renderers/ppt_writer.py`：关系标签原先画在**源节点中心**，会盖住节点标题。改为画在连接线中点、向右偏移 0.06in，落在两行之间的空隙里。24 节点 / 16 关系场景下复核：标签与节点矩形零重叠。
- `src/renderers/ppt_ooxml.py`：`inspect_pptx_ooxml()` 增加 `invalid_numeric_attributes` 检查，把上述浮点属性问题变成可检测的失败项，而不是留到打开文件时才发现。
- `src/layout/validator.py`：增加单页边界检查，画布超过 1280×720 时写入 `single-slide bounds` 警告（此前会静默生成被裁切的幻灯片）。
- `tests/test_ooxml_effects.py`、`tests/test_architecture_migration.py`：新增 4 个回归测试（整数 EMU 几何、标签落位、网格容量不告警、网格溢出告警），共 22 个测试。

### 已验证（2026-09-15，Python 3.12.10 + python-pptx 1.0.2）

- `python -m unittest discover -s tests -q`：22 个测试通过；`compileall` 通过。
- 真实报告：`prepare_source.py` 从 DOCX 提取 33 个 block（locator `p1`..`p33`，该报告未使用标题样式，全部为 paragraph）；Agent 抽取 24 节点 / 16 关系的五层系统架构（服务对象层 4、业务应用层 8、平台支撑层 4、数据资源层 4、基础保障层 4）。
- 生成的 `系统架构图.pptx`：`validation.valid=true`、`pptx=PASS`；OOXML 检查 41 个可编辑形状（24 节点 + 标题条 + 16 关系标签）、16 条连接线、`duplicate_fill_errors=[]`、`invalid_numeric_attributes=[]`、`valid=true`；所有形状落在 13.333in × 7.5in 幻灯片内（最大右边 13.333in、最大下边 6.5in）。
- 标签与节点矩形重叠检查：0 处重叠。

### 记录为已知限制（未改代码）

- 单页网格容量为 24 个节点（4 列 × 6 行），超出后会被裁切，只能靠拆图。
- 关系连线不做避让：跨行跨列的关系是直线穿越，会压到中间节点；实务上应让关系连相邻行的同列节点。
- 版式仍不随 `architecture_type` 变化。

## [4.0.0] - 2026-09-15 — 收敛为单一 pptx 输出，移除 Draw.io 与 PNG 预览

### 破坏性变更

- **移除 Draw.io 链路**：删除 `drawio_repair.py`、`validate_drawio.py`、`layout_planner.py`、`normalize_spec.py`、`extract_evidence_draft.py`、`spec_from_evidence.py`、`validate_evidence.py`、`validate_layout_plan.py`、`validate_semantic_coverage.py`、`draw_architecture.md`、`evidence_to_diagram_spec.md`、`extract_architecture_evidence.md`、`normalize_input.md`、`plan_layout.md`、`prompts/templates/*`、`resources/schema/*`、`examples/drawio|spec|layout|evidence`、`examples/example2.md`。`src/` 与 PPTX 路径原本就不引用 Draw.io，因此删除不影响主流程。
- **移除 PNG 预览**：删除 `src/renderers/preview.py` 和 `scripts/preview_renderer.py`；不再需要 Pillow，产物只有 pptx。
- **CLI 只接受 Agent 模型 JSON**：`.txt` / `.md` 及其它后缀不再静默降级为 `unclassified_evidence` 节点，而是返回 `DOCUMENT_READ_BLOCKED` 并提示先用 `scripts/prepare_source.py`。
- **无 Agent 语义不出图**：模型没有 Agent 契约且节点全部是 `unclassified_evidence` 时，返回 `ARCHITECTURE_EXTRACTION_INSUFFICIENT_EVIDENCE`，退出码 2，不生成 pptx（此前会照常出图）。
- 不再生成 `generated_ppt_prompt.md` 占位产物。

### 新增

- `scripts/prepare_source.py`：把 `.docx` / `.md` / `.txt` 规范化为 Agent 可读的 UTF-8 文本与带定位的 blocks（`.docx` 支持标题层级、段落、表格、图片占位标记；PDF 等二进制明确报 `UNSUPPORTED`，不做 OCR 猜测）。输出 `<stem>.md` 与 `<stem>.source.json`。
- `--view` 参数：用户要什么图就出什么图，例如 `--view 系统架构图` 决定输出文件名 `系统架构图.pptx` 与图内标题；缺省时用 Agent 给的标题。
- 主题独立成数据文件 `resources/themes/*.json`（6 套：`government_blue`、`scientific_blue`、`enterprise_tech`、`academic_minimal`、`industrial_engineering`、`tech_gradient`），补齐 `font`、`background`、`node_corner_radius`、`text_primary` / `text_secondary`，并可用 `src.style.planner.available_themes()` 枚举。
- `tests/test_prepare_source.py`：覆盖 docx 标题/表格/图片标记、md/txt 归一化、不支持格式与缺文件。

### 变更

- `src/style/planner.py`：预设从硬编码改为读取 `resources/themes/*.json`，保留参考风格契约分支与中文别名。
- `src/pipeline/run.py`：只出 pptx，返回 `pptx_path`；把读取阶段诊断并入模型诊断；pptx 文件名由图名/标题生成并做 Windows 文件名净化。
- 测试从 23 个收敛为 18 个（删除只覆盖 legacy 链路的 10 个，新增 3 个 prepare_source 与 2 个管线行为用例）。

### 已验证（2026-09-15，Python 3.12.10 + python-pptx 1.0.2）

- `python -m compileall -q src scripts tests` 通过；`python -m unittest discover -s tests -q` 18 个测试通过。
- 6 套主题逐一执行 `python scripts/main.py examples/model/government-overall.sample.json -o <out> --style <主题> --view 系统架构图`：全部 `valid=true`、`pptx=PASS`，输出均为 `系统架构图.pptx`，无 PNG。
- OOXML 检查：`government_blue` 为纯 solid（gradient/shadow/alpha 计数均为 0，可编辑形状 11、连接线 2，`valid=true`）；`tech_gradient` 为 `gradient_fill_count=9`、`outer_shadow_count=9`、`alpha_count=25`，`valid=true`。
- `scripts/prepare_source.py` 在含标题、段落、图片、表格的 DOCX 上输出 4 个 blocks 并记录 `ASSET_NOT_READ` 诊断。

### 已知问题

- `SKILL.md` 的包布局树仍使用旧目录名 `architecture-drawing-skill/`。
- 布局仍是固定 4 列网格，`architecture_type` 只记录不改变版式；`validate_layout` 不检查连接线穿越节点。
- 参考风格只能通过 `src.pipeline.run.run(..., style_reference=...)` 传入，CLI 无对应参数。

## [3.2.0] - 2026-09-15 — 技能包迁入 skills/ 并按实测行为校准文档

### 变更

- 技能包由仓库根目录 `architecture-drawing-skill/` 迁移到 `skills/architecture-drawing/`；84 个受版本控制的文件内容逐字节一致，仅目录位置变化。
- `README.md` 依据实际运行行为重写：补充定位与职责边界、运行环境与依赖、快速开始、输入契约（含纯文本降级与不可读输入）、输出产物与退出码、布局与校验的真实覆盖范围、风格别名与 OOXML 触发方式、验证命令与实测结果、已知限制、更新后的包布局。
- 更正包路径引用：README 中的目录树由 `architecture-drawing-skill/` 改为 `skills/architecture-drawing/`。
- `resources/prompt.md` 的资源索引把失效的 `docs/` 更正为 `resources/`。

### 新增

- `.gitignore` 增加 `artifacts/`，避免把流水线输出目录提交进版本控制。

### 已验证（2026-09-15，Python 3.12.10 + python-pptx 1.0.2 + Pillow + lxml）

- `python -m unittest discover -s tests -q`：23 个测试通过。
- 样例流水线：`validation.valid=true`、`pptx=PASS`、`preview=PASS`。
- `python scripts/validate_ooxml_effects.py`：`pptx_package_valid=true`、`slide_xml_valid=true`、`gradient_fill_count=9`、`outer_shadow_count=9`、`alpha_count=25`、`editable_shape_count=11`、`editable_connector_count=2`、`valid=true`。
- `.mmd` 等不可读输入返回 `DOCUMENT_READ_BLOCKED`，退出码 2；`.txt` 输入走 `structured_fallback`（该行为已在 4.0.0 移除）。

## [3.1.0] - 2026-09-11 — Skill 包布局标准化

### 新增

- 增加 `metadata.json`，记录技能名称、版本、入口、能力和依赖边界。
- 增加 `resources/prompt.md`、`resources/config.yaml` 作为统一资源入口和运行配置。
- 增加 `examples/example1.md`，覆盖 Agent 模型到可编辑 PPTX 的默认路径。
- 增加 `examples/example2.md`，覆盖 Legacy Draw.io 校验与修复路径。
- 增加 `tests/test_cases.md` 和 `tests/eval.yaml`，记录回归用例、手工检查和评估门槛。
- 增加 `scripts/main.py` 作为 canonical CLI 入口，增加 `scripts/utils.py` 通用路径/JSON 工具。

### 变更

- 将提示词、领域配置、JSON Schema、风格模板和设计文档统一收拢到 `resources/`。
- 保留 `src/` 作为内部 Python 实现层，保留原有 `scripts/*.py` 兼容入口。
- `scripts/architecture_pipeline.py` 改为转发到 `scripts/main.py`，旧命令仍可使用。
- `tech_gradient.json` 的读取路径改为 `resources/templates/styles/tech_gradient.json`（4.0.0 起改为 `resources/themes/tech_gradient.json`）。

## [2.0.0] — Phase 3：OOXML 高级视觉效果层

### 新增

- 新增集中式 `src/renderers/ppt_ooxml.py`。
- 支持原生 `a:gradFill`、渐变线条、透明度、`a:outerShdw` 和 `a:glow`。
- 新增 `tech_gradient` 风格及中文/英文别名。
- 新增 OOXML 能力矩阵、PPTX 结构检查脚本和独立 smoke test。
- Preview Renderer 支持渐变可视化；阴影和 Glow 由 PPTX 原生效果层保留（Preview 已在 4.0.0 移除）。

### 兼容性

- 不依赖 Microsoft Office、COM、VBA 或 PowerPoint.exe。
- 不使用整页 PNG/SVG 作为高级效果回退。
- 现有 Agent-first 语义流水线、ArchitectureModel、确定性布局和 Draw.io legacy 路径不变（Draw.io 已在 4.0.0 移除）。

## [1.1.0] — Agent-first 流水线质量增强

### 新增

- 增加文档读取阻塞、语义证据不足、参考风格不可用等诊断状态。
- 增加长文档、快速路径、迁移兼容和语义覆盖测试。
- 保留原始输入、模型、布局、风格和验证产物，方便追溯。

### 变更

- 明确 Python 代码不承担复杂 DOCX/PDF NLP 解析；文档理解由 Agent/runtime 或已有 parser 完成。
- 将 Draw.io 从默认输出路径降级为 legacy 兼容路径。

## [1.0.0] — 从 Draw.io 迁移到 Agent-first ArchitectureModel

### 新增

- 新增 `ArchitectureModel`，统一节点、关系、层级、证据和诊断。
- 新增输入适配、模型分析后处理、简化器和架构类型选择器。
- 新增与渲染器无关的确定性布局、碰撞检查和连接线规划。
- 新增基于 `python-pptx` 的原生可编辑 PPTX Renderer 和 PNG 预览（PNG 已在 4.0.0 移除）。

### 迁移原则

- Agent 先理解文档并生成语义模型；代码只负责确定性处理和序列化。
- 不再把关键词抽取或 Python 启发式分析器当作主语义引擎。
- Draw.io XML、`mxCell`、旧 schema 和旧校验工具继续保留以支持已有项目（4.0.0 起不再保留）。

## [0.2.0] — Evidence / Spec / Layout 质量链路

### 新增

- 增加架构证据抽取草稿、证据校验和语义覆盖检查。
- 增加 `diagram_spec`、`layout_intent`、`layout_plan` 结构化契约。
- 增加输入归一化、规格生成、布局规划、Draw.io 修复和严格校验。
- 增加政府蓝、通用系统等 Draw.io 示例和测试夹具。

## [0.1.0] — 初始 Draw.io skill

### 新增

- 以 Draw.io XML 为默认架构图输出格式。
- 建立中文架构图绘制提示词、输入归一化规则和模板提示词。
- 建立 `mxCell`、节点、分组、边、标签和布局计划的基础约定。
- 提供 Draw.io XML 校验与确定性修复脚本。
- 提供基础示例、schema 和命令行脚本。

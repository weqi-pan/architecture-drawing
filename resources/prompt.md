# 资源入口与使用约定

本目录集中保存 `architecture-drawing` 的非执行资源。技能入口是根目录的 `SKILL.md`；可执行入口是 `scripts/main.py`，文档预处理入口是 `scripts/prepare_source.py`。

## 资源索引

- `prompt.md`：资源索引与运行原则。
- `config.yaml`：目录、输入类型、默认主题、输出和能力开关。
- `themes/*.json`：6 套主题数据（颜色、header、node、connector、效果开关）。
- `prompts/agent_semantic_parsing.md`：Agent 语义解析 SOP。
- `profiles/generic.md`：通用领域分类与命名规则。
- `STYLE_CAPABILITIES.md`：渲染器能力矩阵。
- `REUSE_AUDIT.md`：能力边界与复用审计。

## 运行原则

1. 先用 `scripts/prepare_source.py` 把 docx/md/txt 转成规范化文本与带定位的 blocks。
2. Agent 阅读文本后产出 `ArchitectureModel` JSON；这是 `scripts/main.py` 唯一接受的输入。
3. Python 代码只做契约归一化、确定性布局、校验和序列化，不做语义推断。
4. 输出只有原生可编辑 pptx；不生成 PNG，不生成 Draw.io。
5. 只有 `unclassified_evidence` 节点时不出图，报 `ARCHITECTURE_EXTRACTION_INSUFFICIENT_EVIDENCE`。
6. 不能读取原始文档时必须报告 `DOCUMENT_READ_BLOCKED`，不得伪造架构节点。

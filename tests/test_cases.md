# 测试用例说明

## 核心回归

- Agent 模型归一化、简化和架构类型选择。
- 确定性布局、边界和重叠校验。
- 直接生成并重新打开可编辑 PPTX。
- 以 `--view` 指定的图名决定 pptx 文件名与图内标题。
- 没有 Agent 语义（全部为 `unclassified_evidence`）时不出图。
- 非 JSON 输入（docx/txt）被拒绝并提示 `prepare_source.py`。
- DOCX / Markdown / TXT 规范化：标题层级、段落、表格、图片占位标记、源定位。
- 不支持的格式返回 `UNSUPPORTED`，缺文件返回错误，不伪造正文。
- OOXML 渐变、透明度、阴影、Glow 和渐变线条结构。
- 非法高级效果配置回退到已有 solid fill，不损坏 PPTX。

## 手工检查

1. 运行 `python scripts/prepare_source.py <报告.docx> -o prepared`，检查 `prepared/*.md` 的标题层级和表格，以及 `*.source.json` 的 `blocks[].locator`。
2. 用 `scripts/main.py ... --view "系统架构图"` 生成 pptx，确认文件名与图内标题一致、目录内没有 PNG。
3. 逐一试用 6 套主题，确认配色变化而版式一致。
4. 用 `scripts/validate_ooxml_effects.py` 检查 PPTX 包完整性和 XML 结构。
5. 在有 Microsoft PowerPoint 的环境中再进行 GUI 打开验证；没有该环境时保持 `NOT_VERIFIED`，不要伪造结果。

自动化 Python 测试位于本目录的 `test_*.py` 文件；评估入口和通过条件见 `eval.yaml`。

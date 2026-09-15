# 渲染器风格能力矩阵

主题数据文件位于 `resources/themes/*.json`，由 `src/style/planner.py` 读取。

| 能力 | 状态 | 实现方式 |
|---|---|---|
| solid_fill | SUPPORTED | python-pptx |
| gradient_fill | SUPPORTED_OOXML | `a:gradFill`，主题 `header.fill` / `node.fill` 为 `type: gradient` |
| gradient_line | SUPPORTED_OOXML | `a:ln/a:gradFill`，主题 `connector.line`，兼容性优先 |
| transparency | SUPPORTED_OOXML | `a:alpha`，stop `opacity` |
| outer_shadow | SUPPORTED_OOXML | `a:effectLst/a:outerShdw` |
| glow | SUPPORTED_OOXML | `a:effectLst/a:glow`，6 套主题默认关闭 |
| soft_edge | NOT_SUPPORTED | Style Planner 不输出 |
| glass_blur | NOT_NATIVE / NOT_SUPPORTED | 不使用栅格回退 |

主题清单：`government_blue`、`scientific_blue`、`enterprise_tech`（默认）、`academic_minimal`、`industrial_engineering`、`tech_gradient`。其中只有 `tech_gradient` 使用渐变填充；其余主题为 solid fill，实测 gradient/shadow/alpha 计数均为 0。

PPTX 生成仅依赖 `python-pptx` 和 Office Open XML，不依赖 Microsoft Office、COM、VBA 或桌面自动化，也不输出 PNG 预览。

# V16 PRD — 聚合 Prompt 自定义

> 从主 PRD.md 切面的版本副本。

## Problem Statement

聚合节点生成质量取决于 prompt 指令。当前四种聚合 prompt（全量/全量追加/追加/节点分析追加）全部硬编码在 `aggregation/prompts.py` 中，用户无法根据素材特点调整聚合策略。聚合任务复用了"文档分析"的模型配置（`task_models.text`），无法独立选择更适合聚合的模型。

## Solution

将 4 种聚合 prompt 迁入 `prompts.yaml`，与已有的 vision/text/search_ai 等统一管理。新增 `task_models.aggregation` 独立模型绑定，不再复用 text。设置面板 AI 提示词 Tab 按三组展示：分析 / 聚合 / 搜索。

## Key Features

- 新增 4 个 prompt 类型 + 独立模型绑定 + 设置面板三组布局 + 占位符说明
- 详见主 PRD.md v16 章节

## User Stories

1. 自定义聚合策略适配素材库
2. 聚合单独配置模型
3. 知道可用的占位符变量
4. 修改 prompt 后立即生效
5. 设置面板分组更清晰

## Out of Scope

- 不修改 _asset_text() 格式化逻辑
- 不修改聚合 Worker 调度
- 预设模板初始为空
- 不修改 MCP 聚合工具

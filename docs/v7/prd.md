# QuickMedia v7 PRD — MiniMax 支持 + 设置弹窗重构

## Problem Statement

1. 当前设置面板为侧边栏内嵌，占据常驻空间，展开时压缩素材区域。交互分散（Ollama 配置在底部、AI Prompt 在分隔线下方），不够聚焦
2. 缺少 MiniMax 原厂模型支持，用户无法使用国产大模型做分析

## Solution

### MiniMax 支持

在 models.yaml 新增 minimax provider，6 个模型，走现有 OpenAI 适配器，无需代码改动。

### 设置弹窗重构

将设置面板改为模态弹窗，三个 Tab 切换：
- **基础配置** — 视频采样帧数 + 请求超时
- **模型管理** — 完全复用现有 ModelManager
- **AI 提示词** — 完全复用现有 Prompt 编辑区

保存按钮初始浅色，有修改后激活。Provider 删除加确认弹窗。

## Testing Seam

| 层次 | seam |
|------|------|
| API | 无新增端点 |
| 数据 | `quickmedia/models.yaml` 新增 minimax 条目 |
| 前端 | 设置弹窗组件（替...[truncated]
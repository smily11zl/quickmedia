# QuickMedia v6 PRD — 多模型配置

## Problem Statement

当前 AI 分析硬编码使用本地 Ollama 单一模型。用户可能想用更好的远端模型（如 GPT-4o 做图片分析、Claude 做文档分析），或完全切换 provider（DeepSeek / OpenRouter）。缺乏灵活配置机制，扩展新模型需改代码。

## Solution

将 AI 模型配置从硬编码改为可配置的多 provider 架构。按协议适配不同服务商（OpenAI 兼容 / Ollama 原生），不同分析任务可独立选择 provider + model。API Key 分离到 .env 安全存储。

## Key Features

- **Provider 注册** — 支持 Ollama / OpenAI 兼容（OpenAI / DeepSeek / OpenRouter）两类协议适配器
- **任务模型绑定** — 每种分析类型独立配置 provider + model
- **模型能力目录** — `models.yaml` 出厂定义支持模型及 capabilities，首次启动复制到用户目录，升级自动合并
- **API Key 安全** — Key 存 `~/.asset-manager/.env`，config.yaml 可安全分享
- **自动迁移** — 检测旧 `ai.*` 配置自动生成 providers + task_models
- **Web UI** — 独立模型管理页面，provider 管理 + 任务绑定 + 连接测试
- **连接测试** — 支持测试单个 provider 是否可用

## User Stories

1. As a 用户，I want 图片分析用 GPT-4o，文档分析用本地方案，so that 远端高质量 + 本地快速兼顾。
2. As a 用户，I want 一键添加 DeepSeek provider，so that 无需写代码即可切换模型。
3. As a 用户，I want API Key 不暴露在 config 文件中，so that 分享配置或截图时不会泄露。
4. As a 用户，I want 升级后自动保留现有 Ollama 配置，so that 不需要手动迁移。

## Implementation Decisions

- **协议适配**：按协议写适配器，不按公司。一套 OpenAI 兼容适配器覆盖 3 个 provider
- **配置粒度**：按分析任务绑定模型（vision/text/speech/video_summary），非全局
- **迁移策略**：检测旧 `ai.ollama_url` 字段，自动写入 providers.ollama + task_models
- **模型目录**：项目目录 `quickmedia/models.yaml`，首次启动复制到用户目录

## Testing Decisions

- 最高 seam：GET/PUT /api/providers + POST /api/providers/test
- 模块 seam：ProviderRegistry + OpenAIAdapter + AIWorker 多模型路由
- 前端 seam：ModelManager 独立页面
- 迁移测试：旧配置 → 新结构自动转换

## Tasks

详见 [tasks.md](tasks.md)。

## Implementation Notes

- Ollama 所有硬编码已归入 provider 系统，settings panel 去掉了单独的 Ollama URL/模型/检测连接
- Provider 添加/删除立即保存，任务配置手动保存
- AIWorker 每个任务重新读磁盘配置，修改任务绑定无需重启
- API Key 存 .env，URL 存 config.yaml
- 日志格式：`[provider] model=xxx` → `[provider prompt]` → `[provider] response`
- 模型下拉自定义组件，两行显示（模型名深色 / 能力浅色）
- 任务配置页每个任务类型下有提示说明
- models.yaml 支持 openrouter/deepseek/openai/ollama 四类，26 个模型

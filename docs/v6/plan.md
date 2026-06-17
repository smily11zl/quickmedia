# QuickMedia v6 — 多模型配置

> 需求访谈记录。grill-me 时间：2026-06-16。

## 设计决策

### 1. 配置粒度：按分析类型分

每种分析任务（vision / text / speech / video_summary）可独立指定 provider + model。

### 2. Provider 按协议分类，不按公司

```
OpenAI 兼容适配器 → OpenAI / DeepSeek / OpenRouter（共用 /v1/chat/completions）
Ollama 适配器     → 本地模型（/api/chat + image base64）
Anthropic 适配器   → 未来（/v1/messages）
```

同一协议一个适配器，换 base_url + api_key 就能切 provider。

### 3. 模型能力目录：quickmedia/models.yaml

- 随项目发布，定义每个 provider 支持的模型及 capabilities
- 首次启动自动复制到 `~/.asset-manager/models.yaml`
- 升级时合并新增模型，保留用户添加的
- capabilities 标注：vision / text / speech

### 4. 配置拆分

| 文件 | 内容 | 权限 |
|------|------|------|
| config.yaml | provider URL + 模型列表 + task_models 绑定 | 可分享 |
| .env | API Key | 私密，不可分享 |

### 5. Task Model Binding 结构

```yaml
providers:
  ollama:
    url: http://localhost:11434
  openrouter:
    url: https://openrouter.ai/api/v1
  deepseek:
    url: https://api.deepseek.com/v1

task_models:
  vision: {provider: ollama, model: qwen3.5:9b}
  text: {provider: ollama, model: qwen3.5:9b}
  speech: {provider: ollama, model: qwen3.5:9b}
  video_summary: {provider: ollama, model: qwen3.5:9b}
```

### 6. 首次升级自动迁移

检测到旧 `ai.ollama_url` + `ai.model` 字段 → 自动生成 providers.ollama + task_models → 写入 config.yaml。不保留旧字段。

### 7. Web UI 入口

设置面板 → "模型管理"按钮 → 独立配置页面，包含：
- Provider 列表（添加/删除/测试连接）
- 每个分析任务的下拉选 provider + model
- model 下拉按 capabilities 过滤

### 8. API Key 管理

`.env` 文件格式：
```
OPENROUTER_API_KEY=***
DEEPSEEK_API_KEY=***
```
一个 provider 一个 key，不按模型分。

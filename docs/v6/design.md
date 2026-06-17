# QuickMedia v6 技术方案

## 新增文件

| 文件 | 说明 |
|------|------|
| `quickmedia/providers.py` | ProviderRegistry — provider 注册、模型查找、任务绑定 |
| `quickmedia/openai_adapter.py` | OpenAI 兼容协议适配器，支持 `test()` 和 `chat()` |
| `quickmedia/models.yaml` | 出厂模型目录，5 个 provider × 26 个模型 |
| `quickmedia/ai.py` (OllamaAdapter) | Ollama 原生协议适配器，封装 `/api/chat` |
| `frontend/src/ModelManager.tsx` | 模型管理独立页面 |

## 修改文件

| 文件 | 变更 |
|------|------|
| `quickmedia/config.py` | DEFAULT_CONFIG 扩展 providers + task_models；`_migrate_if_needed` 旧配置迁移；`_ensure_models_yaml` 首次复制和升级合并 |
| `quickmedia/ai.py` | VisionAnalyzer/TextAnalyzer 接受 adapter 参数；OllamaAdapter 类；删除重复的 `_call_ollama` |
| `quickmedia/ai_worker.py` | AIWorker 按 task_models 动态创建 adapter；每次任务重读配置和 .env |
| `quickmedia/api/server.py` | GET/PUT /api/providers、模型查询、连接测试；/api/config 读写 provider 字段 |
| `quickmedia/cli.py` | 启动检测走 provider 系统 |
| `frontend/src/App.tsx` | 设置面板精简（去 Ollama URL/模型/检测连接），加模型管理入口 |
| `tests/` | test_v6_config.py(4) + test_v6_providers.py(5) + test_v6_api.py(5) |

## 架构

```
用户 UI（ModelManager）
  ├── Provider 管理 Tab → 选择内置 provider + 填 Key → 立即保存
  └── 任务配置 Tab → 四任务选 provider+model → 点保存提交

AIWorker._get_adapter(task_type)
  ├── 重读 config + .env（热更新）
  ├── 查 task_models → provider + model
  ├── ollama → OllamaAdapter
  └── 其他 → OpenAIAdapter(provider_name)

Prompt 日志：[provider] model=xxx → [provider prompt] ... → [provider] response
```

## 数据流

```
config.yaml                    .env
  providers.ollama.url          DEEPSEEK_API_KEY=***
  providers.openrouter.url      OPENROUTER_API_KEY=***
  providers.deepseek.url
  task_models.vision.{provider,model}
  task_models.text.{provider,model}
```

## models.yaml 结构

```yaml
ollama:
  url: http://localhost:11434/v1
  models:
    - name: qwen3.5:9b
      capabilities: [vision, text, speech]

openrouter:
  url: https://openrouter.ai/api/v1
  models:
    - name: openai/gpt-4o
      capabilities: [vision, text]
    ...
```

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/providers | 返回 providers + task_models（含 .env 中的 Key） |
| GET | /api/providers/{name}/models | 返回 `[{name, capabilities}]` |
| PUT | /api/providers | 保存 providers 到 config.yaml，Key 到 .env |
| POST | /api/providers/test | 测试 provider 连接 |
| GET | /api/config | 返回 ollama_url/model（兼容）+ providers/task_models |
| PUT | /api/config | 写 providers.ollama.url + task_models.*.model（兼容） |

## 模型目录

| Provider | 模型数 | 典型模型 |
|----------|--------|---------|
| ollama | 1 | qwen3.5:9b |
| openrouter | 12 | openai/gpt-4o, anthropic/claude-sonnet-4, deepseek/*, qwen/* |
| deepseek | 4 | deepseek-chat, deepseek-v4-pro, deepseek-v4-flash, deepseek-reasoner |
| openai | 2 | gpt-4o, gpt-4o-mini |

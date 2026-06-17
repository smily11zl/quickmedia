# QuickMedia v6 任务拆分

> 按垂直切片拆分，每个切片端到端可独立验证。

## Slice 6.1 — Config + 数据层

**目标：** 建立 provider 配置结构，模型目录文件，自动迁移旧配置。

**后端：**
- [ ] `DEFAULT_CONFIG` 扩展 `providers` + `task_models` 字段
- [ ] `Config._load()` 检测旧 `ai.ollama_url`，自动迁移到新结构
- [ ] 创建 `quickmedia/models.yaml`（出厂模型目录：ollama + openai_compatible）
- [ ] `Config` 首次启动复制 `models.yaml` 到 `~/.asset-manager/models.yaml`
- [ ] `models.yaml` 升级合并逻辑（新增模型追加，用户添加的保留）

**测试：**
- [ ] `test_config_migration` — 旧配置 → 新结构自动转换
- [ ] `test_models_yaml_copy` — 首次启动复制模型目录
- [ ] `test_models_yaml_merge` — 升级时合并新模型

**验证：** 启动 `quickmedia serve`，检查 `~/.asset-manager/config.yaml` 包含 providers + task_models，`models.yaml` 存在。

---

## Slice 6.2 — Provider 架构 + 适配器

**目标：** Provider 注册管理和协议适配器，AIWorker 按任务路由模型。

**后端：**
- [ ] `quickmedia/providers.py` — `ProviderRegistry` 类
  - `__init__(config, models_path)` 加载配置和模型目录
  - `get_provider(name)` 返回 provider 配置
  - `get_models(name, capability)` 按能力过滤模型列表
  - `get_task_binding(task_type)` 返回任务绑定的 provider+model
- [ ] `quickmedia/openai_adapter.py` — `OpenAIAdapter` 类
  - `chat(prompt, images=None)` 调用 `/v1/chat/completions`
  - `test()` 测试连接
- [ ] `AIWorker.__init__` 改为根据 `task_models` 创建分析器
  - `_get_adapter(task_type)` 根据任务类型查 provider + model
  - 图片分析传 images 参数
- [ ] `VisionAnalyzer` / `TextAnalyzer` 改为接受 adapter 参数（而非硬编码 ollama_url）
- [ ] `POST /api/providers/test` 端点

**测试：**
- [ ] `test_provider_registry` — 加载配置，查询 provider 和模型
- [ ] `test_openai_adapter_test` — 模拟连接测试
- [ ] `test_worker_routes_to_correct_adapter` — AIWorker 按任务选择适配器

**验证：** 配置一个远端 provider，手动调用 `analyze` 看是否能成功调用。

---

## Slice 6.3 — API 端点

**目标：** 前端可通过 API 读写 provider 配置。

**后端：**
- [ ] `GET /api/providers` — 返回 providers + task_models
- [ ] `PUT /api/providers` — 保存 providers + task_models，写入 config.yaml + env
- [ ] `POST /api/providers/test` — 测试单个 provider 连接（调用 adapter.test()）

**测试：**
- [ ] `test_get_providers` — 返回完整配置结构
- [ ] `test_put_providers` — 保存配置并持久化
- [ ] `test_test_connection_success` — Ollama 本地测试成功
- [ ] `test_test_connection_failure` — 无效 URL 返回错误

**验证：** `curl GET /api/providers` 查看配置，`curl PUT` 修改后 `curl GET` 确认。

---

## Slice 6.4 — 前端模型管理页面

**目标：** Web UI 独立模型管理页面。

**前端：**
- [ ] `App.tsx` — 设置面板底部加"模型管理"按钮入口
- [ ] `ModelManager.tsx` — 独立页面
  - Provider 列表（名称 + URL，添加/删除按钮）
  - 每个 provider 行有"测试连接"按钮
  - 四个分析任务的下拉选择器（provider + model 联动）
  - model 下拉按 capabilities 过滤
  - 保存按钮（PUT /api/providers）
  - 沿用 DESIGN.md 设计 token
- [ ] Autocomplete 集成，type 筛选

**验证：** 浏览器打开设置 → 模型管理，添加/删除 provider，切换任务模型绑定，保存后刷新确认。

---

## 完成统计

| 切片 | 预估 | 状态 |
|------|------|------|
| 6.1 Config + 数据层 | AFK | ✅ |
| 6.2 Provider 架构 + 适配器 | AFK | ✅ |
| 6.3 API 端点 | AFK | ✅ |
| 6.4 前端模型管理页面 | HITL | ✅ |

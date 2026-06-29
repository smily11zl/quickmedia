# V16 任务列表

> 5 个垂直切片，聚合 Prompt 全部迁入 prompts.yaml。

---

## ✅ s1: [后端] DEFAULT_PROMPTS 加 4 个聚合条目 + PUT validator 扩展

**类型**: 后端 | **依赖**: 无 | **用户可测**: ❌

### What to build

在 prompt_config.py 和 api/server.py 中加入 4 个聚合 prompt 的配置结构。

- `DEFAULT_PROMPTS` 新增 `aggregation_full`、`aggregation_full_append`、`aggregation_append`、`aggregation_analyze_append` 四个条目
- 每个条目结构：system_format（JSON 格式约束） + default（从现有 aggregation/prompts.py 粘贴完整指令） + custom 空 + presets 空
- system_format:
  - aggregation_full: `{"nodes": [{"name":..., "description":..., "asset_ids":[...]}, ...]}`
  - aggregation_full_append: `{"nodes": [...], "assignments": {"已有节点ID": [...]}}`
  - aggregation_append: `{"assignments": {"node_id": [...]}}`
  - aggregation_analyze_append: `{"asset_ids": [...]}`
- default 模板包含占位符：`{assets}` 素材列表、`{nodes}` 已有节点
- aggregation_analyze_append 额外占位符：`{node_name}`、`{node_description}`、`{existing_assets}`、`{candidates}`
- `PUT /api/prompts` validator 扩展 `analysis_type not in (...)` 加 4 个聚合 type
- `PromptConfig._load()` 自动合并（已有逻辑，无需修改）

### Acceptance criteria

- [ ] `DEFAULT_PROMPTS` 包含 4 个 aggregation_* 条目
- [ ] 每个条目有 system_format / default / custom / presets
- [ ] PUT /api/prompts type=aggregation_full 返回 200
- [ ] GET /api/prompts 返回包含 4 个新条目
- [ ] 现有 6 种 prompt 类型不受影响

---

## ✅ s2: [后端] DEFAULT_CONFIG 加 aggregation task_model

**类型**: 后端 | **依赖**: 无 | **用户可测**: ❌

### What to build

在 config.py 中加入 aggregation 任务模型绑定。

- `DEFAULT_CONFIG.task_models` 新增 `"aggregation": {"provider": "", "model": ""}`
- `_fill_missing_task_models()` 自动填充到用户 config.yaml（已有逻辑）
- `GET /api/task-models` 返回包含 aggregation 字段
- `ModelManager.tsx` 的 `TASK_LABELS` 和 `TASK_HINTS` 新增 `aggregation: "聚合分析"`

### Acceptance criteria

- [ ] `DEFAULT_CONFIG.task_models["aggregation"]` 存在
- [ ] `_fill_missing_task_models()` 填充到用户配置
- [ ] GET /api/task-models 包含 aggregation
- [ ] 现有 task_models 不受影响

---

## ✅ s3: [后端] aggregation/prompts.py 改为 PromptConfig 读取模板

**类型**: 后端 | **依赖**: s1 | **用户可测**: ❌

### What to build

聚合 prompt 构建函数改为从 PromptConfig 读取模板，替换占位符。

- `_build_full()`: 从 `PromptConfig.get_prompt("aggregation_full")` 读取，替换 `{assets}` → 素材文本列表
- `_build_full_append()`: 同读 `get_prompt("aggregation_full_append")`，替换 `{nodes}` → 节点文本列表，`{assets}` → 素材文本
- `_build_append()`: 同读 `get_prompt("aggregation_append")`，替换 `{nodes}` → 节点文本，`{assets}` → 素材文本
- `build_append_prompt()`: 同读 `get_prompt("aggregation_analyze_append")`，替换 `{node_name}`、`{node_description}`、`{existing_assets}`、`{candidates}`
- `_asset_text()` 保持不变（素材格式化逻辑不进模板）
- 移除硬编码的 prompt 文本（parts 列表）

### Acceptance criteria

- [ ] `build_prompt("full", assets)` 使用 PromptConfig 模板
- [ ] `build_prompt("full_append", assets, nodes)` 使用 PromptConfig 模板
- [ ] `build_prompt("append", assets, nodes)` 使用 PromptConfig 模板
- [ ] `build_append_prompt(node_info, existing, candidates)` 使用 PromptConfig 模板
- [ ] 聚合结果与迁移前一致（相同模型 + 相同 prompt 文本）
- [ ] 现有聚合测试通过

---

## ✅ s4: [后端] aggregation/core.py 改为 task_models.aggregation

**类型**: 后端 | **依赖**: s2 | **用户可测**: ❌

### What to build

聚合分析改用独立的 aggregation 模型绑定。

- `aggregation/core.py` 的 `_get_adapter()` 从 `registry.get_task_binding("text")` 改为 `registry.get_task_binding("aggregation")`
- 未配置 aggregation binding 时聚合任务执行失败（不再 fallback）
- `analyze_append_node` 的 MCP 调用同样改用 aggregation binding

### Acceptance criteria

- [ ] 聚合使用 task_models.aggregation 而非 task_models.text
- [ ] 未配置 aggregation 时聚合返回错误
- [ ] 已配置 aggregation 时聚合正常执行
- [ ] 文档分析（text）不受影响

---

## ✅ s5: [前端] SettingsModal 三组布局 + 占位符说明 + ModelManager

**类型**: 前端 | **依赖**: s1 | **用户可测**: ✅ 看三组按钮 + 编辑聚合 prompt

### What to build

设置面板 AI 提示词 Tab 改为三组布局，聚合 prompt 可编辑。

- SettingsModal prompts Tab 按钮分三组，每组加标题：
  - **分析**: vision(图片), text(文档), speech(语音), video_vision(视频视觉), video_summary(视频综合)
  - **聚合**: aggregation_full(全量聚合), aggregation_full_append(全量追加), aggregation_append(追加分析), aggregation_analyze_append(节点追加)
  - **搜索**: search_ai(搜索)
- 每个编辑区 textarea 下方显示可用占位符说明（灰色小字 `text-[9px]`）
- 占位符映射硬编码：
  - aggregation_full / aggregation_full_append / aggregation_append: "{assets} 素材列表, {nodes} 已有节点"
  - aggregation_analyze_append: "{node_name} 节点名, {node_description} 节点描述, {existing_assets} 已有素材摘要, {candidates} 候选素材"
- `pt` state 类型扩展为包含 4 个聚合 type
- 现有保存/恢复逻辑不变

### Acceptance criteria

- [ ] AI 提示词 Tab 显示三组标题（分析 / 聚合 / 搜索）
- [ ] 每组按钮可点击切换
- [ ] 编辑区下方显示对应占位符说明
- [ ] aggregation_full 的 custom 可保存 + 恢复默认
- [ ] 其他分析 prompt 编辑不受影响

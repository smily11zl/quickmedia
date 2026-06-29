# V16 技术设计 — 聚合 Prompt 自定义

## Prompt 模板结构

### aggregation_full

```yaml
aggregation_full:
  system_format: |
    请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：
    {"nodes": [{"name": "...", "description": "...", "asset_ids": [1,2]}, ...]}
  default: |
    你是一个素材库整理专家。
    ...(96行完整指令，从 aggregation/prompts.py:_build_full 提取)...
    素材列表：
    {assets}
  custom: ""
  presets: []
```

### aggregation_full_append

```yaml
aggregation_full_append:
  system_format: |
    请严格按以下JSON格式输出：
    {"nodes": [{"name": "...", "description": "...", "asset_ids": [1,2]}], "assignments": {"已有节点ID": [素材ID,...]}}
  default: |
    你是一个素材分类专家。已有以下聚合节点...
    {nodes}
    ...
    {assets}
  custom: ""
  presets: []
```

### aggregation_append

```yaml
aggregation_append:
  system_format: |
    请严格按以下JSON格式输出：
    {"assignments": {"node_id": [asset_id, ...], ...}}
  default: |
    你是一个素材分类专家。已有以下聚合节点...
    {nodes}
    ...
    {assets}
  custom: ""
  presets: []
```

### aggregation_analyze_append

```yaml
aggregation_analyze_append:
  system_format: |
    请严格按以下JSON格式输出：
    {"asset_ids": [id1, id2, ...]}
    如果没有匹配素材，返回 {"asset_ids": []}
  default: |
    你是一个素材分类助手。有一个聚合节点...
    节点名称: {node_name}
    节点描述: {node_description}
    {existing_assets}
    {candidates}
  custom: ""
  presets: []
```

---

## 占位符映射

| 占位符 | 数据来源 | 适用 type |
|--------|---------|-----------|
| `{assets}` | `_asset_text()` 生成的素材文本列表 | full, full_append, append |
| `{nodes}` | 节点 id/name/description/素材数 文本 | full_append, append |
| `{node_name}` | 目标节点名称 | analyze_append |
| `{node_description}` | 目标节点描述 | analyze_append |
| `{existing_assets}` | 节点已有素材摘要（代码生成） | analyze_append |
| `{candidates}` | 候选素材列表（代码生成） | analyze_append |

---

## 数据流

```
用户触发聚合
  → aggregation/api.py
    → aggregation/core.py
      → _get_adapter("aggregation")  ← 改为 aggregation, 不再 text
      → aggregation/prompts.py:build_prompt(mode, assets, nodes)
        → PromptConfig.get_prompt("aggregation_full")  ← 新增
        → prompt.replace("{assets}", asset_text_list)   ← 替换占位符
        → 返回完整 prompt
    → adapter.chat(prompt)
    → 解析 JSON → 创建/更新 nodes + node_assets
```

---

## 文件变更

| 文件 | 变更 | 说明 |
|------|------|------|
| `quickmedia/prompt_config.py` | +~200 行 | DEFAULT_PROMPTS 加 4 个聚合条目 |
| `quickmedia/config.py` | +1 行 | DEFAULT_CONFIG.task_models 加 aggregation |
| `quickmedia/aggregation/prompts.py` | -~200 行 + ~30 行 | 4 个函数改为 PromptConfig 读取 |
| `quickmedia/aggregation/core.py` | 1 行 | get_task_binding("text") → "aggregation" |
| `quickmedia/api/server.py` | 1 行 | PUT /api/prompts validator 加 4 个 type |
| `frontend/src/SettingsModal.tsx` | ~30 行 | 三组布局 + 占位符说明 |
| `tests/test_v16.py` | ~50 行 | 新增测试 |

---

## 设置面板布局

```
┌─ AI 提示词 Tab ──────────────────────────┐
│ 分析                                      │
│ [图片] [文档] [语音] [视频视觉] [视频综合] │
│                                           │
│ 聚合                                      │
│ [全量聚合] [全量追加] [追加分析] [节点追加]│
│                                           │
│ 搜索                                      │
│ [搜索]                                    │
│                                           │
│ ┌─ textarea ─────────────────────────┐    │
│ │                                    │    │
│ └────────────────────────────────────┘    │
│ 可用变量：{assets} 素材列表, ...           │
│ [保存自定义] [恢复默认]                    │
└───────────────────────────────────────────┘
```

---

## 聚合模型变更

```
旧: task_models.text  →  aggregation + text 共用
新: task_models.aggregation  →  聚合独立绑定

未配 aggregation: 聚合执行失败
已配 aggregation: 正常使用
text 不受影响: 文档分析继续用 task_models.text
```

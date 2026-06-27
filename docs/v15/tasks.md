# V15 任务列表

> 10 个垂直切片，按依赖排序。

---

## ✅ s1: [后端] search_ai prompt + task_models 基础设施

**类型**: 后端 | **依赖**: 无 | **用户可测**: ❌  
**状态**: ✅ 完成

### What to build

在 prompt_config.py 和 config.py 中加入 search_ai 的基础配置结构，不涉及 API 调用。

- `DEFAULT_PROMPTS` 新增 `search_ai` 条目：system_format（要求输出 `{"asset_ids": [...]}`） + default（素材搜索助手角色+格式说明+严格筛选原则） + custom 空 + presets 空
- `DEFAULT_CONFIG.task_models` 新增 `search_ai` 空占位（provider/model 空），`_fill_missing_task_models()` 自动同步至用户配置
- PromptConfig 兼容：`_load()` 遍历 DEFAULT_PROMPTS keys 自动发现 search_ai
- 设置面板 prompts Tab 自动展示 search_ai 编辑项（复用现有 prompt 编辑逻辑）

### Acceptance criteria

- [ ] `DEFAULT_PROMPTS["search_ai"]` 包含 system_format/default/custom/presets
- [ ] `DEFAULT_CONFIG.task_models["search_ai"]` 存在
- [ ] `PromptConfig._load()` 自动合并 search_ai 到 prompts.yaml
- [ ] `_fill_missing_task_models()` 填充 search_ai 到用户 config.yaml
- [ ] 设置面板 prompts Tab 可选 search_ai 进行编辑
- [ ] 现有 4 种 prompt 类型不受影响

---

## ✅ s2: [前端] 搜索模式 UI 改名+重排

**类型**: 前端 | **依赖**: 无 | **用户可测**: ✅ 看模式名字和顺序  
**状态**: ✅ 完成

### What to build

纯前端改动：搜索模式选择器的 option 改名和顺序调整。不涉及 AI 搜索逻辑。

- smode select option 重排：AI → 语义（K聚合）→ 语义（纯向量）→ 关键词
- value 映射：`"ai"`、`"combined"`（历史兼容）、`"semantic"`、`"keyword"`
- option labels：综合→语义（K聚合），语义→语义（纯向量），匹配→关键词
- AI option 暂时无 disabled 逻辑（s4 做），先当普通 option 渲染
- 默认选中：暂不改为 AI（s4 做），保持 combined = 语义（K聚合）
- 选中 AI 时搜索按钮 click → toast "AI 搜索开发中"（临时，s4 替换）

### Acceptance criteria

- [ ] 模式选择器显示 4 个选项：AI、语义（K聚合）、语义（纯向量）、关键词
- [ ] 原有 value 兼容（combined/semantic/keyword 仍正常工作）
- [ ] 默认选中语义（K聚合）
- [ ] 选中 AI 点击搜索 → toast 提示"AI 搜索开发中"
- [ ] 其他 3 种模式搜索功能不受影响

---

## ✅ s3: [后端] /api/search?mode=ai 端点实现

**类型**: 后端 | **依赖**: s1 | **用户可测**: ❌

### What to build

在 search.py 中实现 AI 搜索逻辑，在 API server 中接入 mode=ai 分支。

- 新增 `search_ai_assets(query, db, cfg, data_dir)` 函数
  - 从 DB 查出全量素材：`SELECT id, filename, asset_type, visual_description, ai_summary FROM assets WHERE status='active'`
  - 查每个素材的 tags：`get_asset_tags()`
  - 构建 assets 文本：格式同聚合 prompt `_asset_text()` —— `[ID] filename (type)` + `描述: visual_description 或 ai_summary` + `标签: tag1, tag2`
  - 构建 prompt：`PromptConfig.get_prompt("search_ai")` + 替换 `{assets}` 和 `{query}` 占位符
  - 调 `AIWorker.get_adapter("search_ai")` 获取适配器，调 chat
  - 解析 `{"asset_ids": [...]}` JSON
  - 回查素材全量数据 → 返回 `[dict(r) for r in rows]`
- API server `GET /api/search?mode=ai&q=xxx` 分支：调 search_ai_assets()，返回 `{"items": [...], "counts": {...}}`
- 异常处理：LLM 调用失败/解析失败 → 返回空 items，打印日志
- 复用 `_count_by_type()` 生成类型计数

### Acceptance criteria

- [ ] `GET /api/search?mode=ai&q=猫` 返回 `{"items": [...], "counts": {...}}`
- [ ] items 结构与 keyword 搜索一致（id, filename, asset_type, size, tags 等）
- [ ] counts 按类型正确计数
- [ ] 空查询返回空 items
- [ ] LLM 调用失败返回空 items（不 throw 500）
- [ ] 搜索不依赖 ChromaDB

---

## ✅ s4: [前后端] AI 搜索集成

**类型**: 全栈 | **依赖**: s1,s2,s3 | **用户可测**: ✅ 配模型搜"猫"看结果  
**状态**: ✅ 完成

### What to build

前端 AI 搜索的完整交互：红点检测、默认选中回退、搜索触发、结果展示、错误处理。

后端：
- `GET /api/task-models` 返回包含 search_ai 字段（已有逻辑，只需确认 task_models 包含 search_ai）

前端：
- 挂载时调 `/api/task-models`，检查 `search_ai` 是否有效（provider + model 均非空）
- 有效时：`smode` 默认设为 `"ai"`，AI option 无红点
- 无效时：AI option 加 `disabled` + 红点（红色圆点 span），`smode` 默认 `"combined"`（语义 K聚合）
- 搜索调用：mode="ai" 时 `GET /api/search?q=xxx&mode=ai`
- 搜索中 `slc` 控制搜索按钮 spinner
- 结果替换主区域 searchResults，类型计数随结果更新
- 失败：toast "AI 搜索失败: {error}"，不改变已有搜索结果
- 搜索结果联动：类型筛选计数、格式/标签/日期筛选、视图切换、排序
- 云图联动：搜索结果传给 GraphView，自动高亮/过滤
- 去掉 s2 里的临时 toast "AI 搜索开发中"

### Acceptance criteria

- [ ] 已配 search_ai 模型时，页面打开默认选中 AI
- [ ] 未配 search_ai 模型时，AI 选项 disabled + 红点，默认选中语义（K聚合）
- [ ] 输入关键词点搜索 → spinner → 搜索结果出现
- [ ] 搜索失败 → toast 报错，结果不变
- [ ] 搜索结果类型计数正确
- [ ] 搜索结果支持类型/格式/标签/日期筛选
- [ ] 搜索结果支持视图切换和排序
- [ ] 云图联动搜索结果过滤
- [ ] 其他 3 种模式不受影响

---

## ✅ s5: [前端] 树节点展开/折叠基础

**类型**: 前端 | **依赖**: 无 | **用户可测**: ✅ 点箭头展开折叠  
**状态**: ✅ 完成

### What to build

NodePanel 节点渲染从平铺 div 改为 TreeItem 组件，实现基本展开/折叠交互。

- 新建 `TreeItem` 组件（在 NodePanel.tsx 或独立文件）
  - row：箭头（▶/▼）+ 节点名 + 素材数量 + 右键菜单按钮
  - 箭头独立点击 → toggle expand状态
  - 节点名点击 → `onSelectNode`（保持原有行为）
  - 箭头 hover → title 提示
- 展开状态：`expandedNodes` Set 管理（NodePanel 内部 state）
- 默认全部折叠（`new Set()`）
- 展开区域暂时显示占位文本 "加载中..."（灰色文字）
- 素材数量显示在箭头旁边同一行
- 右键菜单复用现有（重命名、编辑描述、删除、添加素材、移除素材、分析追加）

### Acceptance criteria

- [ ] 节点列表显示为树形，每个节点前有 ▶ 箭头
- [ ] 点击箭头 → ▶ 变 ▼，展开区出现"加载中..."
- [ ] 再次点击箭头 → ▼ 变 ▶，展开区收起
- [ ] 点击节点名 → 云图聚焦 + 主区域筛选（原有行为）
- [ ] 素材数量显示在箭头旁边
- [ ] 右键菜单功能正常
- [ ] 默认全部折叠

---

## ✅ s6: [前端] 树素材加载+点击详情

**类型**: 前端 | **依赖**: s5 | **用户可测**: ✅ 展开看列表，点素材看详情  
**状态**: ✅ 完成

### What to build

展开节点后加载真实素材数据并渲染素材列表。

- 展开状态变为 true 时，调 `GET /api/nodes/{id}`，取 `assets` 数组
- 渲染素材子列表：
  - 每项：类型图标（根据 asset_type）+ 文件名
  - 类型图标映射：图片🖼、视频🎬、音频🎵、文档📄（用文字标识，与现有风格一致）
  - 缩进样式：左边距比节点行多 16-20px
- 点击素材项 → 获取素材 ID，调 `onSelectAsset` → `selA(asset_id)` 打开右侧详情
- 折叠状态不做请求
- 加载中显示 spinner/占位文字，加载完成替换为素材列表
- 空列表显示 "暂无素材"

### Acceptance criteria

- [ ] 展开节点 → 看到素材列表（类型图标 + 文件名）
- [ ] 多个节点可同时展开，各自独立加载
- [ ] 点击素材项 → 右侧详情面板打开对应素材
- [ ] 折叠节点 → 素材列表隐藏
- [ ] 空节点显示"暂无素材"
- [ ] 再次展开无需重新加载（缓存机制可选）

---

## ✅ s7: [前端] 未分配虚拟节点展示

**类型**: 前端 | **依赖**: s6 | **用户可测**: ✅ 看到灰色节点在末尾，可展开看  
**状态**: ✅ 完成

### What to build

在树末尾增加未分配虚拟节点，展示未分配素材。

- TreeItem 列表末尾固定渲染"未分配"节点
- 数据源：`graphData.unassigned`（从 props 传入）
- 视觉区分：灰色文字（`color: S.ms`），虚线/虚线边框风格
- 箭头 + 节点名（"未分配"）+ 素材数量
- 展开后显示未分配素材列表：类型图标 + 文件名（复用 s6 的素材子列表渲染逻辑）
- 数据直接从 `graphData.unassigned` 取，不需要调 API
- 无右键菜单
- 数量联动云图（素材移入移出后数量同步变化——靠 s9 刷新机制）
- graphData 变化时未分配节点数量和列表自动更新

### Acceptance criteria

- [ ] 树末尾出现"未分配"节点，灰色/虚线风格
- [ ] 展开后显示未分配素材（类型图标+文件名）
- [ ] 点击素材 → 打开右侧详情
- [ ] 无右键菜单
- [ ] 素材数量随 graphData 变化实时更新
- [ ] 常规节点功能不受影响

---

## ✅ s8: [前端] 树拖放

**类型**: 前端 | **依赖**: s6,s7 | **用户可测**: ✅ 拖素材从A节点到B节点  
**状态**: ✅ 完成

### What to build

素材在树内、树→云图、网格→树之间的拖放操作。

- 树素材项加 `draggable`，dragstart 设 `dataTransfer`：
  ```json
  `{"asset_id": 1, "source_node_id": 3, "filename": "cat.png"}`
  ```
- 树节点 drop target：
  - dragover：`preventDefault` + 高亮样式
  - drop：POST /api/nodes/{target_id}/assets `{"asset_ids": [asset_id]}`，成功后刷新 source+target 展开节点
- 未分配节点 drop：
  - drop：DELETE /api/nodes/{source_node_id}/assets/{asset_id}（从 drag data 获取 source_node_id），成功后刷新 source 展开节点 + 未分配列表
  - 未分配内素材拖出到其他节点：POST /api/nodes/{target_id}/assets（正常分配）
- 云图 drop：复用现有 `onAssetDrop`
- 网格/列表素材：
  - 素材卡片加 `draggable`，dragstart 设 `dataTransfer`（source_node_id 为 null 或从上下文获取）
  - 网格素材可能是未分配的（source_node_id=null），拖到树节点 → POST 分配
- 拖放完成后：
  - 用 `nodeRefreshKey` 触发已展开节点的重新加载
  - 调用父组件 `onGraphRefresh` 刷新 graphData
- 拖放时显示视觉反馈（半透明跟随或高亮 drop zone）

### Acceptance criteria

- [ ] 从节点A展开列表拖素材到节点B → 节点B素材列表出现该素材
- [ ] 从未分配拖素材到已分配节点 → 分配成功
- [ ] 从已分配节点拖素材到未分配 → 取消分配成功
- [ ] 从网格拖素材到树节点 → 分配成功
- [ ] 从未分配节点拖素材到云图节点 → 分配成功
- [ ] 拖放后 source 和 target 展开节点列表刷新
- [ ] 拖放后 graphData.unassigned 更新
- [ ] 拖放中不出现 JS 错误

---

## ✅ s9: [前后端] 树联动刷新

**类型**: 全栈 | **依赖**: s6 | **用户可测**: ✅ 执行聚合看树自动刷新  
**状态**: ✅ 完成

### What to build

树列表在操作后的自动刷新联动。

- 聚合完成（/api/aggregation/run）：轮询检测 status=done → 重新取 `/api/nodes` + graphData + setNodeRefreshKey
- 节点分析追加完成：NodePanel 检测完成后 → setNodeRefreshKey
- 新建节点保存后：重新取 `/api/nodes` + setNodeRefreshKey + 自动展开新节点
- 删除节点后：重新取 `/api/nodes` + 清空 selectedNodeId + graphData
- 添加素材/移除素材弹窗确认后：setNodeRefreshKey
- nodeRefreshKey 变化时：
  - 遍历已展开节点（expandedNodes），调 `GET /api/nodes/{id}` 重新加载素材
  - collapsed 节点不请求
  - 保持展开状态不变
- graphData 刷新时未分配节点数量和列表同步更新

### Acceptance criteria

- [ ] 执行全量聚合 → 聚合完成后树节点列表刷新（节点可能增减，展开状态重置）
- [ ] 分析追加到节点 → 完成后该节点素材列表刷新（如果已展开）
- [ ] 新建节点保存 → 树列表出现新节点，自动展开
- [ ] 删除节点 → 树列表移除该节点，选中状态清除
- [ ] 添加/移除素材弹窗确认 → 对应节点素材列表刷新
- [ ] 折叠节点不发送请求
- [ ] 未分配节点数量联动更新

---

## ✅ s10: [后端] MCP search_assets 支持 ai 模式

**类型**: 后端 | **依赖**: s3 | **用户可测**: ❌

### What to build

让 MCP 工具 `search_assets` 支持 mode="ai"。

- `quickmedia/mcp_server.py` 的 `search_assets` 工具 mode 参数扩展为 `"keyword" | "semantic" | "combined" | "ai"`
- mode="ai" 时调用 `search_ai_assets()`（从 search.py 导入）
- 返回结构保持与 keyword 模式一致
- 错误处理：search_ai_assets 返回空时不 crash

### Acceptance criteria

- [ ] Hermes 中 `search_assets(query="猫", mode="ai")` 返回匹配素材列表
- [ ] mode="ai" 不依赖 ChromaDB
- [ ] 其他 mode 不受影响
- [ ] 无素材时报空列表不报错

---

## ✅ s11: [后端] 聚合 _asset_text() video_summary 修复

**类型**: 后端 | **依赖**: 无 | **用户可测**: ❌  
**状态**: ✅ 完成

### What to build

修复聚合 prompt 中素材描述字段优先级，视频应优先取 `video_summary`（综合理解）。

- `quickmedia/aggregation/prompts.py` 的 `_asset_text()` 描述字段改为：
  `video_summary → visual_description → ai_summary`
- AI 搜索 `search_ai_assets()` 中的 assets 文本构建使用相同的优先级
- 同时更新 `build_append_prompt()` 中 candidate 素材的描述字段

### Acceptance criteria

- [ ] `_asset_text()` 对视频素材优先使用 video_summary
- [ ] 有 video_summary 的视频不再用 visual_description
- [ ] 无声视频 video_summary = visual_description，行为不变
- [ ] 图片/文档行为不变（visual_description / ai_summary）
- [ ] search_ai_assets 构建的描述字段同此优先级

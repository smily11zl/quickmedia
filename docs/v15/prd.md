# V15 PRD — AI 搜索 + 节点树状列表

> 从主 PRD.md 切面的版本副本。主 PRD 保持全版本汇总累积。

## Problem Statement

搜索方面：现有三种搜索模式（综合/语义/关键词）都依赖 ChromaDB/jieba 等索引基础设施。用户用自然语言描述想要的素材（如"上次聚会时小明切蛋糕的视频"），无法通过现有搜索直接找到——需要 AI 理解用户意图后匹配素材。

节点管理方面：聚合节点侧边栏展示为扁平列表，用户只能看到节点名和素材数量。想浏览节点内素材必须点击节点名再等主区域刷新，操作割裂。同时缺少未分配素材的直观入口。

## Solution

**功能 1 — AI 搜索**：纯 LLM 单次调用。用户输入自然语言查询，全量素材（id + filename + type + tags）送入模型，模型直接返回匹配的 asset_ids。不经过 ChromaDB、jieba 或 RRF 融合。搜索模式重命名：原"综合"→"语义（K聚合）"，原"语义"→"语义（纯向量）"，新增"AI"排在首位默认选中。

**功能 2 — 树状节点列表**：NodePanel 侧边栏节点改为可折叠树形结构。每个节点前有独立箭头图标（▶/▼），点击展开/折叠节点内素材列表。展开按需加载 API，显示素材类型图标 + 文件名。列表末尾增加未分配虚拟节点，与云图未分配节点共享数据源。

## Key Features

**AI 搜索**
- AI 搜索模式位于搜索模式选择器首位，已配模型时默认选中，未配时红点 + 不可选 + 默认回退语义（K聚合）
- 搜索时全量素材信息（id + filename + asset_type + tags）传入 prompt，1M 上下文模型一次调用
- AI 严格匹配，自行判断返回数量，无匹配返回空数组；搜索结果替换主区域搜索列表
- 搜索中搜索按钮显示 spinner，完成后展示结果，失败 toast 报错不回退
- 搜索结果与现有搜索一致：类型计数随结果更新，支持类型/格式/AI状态/标签/日期筛选，支持视图切换和排序
- 搜索框输入后按 Enter 触发，点击搜索按钮触发
- 云图联动：搜索结果高亮，联动 GraphView 过滤显示

**搜索模式重命名与排序**
- 模式选择器顺序：AI（首位）→ 语义（K聚合）→ 语义（纯向量）→ 关键词
- 原"综合"→"语义（K聚合）"，原"语义"→"语义（纯向量）"，原"匹配"→"关键词"

**Prompt 配置**
- `search_ai` 作为第 5 种任务类型加入 `prompts.yaml`，与现有 vision/text/speech/video_summary 结构统一
- 结构：system_format / default / custom / presets
- system_format 强制输出 `{"asset_ids": [1,5,23]}`，无匹配 `{"asset_ids": []}`
- custom 非空优先于 default，custom 为空走 default + system_format
- DEFAULT_PROMPTS 新增 search_ai 条目，启动自动同步至 prompts.yaml
- 设置面板 prompts Tab 新增 search_ai 编辑项

**模型绑定**
- `task_models` 新增 search_ai 条目，用户可绑定 provider + model
- 未配时前端检测 `/api/task-models` 返回无 search_ai 或 model 为空，展示红点 + 禁用
- 推荐默认模型：deepseek-v4-flash（1M 上下文）

**节点树状列表**
- NodePanel 侧边栏节点改为树形结构，每个节点前独立箭头图标（▶ 折叠 / ▼ 展开）
- 箭头点击展开/折叠，节点名点击保持原有选中 + 云图聚焦行为（职责分离）
- 默认全部折叠
- 展开后调 `GET /api/nodes/{id}` 按需加载素材列表，折叠不发生请求
- 素材列表项显示：素材类型图标 + 文件名
- 点击素材项打开右侧详情面板（复用现有 selA）
- 素材项支持拖放到其他树节点或云图（HTML5 DnD 跨组件）
- 拖放后等待 API 返回再刷新对应展开节点列表
- 变更后精准刷新：只刷新已展开节点的列表，折叠节点不请求
- 节点分析追加/聚合完成后联动刷新展开节点
- 无"找相似"按钮
- 素材数量显示在箭头旁边（与展开状态同行）
- 展开按钮有 hover 提示

**未分配虚拟节点（树状列表）**
- 固定在树末尾，始终显示（即使素材数为 0）
- 视觉上与云图未分配节点风格一致：灰色/虚线
- 可展开/折叠，展开后显示未分配素材列表
- 支持从树内展开的已分配节点拖素材到底部节点取消分配
- 支持从网格/列表拖素材到未分配节点取消分配
- 支持从未分配展开列表拖素材到其他树节点分配
- 拖放到未分配节点后端幂等（已分配移除，未分配忽略），toast 显示实际结果
- 素材数量实时联动云图

**树状列表与现有侧栏按钮联动**
- 新建节点弹窗保存后自动刷新树列表
- 节点删除后自动刷新树列表
- 全量聚合完成、追加聚合完成后刷新树列表
- 右键菜单"分析追加到此节点"完成后刷新树列表
- 添加素材/移除素材弹窗确认后刷新树列表

**侧边栏 Tab 联动**
- 搜索 Tab 的类型计数随 AI 搜索结果变化
- 云图 view 下节点选中态在树状列表中高亮

## User Stories

**AI 搜索**
1. 作为素材库用户，我想用自然语言描述想要的素材，由 AI 帮我匹配，减少手动翻找
2. 作为素材库用户，我想在多种搜索模式间切换，AI 模式更智能、K 聚合更全面、纯向量更精准、关键词更快
3. 作为素材库用户，我想自定义 AI 搜索的判断逻辑（prompt），适配自己的素材类型和搜索习惯
4. 作为素材库用户，我想自由选择 AI 搜索用的模型（本地或云端），控制成本和精度
5. 作为素材库用户，未配置 AI 搜索模型时我想看到明确提示（红点），并自动回退到可用模式
6. 作为素材库用户，AI 搜索结果应和普通搜索一样支持筛选、排序、视图切换
7. 作为素材库用户，AI 搜索失败时我不想丢失已有结果，应得到明确的错误提示
8. 作为素材库用户，AI 搜索应严格匹配，不相关的素材不出现，避免噪音

**搜索模式重命名**
9. 作为新用户，搜索模式名应准确反映其机制，不被"综合"这种模糊名字误导

**节点树状列表**
10. 作为素材库用户，我想在侧边栏直接展开节点看里面的素材，不用跳到主区域再回来
11. 作为素材库用户，我想快速浏览多个节点的素材内容，折叠/展开自如切换
12. 作为素材库用户，我想拖放素材从一个节点到另一个节点或云图，操作路径更短
13. 作为素材库用户，我想看到未分配素材并直接在这里分配或取消分配
14. 作为素材库用户，节点素材变更后树列表应即时刷新，不需要手动更新
15. 作为素材库用户，默认所有节点折叠能让我一览全部节点名和素材数量

## Implementation Decisions

**后端 — AI 搜索**
- `GET /api/search` mode 参数新增 `"ai"` 值
- 新增 `search_ai_assets()` 函数，从 DB 查出全量素材（id + filename + asset_type + tags），构建 prompt 调用 LLM，解析返回 asset_ids，回查素材全量数据
- 复用 `PromptConfig.get_prompt("search_ai")` 获取模板
- 复用 `ai_worker.get_adapter("search_ai")` 获取适配器并调用 chat
- 解析 JSON 结果：`{"asset_ids": [...]}`，解析失败返回空
- `DEFAULT_PROMPTS` 新增 search_ai 条目，`PromptConfig._load()` 自动合并
- `DEFAULT_CONFIG.task_models` 新增 search_ai 空占位

**后端 — search_ai prompt 模板**
- system_format：要求输出 `{"asset_ids": [1, 5, 23]}` JSON，严格模式
- default：角色说明（素材搜索助手）+ 素材格式说明 + 筛选原则（宁缺毋滥）
- custom：可覆盖的个性化筛选逻辑（默认空，走 default）
- presets：初始为空列表（后续可扩展）

**前端 — 搜索模式选择器**
- smode 类型扩展为 `"ai" | "keyword" | "semantic" | "combined"`
- 模式选择器 option 渲染顺序：AI → 语义（K聚合）→ 语义（纯向量）→ 关键词
- value 映射：`"ai"`、`"combined"`（历史兼容）、`"semantic"`、`"keyword"`
- AI 模式 option 条件渲染 label 后红点：初始调 `/api/task-models`，检查 search_ai 是否有效
- 未配时 AI option disabled + 红点，默认回退语义（K聚合）

**前端 — 树状节点列表**
- NodePanel.tsx 改造节点渲染：平铺 div → TreeItem 组件
- TreeItem：row（箭头 + 节点名 + 素材数 + 右键菜单按钮）+ 条件展开的素材子列表
- 展开状态：`expandedNodes` Set 管理
- 箭头：▶（折叠）/ ▼（展开），独立点击 toggle
- 节点名 click → `onSelectNode` prop（保持原有行为）
- 展开后调 `GET /api/nodes/{id}`，取 `assets` 数组渲染
- 素材子列表项：类型图标 + 文件名，click → `selA(asset_id)`
- 素材子列表项 draggable，dragstart 设置 `dataTransfer`

**前端 — 未分配虚拟节点**
- TreeItem 列表末尾固定渲染，从 graphData.unassigned 获取数据
- 视觉区分：灰色/虚线风格
- 树内 drop target 区分：已分配节点 drop → POST，未分配节点 drop → DELETE

**前端 — 拖放联动**
- dragstart：`dataTransfer.setData("text/plain", JSON.stringify({asset_id, source_node_id, filename}))`
- drop on 树节点：POST /api/nodes/{target_id}/assets
- drop on 未分配节点：DELETE /api/nodes/{source_node_id}/assets/{asset_id}
- drop on 云图：复用现有 onAssetDrop 逻辑

**联动刷新**
- `nodeRefreshKey` 状态触发 tree 恢复展开态 + 重新加载已展开节点
- 聚合完成/分析追加/删除节点/新建节点后自动刷新

## Testing Decisions

- **最高 seam**：`GET /api/search?mode=ai&q=xxx` — items 结构 + 类型计数
- **次高 seam**：`GET /api/task-models` 返回 search_ai 字段
- **配置 seam**：`PromptConfig` 加载 search_ai + `get_prompt("search_ai")`
- **解析 seam**：`parse_search_ai_result()` — 正常/空/格式错误
- **前端测试**：搜索模式选择器渲染 + 红点逻辑；NodePanel 树形展开/折叠 + 拖放
- **先验测试**：`tests/test_v14.py`（API 端点模式）、V12 前端测试

## Out of Scope

- AI 搜索结果不缓存
- search_ai prompt 不设 presets 初始列表
- 树状列表不支持批量拖放
- 树状列表不支持右键菜单（保留在节点 row 层级）
- 不修改聚合模式行为
- 树状列表不支持搜索/过滤
- 不修改 MCP search_assets 工具

## Further Notes

- AI 搜索依赖 1M 上下文模型，推荐 deepseek-v4-flash
- 树状列表拖放跨组件（NodePanel ↔ GraphView ↔ 网格）通过 HTML5 DnD 实现
- 未分配节点拖放取消分配后端幂等
- prompts.yaml 新增 key 自动合并逻辑 PromptConfig._load() 已内置

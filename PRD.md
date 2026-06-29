# QuickMedia PRD

> 全版本产品需求文档汇总。

---

## v1 — 已完成 ✅

### Problem Statement

用户有大量本地媒体素材（图片、视频、音频、文档），需要快速浏览、搜索和管理。

### Solution

基础素材管理工具：扫描索引、元数据提取、AI 图片分析、全文搜索。

### Key Features

- 扫描索引（SHA256 去重 + inode 追踪）
- 元数据提取（尺寸、分辨率、时长）
- AI 图片分析（场景描述 + 元素标签）
- 手动标签管理
- 全文搜索
- Web UI（暖色调设计系统）

---

## v2 — 已完成 ✅

### Problem Statement

截图中的文字无法检索，视频只有首帧分析，AI 分析阻塞扫描。

### Solution

OCR 文字提取、视频多帧采样、AI 分析异步化。

### Key Features

- OCR 图片文字提取（可搜索）
- 视频多帧采样分析（默认 1 帧）
- AI 分析异步队列（不阻塞扫描）
- 搜索结果高亮
- Finder 打开按钮

---

## v3 — 已完成 ✅

### Problem Statement

视频和音频中的语音内容无法检索，视频缺乏综合理解，分析结果无法刷新。

### Solution

whisper 语音转录、语音内容分析、视频综合总结、重新分析。

### Key Features

- whisper 语音转录（faster-whisper small）
- 语音 AI 标签 + 摘要
- 视频综合总结（语音 + 视觉融合）
- 重新分析（单个 + 批量）
- 素材删除
- 手动扫描

---

## v4 — 已完成 ✅

### Problem Statement

基础属性（时间、格式）污染标签系统，标签列表冗长，筛选能力不足，无法按日期区间、文件格式、AI 状态筛选。

### Solution

侧边栏筛选重构：类型、时间区间、文件格式、AI 状态、标签五组筛选组件，全部位于侧边栏，使用统一的下拉多选/日期控件交互。

### Key Features

- 创建时间 / 修改时间日期区间筛选
- 文件格式下拉多选（默认「点击筛选」，选中显示「已选 N 项」+ ✕）
- AI 状态下拉多选（交互同格式）
- 标签下拉多选（输入框展示已选标签名，逗号分隔，高度自适应，取并集）
- 启动时清理旧时间/格式/类型标签
- Scanner 不再生成这些标签

### User Stories

1. As a 用户，I want 按日期区间筛选素材，so that 能快速找到"上周拍的视频"。
2. As a 用户，I want 按文件格式筛选，so that 只看到"所有 PNG 图片"。
3. As a 用户，I want 按 AI 分析状态筛选，so that 能快速找到分析失败的素材并重试。
4. As a 用户，I want 多个筛选条件组合使用，so that 能精确筛选。
5. As a 用户，I want 标签列表不再被自动生成的格式化标签淹没。
6. As a 新用户，I want 筛选交互与标签筛选一致，降低学习成本。

### Implementation Decisions

详见 [docs/v4/plan.md](docs/v4/plan.md)、[docs/v4/design.md](docs/v4/design.md)、[docs/v4/tasks.md](docs/v4/tasks.md)。

---

## v5 — 自定义 AI Prompt

### Problem Statement

当前 AI 分析的 prompt 硬编码在代码中，所有用户使用同一套分析维度。摄影师想要构图/色彩分析，宠物主人想要品种识别，设计师想要版式/色彩方案——不同场景需要不同的分析指令。

### Solution

将 AI prompt 从代码中分离为配置文件，用户可自定义分析指令。系统固定追加格式尾巴确保解析不受影响。

### Key Features

- 独立配置文件 `prompts.yaml`，4 个分析类型 × 14 个预设模板（vision:4, text:3, speech:3, video:1+default）
- 双层 prompt：用户自定义优先，系统默认兜底
- JSON 统一输出格式，解析稳定
- 设置面板 AI 分析 Tab 页：模板选择 + 自定义编辑 + 保存/恢复默认
- 修改后即时生效（每次分析实时读取配置）
- Ollama `think` 参数控制思考过程开关

### Implementation Decisions

- 配置位置：`~/.asset-manager/prompts.yaml`
- 配置结构：扁平式（custom/presets 与 system_format/default 同级）
- Prompt 读取：每次分析实时读取，不缓存
- 预设模板硬编码在 `DEFAULT_PROMPTS` 中，启动时自动同步至 prompts.yaml
- 输出格式：JSON（解析器提取 markdown 代码块或 `{...}`）
- 重新分析：清除旧描述和 auto 标签后重新入队
- AI 状态：检查 ai_description/ai_summary 判断是否已完成，无数据显示"待分析"

### Testing Decisions

- PromptConfig 类加载和 fallback 逻辑
- API 读写端点
- 各分析方法从配置读取而非硬编码

### Tasks

详见 [docs/v5/tasks.md](docs/v5/tasks.md)。


## v6 — 多模型配置

### Problem Statement

当前 AI 分析硬编码使用本地 Ollama 单一模型。用户可能想用更好的远端模型（如 GPT-4o 做图片分析、Claude 做文档分析），或完全切换 provider（DeepSeek / OpenRouter）。缺乏灵活配置机制，扩展新模型需改代码。

### Solution

将 AI 模型配置从硬编码改为可配置的多 provider 架构。按协议适配不同服务商（OpenAI 兼容 / Ollama 原生），不同分析任务可独立选择 provider + model。API Key 分离到 .env 安全存储。

### Key Features

- **Provider 注册** — 支持 Ollama / OpenAI 兼容（OpenAI / DeepSeek / OpenRouter）两类协议适配器
- **任务模型绑定** — 每种分析类型独立配置 provider + model
- **模型能力目录** — `models.yaml` 出厂定义支持模型及 capabilities，首次启动复制到用户目录，升级自动合并
- **API Key 安全** — Key 存 `~/.asset-manager/.env`，config.yaml 可安全分享
- **自动迁移** — 检测旧 `ai.*` 配置自动生成 providers + task_models
- **Web UI** — 独立模型管理页面，provider 管理 + 任务绑定 + 连接测试
- **连接测试** — 支持测试单个 provider 是否可用

### User Stories

1. As a 用户，I want 图片分析用 GPT-4o，文档分析用本地方案，so that 远端高质量 + 本地快速兼顾。
2. As a 用户，I want 一键添加 DeepSeek provider，so that 无需写代码即可切换模型。
3. As a 用户，I want API Key 不暴露在 config 文件中，so that 分享配置或截图时不会泄露。
4. As a 用户，I want 升级后自动保留现有 Ollama 配置，so that 不需要手动迁移。

### Implementation Decisions

- **协议适配**：按协议写适配器，不按公司。一套 OpenAI 兼容适配器覆盖 3 个 provider
- **配置粒度**：按分析任务绑定模型（vision/text/speech/video_summary），非全局
- **迁移策略**：检测旧 `ai.ollama_url` 字段，自动写入 providers.ollama + task_models
- **模型目录**：项目目录 `quickmedia/models.yaml`，首次启动复制到用户目录

### Testing Decisions

- 最高 seam：GET/PUT /api/providers + POST /api/providers/test
- 模块 seam：ProviderRegistry + OpenAIAdapter + AIWorker 多模型路由
- 前端 seam：ModelManager 独立页面
- 迁移测试：旧配置 → 新结构自动转换

### Tasks

详见 [docs/v6/tasks.md](docs/v6/tasks.md)。

---

## v7 — MiniMax 支持 + 设置弹窗重构

### Problem Statement

缺少 MiniMax 国产模型支持。设置面板为侧边栏内嵌，占用空间且交互分散。

### Solution

| 需求 | 方案 |
|------|------|
| MiniMax | models.yaml 加 provider 条目，零代码改动 |
| 设置弹窗 | 模态弹窗替代侧边栏，基础配置/模型管理/AI 提示词三 Tab |

### Key Design Decisions

- 关闭弹窗直接丢弃未保存内容
- 保存按钮浅色初始，有修改后激活
- Provider 删除前确认弹窗
- MiniMax 走现有 OpenAI 适配器

详见 [docs/v7/tasks.md](docs/v7/tasks.md)。---

---

## v8 — 向量化 + 语义搜索

### Problem Statement

搜索仅支持关键词精确匹配，搜"蓝色风格"找不到蓝色调图片，搜"会议相关"找不到会议录音。素材越多，精确匹配的局限性越大。

### Solution

通过 embedding 向量化实现语义理解，用户用自然语言描述即可找到相关素材。同时支持相似素材推荐。

### Key Design Decisions

- 向量存储：ChromaDB，内嵌模式零配置
- embedding 作为第 5 种 AI 分析类型，AI 分析完成后自动入队
- 搜索：综合 / 语义 / 匹配 三种模式
- 相似素材：详情页叠加层展示
- 入库和搜索必须同一模型，切换需重建全量向量

详见 [docs/v8/tasks.md](docs/v8/tasks.md)。

---

## v9 — 语义搜索优化 ✅

### Problem Statement

语义搜索效果差——模型对短标签中文区分度不够，tags 向量检索意图弱。

### Solution

AI 输出新字段 search_terms（检索意图搜索词，每词独立向量）+ Top-K 聚合匹配。

### 实现成果

- **search_terms + tags 合并向量化**——每个素材的标签和搜索词合并去重后独立存向量，Top-K 聚合排序
- **视频字段迁移**——ai_description → visual_description；无声视频自动填充 video_summary
- **多帧一次 API 调用**——video_vision 独立 prompt 类型，Qwen-VL 多帧批量分析
- **文档格式扩展**——CSV/JSON/XLSX/DOCX 支持
- **⭐ 智能标记**——语义+关键词双重命中 + 距离比的 1-5 星重要度标识
- **搜索筛选联动**——搜索结果上叠加侧栏筛选，纯语义模式独立
- **状态实时轮询**——列表3s/详情5s 自动刷新
- **文档预览**——缩略图区显示前 3 行文字
- **热加载 Prompt**——自定义 prompt 保存后即时生效

详见 [docs/v9/tasks.md](docs/v9/tasks.md)。


---

## v10 — 可配置扫描文件夹 ✅

### 实现成果

- **浏览器文件夹配置** — Web UI 管理扫描目录，增删改、命名、启用开关
- **Finder 集成** — macOS 原生文件夹选择器，自动转换 HFS→POSIX 路径
- **智能引导** — 首次无配置自动弹设置、红点提示、扫描保护
- **热加载** — 保存后即时生效，无需重启
- **向后兼容** — 旧 watch_paths 自动迁移新格式

详见 [docs/v10/prd.md](docs/v10/prd.md)。


---

## v11 — MCP 对话式素材管理 ✅

### 实现成果

- **Hermes 原生集成** — quickmedia mcp 启动 MCP server，Hermes 配置 3 行即用
- **6 工具 + 批量** — search_assets / get_asset / list_assets / find_similar / add_asset / delete_asset
- **结构化输出** — Pydantic 模型 + Field(description)，协议层完整字段schema
- **架构复用** — search.py / asset_ops.py 共享模块，API + MCP 共用
- **单文件扫描** — Scanner.scan_file 精确添加单个文件

详见 [docs/v11/prd.md](docs/v11/prd.md)。

---

## v12 — 素材聚合（Aggregation）

### Problem Statement

素材通过 AI 分析获得了描述、标签、摘要，但所有素材仍然是以扁平列表呈现。用户没有"概念级"的素材组织方式——无法按主题（如"猫的照片"、"购物记录"）快速浏览跨类型的素材集合。标签可以实现部分筛选，但需要手动创建且归因粒度太细。

### Solution

AI 驱动的素材自动聚类。全库分析后生成聚合节点（~10-30个），每个节点代表一个语义主题，包含节点名、描述、关联素材。支持全量分析、全量追加、追加分析三种模式，全部手动触发。节点和素材为多对多关系，节点可手动编辑。

### Key Features

- **三种聚合模式** — 全量分析（从头重建）/ 全量追加（增量发现新节点）/ 追加分析（新素材入已分配节点）
- **AI 自动聚类** — 复用现有 text 分析模型，单次 prompt 调用分析全库素材，返回 nodes + assignments
- **独立异步 Worker** — 独立进程 + 独立 SQLite 队列表，与现有 AI 分析队列完全隔离
- **多对多节点关系** — `nodes` + `node_assets` 表，一个素材可属于多个节点，一个节点包含多个素材
- **节点编辑** — 右键菜单支持重命名、编辑描述、删除节点、手动添加/移除素材
- **侧边栏 Tab** — 顶部双 Tab 切换：Tab1 搜索与筛选（现有）、Tab2 聚合节点（新增）
- **素材列表复用** — 点击节点后右侧素材面板复用现有素材浏览列表
- **级联清理** — 删除素材时自动清理 node_assets 关联

### Implementation Decisions

- **聚合模式**：全量分析 / 全量追加 / 追加分析，全部手动触发
- **异步机制**：独立 Aggregation Worker 进程，独立 aggregation_queue 表
- **任务限制**：单任务，运行中拒绝新提交
- **失败处理**：直接标记失败，不重试
- **Prompt**：函数根据 mode 参数组合，AI 不感知 mode
- **模型**：复用现有 text 分析模型配置
- **前端**：NodePanel.tsx + AddAssetModal.tsx，纯 React+TailwindCSS，零依赖
- **后端**：quickmedia/aggregation/ 子包（worker.py / prompts.py / api.py）

### Testing Decisions

- **最高 seam**：POST /api/aggregation/run、GET /api/aggregation/status、节点 CRUD API
- **中层 seam**：数据库 nodes/node_assets/aggregation_queue 表 + 级联删除
- **低层 seam**：build_aggregation_prompt() 三种 mode 输出
- **集成 seam**：delete_asset_full 是否清理 node_assets

详见 [docs/v12/tasks.md](docs/v12/tasks.md)。

---

## v13 — 云图

### Problem Statement

素材聚合节点为扁平列表展示，用户无法直观看到节点间的语义关系、节点与素材的归属关系。

### Solution

Cytoscape.js 力导向图可视化。聚合节点和素材作为图节点渲染，共享边展示节点间关系。

### Key Features

- 视图切换三按钮：☁ 云图 / ▦ 网格 / ☰ 列表
- 聚合节点按素材数量缩放 + 梯度着色
- 共享边（粗细=共享素材数），未分配节点（前端虚拟）
- 素材节点按类型着色，zoom 自适应展开缩略图
- 单击选中/双击展开折叠/单击素材打开详情
- 搜索高亮 + WebSocket 增量推送
- 缩放控件 + 手动重新加载

---

## v14 — 节点增强 + MCP 完善

### Problem Statement

聚合节点的管理能力不足：节点创建只能通过 AI 聚合，无法手动创建；节点删除有 bug 无法使用；单个节点缺少智能补充素材的能力。MCP 工具只覆盖素材操作，无法在对话中管理聚合节点。此外，刷新页面时配置引导弹框过于激进，原生 confirm/alert 弹窗与设计系统不一致。

### Solution

1. **节点分析追加**：右键节点触发，AI 分析全库未连接至此节点的素材，自动匹配添加
2. **手动创建节点**：聚合节点列表支持手动新建，输入名称和描述
3. **修复节点删除**：修复后端 asyncio 冲突 + 前端选中状态清理 + 删除确认弹框改为设计风格
4. **去掉配置引导**：移除页面刷新时自动弹出设置弹窗的逻辑
5. **统一弹框风格**：所有 confirm/alert 原生弹窗替换为设计系统风格的确认弹框和顶部居中 toast
6. **MCP 节点管理**：新增 7 个 MCP 工具覆盖节点 CRUD + 分析追加 + 手动分配素材

### User Stories

1. 作为素材库用户，我想对已有聚合节点一键分析还能加入什么素材，让节点自动补充遗漏的素材
2. 作为素材库用户，我想手动创建聚合节点并命名，不用必须依赖 AI 全量聚合
3. 作为素材库用户，我想删除不再需要的聚合节点，并且操作有确认、有反馈
4. 作为素材库用户，我不想在刷新页面时被自动弹出的设置窗口打断
5. 作为素材库用户，我想所有确认/提示弹窗都统一风格，不再看到浏览器原生的 alert/confirm
6. 作为 AI Agent 用户，我想在 Hermes 对话中直接管理聚合节点（查看、创建、删除、分析追加），不用切换到 Web UI

### Implementation Decisions

- 节点分析追加复用聚合模块的 AI 调用链路（OpenAIAdapter + JSON 解析），新增专属 prompt
- 分析追加使用 daemon 线程，执行期间前端节点行显示旋转菊花 + hover 提示
- 分析范围：全库所有未连接到此节点的素材（不受"未分配"限制），自动添加无需确认
- 无可分析素材时（节点无素材或全库已全连接），前端提示不调 AI
- 新建节点复用现有的编辑弹框样式，标题改为"新建节点"，保存调 POST
- 删除节点修复：后端 `def` → `async def`，`asyncio.run()` → `await broadcast_graph_changed()`
- 删除节点前端：调父组件 `onSelectNode(null)` 清选中，弹框内显示删除中菊花
- 统一弹框：所有 confirm 替换为编辑弹框风格确认框，所有 alert 替换为顶部居中 toast（2.5s）
- 去掉配置引导仅删 `useEffect` 中的 `fetch("/api/config/watch-paths") + sso(true)` 行，不影响扫描按钮的独立检查
- 全量分析已有节点时弹出确认框，警告将删除全部已有节点
- 手动移除素材复用 AddAssetModal 组件，支持多选批量取消分配
- 新建节点支持"保存并分析"：创建后自动分析追加
- 云图聚合节点圆圈内显示素材数量（白色粗体），颜色随素材数量梯度变化
- 未分配节点也显示素材数量
- MCP 新增 trigger_scan / get_aggregation_status / reanalyze_asset / add_asset_tag / remove_asset_tag / get_stats 工具，总计 15+ 工具
- MCP `analyze_append_node` 使用阻塞模式（30s 超时），`run_aggregation` 使用阻塞模式（300s 超时），详见 ADR-0001

### Testing Decisions

- 最高 seam：API 端点（`POST/DELETE/GET /api/nodes`，`POST /api/nodes/{id}/analyze-append`）
- 次高 seam：MCP 工具（通过 stdio 调用验证工具输出结构）
- 前端组件测试：NodePanel 右键菜单交互、弹框/Toast 组件渲染
- 参考现有测试：`tests/test_v12.py`（聚合节点 CRUD 测试），V14 新增 `tests/test_v14.py`

### Out of Scope

- 节点分析追加不支持用户确认再添加（自动完成）
- 不修改其他聚合模式（full/full_append/append）的行为
- 不添加节点排序/搜索功能
- 不添加节点内素材的批量移除
- 不修改现有 settings modal 的其他行为

### Further Notes

- 删除节点的修复同时也覆盖了 create/update/assign 端点的同类 `asyncio.run()` 问题
- Toast 组件作为通用组件抽取，后续所有提示均可复用

详见 [docs/v13/prd.md](docs/v13/prd.md)。

---

## v15 — AI 搜索 + 节点树状列表

### Problem Statement

搜索方面：现有三种搜索模式（综合/语义/关键词）都依赖 ChromaDB/jieba 等索引基础设施。用户用自然语言描述想要的素材（如"上次聚会时小明切蛋糕的视频"），无法通过现有搜索直接找到——需要 AI 理解用户意图后匹配素材。

节点管理方面：聚合节点侧边栏展示为扁平列表，用户只能看到节点名和素材数量。想浏览节点内素材必须点击节点名再等主区域刷新，操作割裂。同时缺少未分配素材的直观入口。

### Solution

**功能 1 — AI 搜索**：纯 LLM 单次调用。用户输入自然语言查询，全量素材（id + filename + type + tags）送入模型，模型直接返回匹配的 asset_ids。不经过 ChromaDB、jieba 或 RRF 融合。搜索模式重命名：原"综合"→"语义（K聚合）"，原"语义"→"语义（纯向量）"，新增"AI"排在首位默认选中。

**功能 2 — 树状节点列表**：NodePanel 侧边栏节点改为可折叠树形结构。每个节点前有独立箭头图标（▶/▼），点击展开/折叠节点内素材列表。展开按需加载 API，显示素材类型图标 + 文件名。列表末尾增加未分配虚拟节点，与云图未分配节点共享数据源。

### Key Features

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
- 推荐默认模型：deepseek-v4-flash（1M 上下文，零成本额外配置）

**节点树状列表**
- NodePanel 侧边栏节点改为树形结构，每个节点前独立箭头图标（▶ 折叠 / ▼ 展开）
- 箭头点击展开/折叠，节点名点击保持原有选中 + 云图聚焦行为（职责分离）
- 默认全部折叠
- 展开后调 `GET /api/nodes/{id}` 按需加载素材列表，折叠不发生请求
- 素材列表项显示：素材类型图标 + 文件名
- 点击素材项打开右侧详情面板（复用现有 selA，与网格/列表/云图一致）
- 素材项支持拖放到其他树节点或云图（HTML5 DnD 跨组件），作为同时分配来源到目标节点
- 拖放后等待 API 返回再刷新对应展开节点列表，乐观更新已分配/未分配节点
- 变更后精准刷新：只刷新已展开节点的列表，折叠节点不请求
- 节点分析追加/聚合完成后联动刷新展开节点
- 无"找相似"按钮
- 素材数量显示在箭头旁边（与展开状态同行）
- 展开按钮有 hover 提示

**未分配虚拟节点（树状列表）**
- 固定在树末尾，始终显示（即使素材数为 0）
- 视觉上与云图未分配节点风格一致：灰色/虚线
- 可展开/折叠，展开后显示未分配素材列表（显示逻辑同上）
- 支持从树内展开的已分配节点拖素材到底部节点取消分配
- 支持从网格/列表拖素材到未分配节点取消分配
- 支持从未分配展开列表拖素材到其他树节点分配
- 拖放到未分配节点后端幂等（已分配移除，未分配忽略），toast 显示实际结果
- 素材数量实时联动云图

**树状列表与现有侧栏按钮联动**
- 新建节点弹窗保存后自动刷新树列表
- 节点删除后自动刷新树列表（清空选中状态）
- 全量聚合完成、追加聚合完成后刷新树列表
- 右键菜单"分析追加到此节点"完成后刷新树列表
- 添加素材/移除素材弹窗确认后刷新树列表

**侧边栏 Tab 联动**
- 搜索 Tab 的类型计数随 AI 搜索结果变化
- 云图 view 下节点选中态在树状列表中高亮

### User Stories

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

### Implementation Decisions

**后端 — AI 搜索**
- `GET /api/search` mode 参数新增 `"ai"` 值
- 新增 `search_ai_assets()` 函数（在 search.py 或独立模块），从 DB 查出全量素材（id + filename + asset_type + tags），构建 prompt 调用 LLM，解析返回 asset_ids，回查素材全量数据
- 复用 `PromptConfig.get_prompt("search_ai")` 获取模板
- 复用 `ai_worker.get_adapter("search_ai")` 获取适配器并调用 chat
- 解析 JSON 结果：`{"asset_ids": [...]}`，解析失败返回空
- `DEFAULT_PROMPTS` 新增 search_ai 条目，`PromptConfig._load()` 自动合并
- `DEFAULT_CONFIG.task_models` 新增 search_ai 空占位，`_fill_missing_task_models()` 自动填充

**后端 — search_ai prompt 模板**
- system_format：要求输出 `{"asset_ids": [1, 5, 23]}` JSON，严格模式
- default：角色说明（素材搜索助手）+ 素材格式说明 + 筛选原则（宁缺毋滥）
- custom：可覆盖的个性化筛选逻辑（默认空，走 default）
- presets：初始为空列表（后续可扩展）

**前端 — 搜索模式选择器**
- smode 类型扩展为 `"ai" | "keyword" | "semantic" | "combined"`
- 模式选择器 option 渲染顺序：AI → 语义（K聚合）→ 语义（纯向量）→ 关键词
- value 映射：`"ai"`、`"combined"`（历史兼容）、`"semantic"`、`"keyword"`
- AI 模式 option 条件渲染 label 后红点：
  - 初始挂载调 `/api/task-models`，检查 `search_ai` 是否有效（provider + model 均非空）
  - 有效时 AI option 可选中 + 默认选中
  - 无效时 AI option 添 `disabled` + 红点指示器，默认选中 fallback 到语义（K聚合）
- 搜索调用：mode="ai" 时 `GET /api/search?q=xxx&mode=ai`，与现有逻辑一致
- 搜索中 `slc` 状态控制搜索按钮 spinner

**前端 — 树状节点列表**
- NodePanel.tsx 改造节点渲染：平铺 div → 递归 TreeItem 组件
- TreeItem：row（箭头 + 节点名 + 素材数 + 右键菜单按钮）+ 条件展开的素材子列表
- 展开状态：`expandedNodes` Set 由 NodePanel 或父组件管理
- 箭头：▶（折叠）/ ▼（展开），独立点击事件 toggle 展开
- 节点名 click → `onSelectNode` prop（保持原有行为）
- 展开后调 `GET /api/nodes/{id}`，取 `assets` 数组渲染子列表
- 素材子列表项：类型图标（根据 asset_type）+ 文件名
- 素材子列表项 click → `selA(asset_id)` 打开右侧详情
- 素材子列表项 draggable，dragstart 设置 `dataTransfer`

**前端 — 未分配虚拟节点**
- TreeItem 列表末尾固定渲染未分配节点（从 graphData.unassigned 获取）
- 视觉区分：gray/虚线风格（CSS class 或 inline style）
- 展开后显示未分配素材（同树素材项逻辑，但源数据不同）
- 树内 drop target 需要区分"已分配节点"和"未分配节点" target：
  - 已分配节点 drop → POST /api/nodes/{id}/assets（分配）
  - 未分配节点 drop → DELETE /api/nodes/{source_node_id}/assets/{id}（取消分配），需从 drag data 获取 source_node_id

**前端 — 拖放联动**
- dragstart：设置 `dataTransfer.setData("text/plain", JSON.stringify({asset_id, source_node_id, filename}))`
- drop on 树节点：发 POST /api/nodes/{target_id}/assets {asset_ids: [asset_id]}
- drop on 未分配节点：发 DELETE /api/nodes/{source_node_id}/assets/{asset_id}
- drop on 云图：复用现有 onAssetDrop 逻辑
- 拖放完成后刷新 source 和 target 展开节点（如已展开）
- 从网格/列表拖素材到树节点：需要给网格/列表素材卡片加 dragstart 逻辑（若已存在则复用）

**联动刷新**
- `nodeRefreshKey` 状态：触发 tree 恢复展开态 + 重新加载已展开节点的素材
- 聚合完成/分析追加完成 → `setNodeRefreshKey(k => k + 1)` + 重新取 graphData
- 删除节点 → 调 `onSelectNode(null)` + 刷新 tree + graphData
- 新建节点 → 刷新 tree + 后台自动展开新节点

**CONTEXT.md 更新**
- 搜索模式改名 + 新增 AI 搜索术语
- 新增"默认搜索模式"描述
- 新增"节点树状列表"术语
- 新增"未分配虚拟节点（树状列表）"术语
- Task Model Binding 修正为 AI 任务类型

### Testing Decisions

- **最高 seam**：`GET /api/search?mode=ai&q=xxx` — 验证返回的 items 结构 + 类型计数
- **次高 seam**：`GET /api/task-models` 返回 search_ai 字段的正确性
- **配置 seam**：`PromptConfig` 加载 search_ai prompt 模板 + `get_prompt("search_ai")` 拼接
- **解析 seam**：`parse_search_ai_result()` — 输入 LLM 响应 JSON，输出 asset_ids 列表，覆盖正常/空/格式错误
- **前端组件测试**：搜索模式选择器渲染 + 红点逻辑 + 默认选中回退；NodePanel 树形展开/折叠 + 素材渲染 + 拖放事件
- **先验测试**：`tests/test_v14.py`（API 端点测试模式）、V12 前端测试（NodePanel 组件）

### Out of Scope

- AI 搜索结果不缓存，每次搜索重新调 LLM
- search_ai prompt 不设 presets 初始列表（用户自由编辑 custom）
- 树状列表不支持批量拖放（一次只拖一个素材）
- 树状列表不支持右键菜单（右键菜单保留在节点 row 层级）
- 不修改聚合模式（full/full_append/append）行为
- 树状列表不支持搜索/过滤（仅展开/折叠浏览）
- 不修改 MCP search_assets 工具（MCP 工具保持现有三种搜索模式）

### Further Notes

- AI 搜索依赖 1M 上下文模型，推荐 deepseek-v4-flash。素材数 < 5000 时 prompt 总量在 70K tokens 左右
- 树状列表拖放跨组件（NodePanel ↔ GraphView ↔ 网格）通过 HTML5 DnD 实现，与现有云图拖放统一
- 未分配节点拖放取消分配后端幂等设计：DELETE 已存在的关联返回 ok，不存在的也返回 ok
- prompts.yaml 新增 key 自动合并逻辑 PromptConfig._load() 已内置，无需改加载代码

---

## v16 — 聚合 Prompt 自定义

### Problem Statement

聚合节点生成质量取决于 prompt 指令。当前四种聚合 prompt（全量/全量追加/追加/节点分析追加）全部硬编码在 `aggregation/prompts.py` 中，用户无法根据素材特点调整聚合策略。此外，聚合任务复用了"文档分析"的模型配置（`task_models.text`），无法独立选择更适合聚合的模型。

### Solution

将 4 种聚合 prompt 迁入 `prompts.yaml`，与已有的 vision/text/search_ai 等统一管理。新增 `task_models.aggregation` 独立模型绑定，不再复用 text。设置面板 AI 提示词 Tab 按三组展示：分析 / 聚合 / 搜索。

### Key Features

**聚合 Prompt 配置**
- 新增 4 个 prompt 类型：`aggregation_full`、`aggregation_full_append`、`aggregation_append`、`aggregation_analyze_append`
- 与现有 prompt 类型相同结构：system_format / default / custom / presets
- system_format 固定 JSON 输出格式约束，custom 非空优先于 default
- 模板可用占位符：`{assets}` 素材列表、`{nodes}` 已有节点、`{node_name}` 节点名、`{node_description}` 节点描述、`{existing_assets}` 已有素材摘要、`{candidates}` 候选素材
- 设置面板每个编辑区下方显示可用占位符说明
- DEFAULT_PROMPTS 硬编码模板，启动自动同步至 prompts.yaml，升级合并系统字段、保留用户 custom

**聚合模型绑定**
- 新增 `task_models.aggregation` 独立配置项
- 不再复用 `task_models.text`（文档分析）
- 未配置时聚合任务执行失败
- 设置面板模型管理 → 任务配置中显示"聚合"绑定行

**设置面板 Prompt Tab 分组**
- 三组：分析（图片/文档/语音/视频视觉/视频综合）、聚合（全量聚合/全量追加/追加分析/节点追加）、搜索（搜索）
- 分组方式一致，每组内按钮同行展示

### User Stories

1. 作为素材库用户，我想自定义聚合策略（如优先按项目分类而非主题），适配我的素材库
2. 作为素材库用户，我想为聚合单独配置模型，和文档分析使用不同的 AI
3. 作为素材库用户，我想知道 prompt 模板中可用的占位符变量及其含义
4. 作为素材库用户，修改聚合 prompt 后立即生效，聚合分析使用我最新的指令
5. 作为素材库用户，设置面板 prompt 按分组展示更清晰，不需要在大量选项里翻找

### Implementation Decisions

**后端 — Prompt Config**
- `DEFAULT_PROMPTS` 新增 4 个聚合条目
- 每个条目：system_format（JSON 格式约束） + default（完整指令） + custom 空 + presets 空
- `PromptConfig._load()` 自动合并（已有逻辑，无需修改）
- `PUT /api/prompts` validator 扩展为接受全部 10 个 type

**后端 — Aggregation Prompts 重构**
- `aggregation/prompts.py` 的 `_build_full()`、`_build_full_append()`、`_build_append()`、`build_append_prompt()` 改为从 `PromptConfig` 读取模板
- 模板通过占位符注入动态数据：`{assets}`、`{nodes}`、`{node_name}`、`{node_description}`、`{existing_assets}`、`{candidates}`
- `_asset_text()` 继续由代码生成（素材文本格式不进入模板）

**后端 — 聚合模型绑定**
- `aggregation/core.py` 的 `_get_adapter()` 从 `get_task_binding("text")` 改为 `get_task_binding("aggregation")`
- `DEFAULT_CONFIG.task_models` 新增 `"aggregation": {"provider": "", "model": ""}`
- `_fill_missing_task_models()` 自动同步（已有逻辑）

**前端 — SettingsModal Prompts Tab**
- 按钮列表分为三组，每组加标题
- 分析组：vision, text, speech, video_vision, video_summary
- 聚合组：aggregation_full, aggregation_full_append, aggregation_append, aggregation_analyze_append
- 搜索组：search_ai
- 每个编辑区 textarea 下方显示灰色占位符说明
- 占位符说明从硬编码映射获取（不依赖后端）

**前端 — ModelManager**
- `TASK_LABELS` 和 `TASK_HINTS` 新增 `aggregation: "聚合分析"`

**CONTEXT.md 更新**
- 聚合模型：独立 task_models.aggregation
- 聚合 Prompt 配置：术语新增
- Task Model Binding：加 aggregation
- AI Prompt 配置：更新类型计数

### Testing Decisions

- **最高 seam**：`GET/PUT /api/prompts` — aggregation_full 等 4 个新 type 的读写
- **次高 seam**：`POST /api/aggregation/run` — 聚合使用 PromptConfig 读取模板
- **配置 seam**：`DEFAULT_PROMPTS` 新增条目结构校验 + `PromptConfig.get_prompt("aggregation_full")` 拼接
- **前端 seam**：SettingsModal prompts Tab 三组布局 + 占位符说明渲染
- **先验测试**：`tests/test_v15.py`（prompts API）、`tests/test_v12.py`（聚合 prompt 测试）

### Out of Scope

- 不修改 `_asset_text()` 的素材格式化逻辑
- 不修改聚合 Worker/线程的调度逻辑
- 预设模板（presets）初始为空，后续版本再扩展
- 不修改 MCP 端的聚合工具

### Further Notes

- 聚合 prompt 模板很长（full 模式 ~100 行），推荐在 Web UI 编辑而非手动改文件
- `PromptConfig._load()` 已内置合并逻辑，DEFAULT_PROMPTS 新增 key 自动同步
- `_fill_missing_task_models()` 自动填充 aggregation 到用户 config.yaml

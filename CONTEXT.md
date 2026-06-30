# QuickMedia — Domain Glossary

> 只收录领域术语，不含实现细节。用于统一讨论语言。

## 核心概念

### 素材（Asset）

被 QuickMedia 索引的任意文件。素材始终保留在原始位置，QuickMedia 只记录引用路径和元数据。

- 每个素材有唯一的资产 ID、SHA256 内容哈希、当前文件路径
- 素材可以被扫描入库、被标记删除、被版本归档
- 同一素材可能有多份拷贝（相同哈希，不同路径）

### 扫描（Scan）

遍历目录，将符合格式白名单的文件入库。首次扫描创建新记录，后续扫描通过 inode 或哈希匹配更新已有记录。

### 监控路径（Watch Path）

用户配置的需要被扫描和监听的目录。每个路径可独立设置递归深度。

### 素材类型（Asset Type）

素材的一级分类，由文件扩展名自动判定。取值：image / video / audio / document / other。

### 标签（Tag）

附加在素材上的文本标记，用于筛选和组织。QuickMedia 使用扁平标签系统（无父子层级），通过多选交集筛选。

标签有三种来源：
- **auto** — 系统在扫描时自动生成（类型标签「图片」、格式标签「PNG」、时间段标签「2026-06」）
- **ai** — AI 模型分析素材内容后生成（虚线边框，待用户确认）
- **manual** — 用户手动添加（实线边框）

### 描述（Description）

用户为素材自由撰写的文本说明。可编辑。

### AI 描述（AI Description）

本地视觉模型对图片/视频首帧自动生成的内容描述。存储在 ai_description 字段。

### AI 摘要（AI Summary）

本地文本模型对文档自动生成的内容摘要。存储在 ai_summary 字段。

### 缩略图（Thumbnail）

素材的低分辨率预览图（256px max）。图片直接缩放生成，视频提取首帧生成。缩略图状态流转：pending → processing → done / failed。

缩略图 URL 携带 `?t=<modified_at>` 缓存破坏参数，确保缩略图更新后浏览器不会使用旧缓存。

### 实时监听（Watch）

通过文件系统事件（fsevents）实时感知监控路径内的文件增删改，自动更新素材库。

## 文件与去重

### 内容哈希（Content Hash）

对文件内容计算的 SHA256 值。相同哈希 = 相同内容，无论文件路径或名称。

### 副本（Duplicate）

与已有素材哈希相同但路径不同的文件。不单独入库，只在主记录中标记「有 N 个副本」。

### Inode 匹配

同文件系统卷内，通过 inode + device 号快速识别同一文件（即使被重命名或移动）。优先于哈希匹配。

### 文件删除（Deletion）

磁盘文件被删除后，素材记录不会直接移除，而是标记为 deleted 状态，保留标签和描述等元数据。

### 素材删除（Asset Deletion）

用户手动从数据库中移除素材记录。删除操作清除素材及所有关联数据（标签关联、AI 分析队列、缩略图记录），但不影响磁盘文件。文件仍存在时，下次扫描会重新入库。

### 文件修改（Modification）

磁盘文件内容变更导致哈希变化时，旧记录版本归档（version_of 指向新记录），新哈希作为新素材入库。

## 搜索与筛选

### 全文搜索（Full-Text Search）

跨文件名、描述、AI 描述、AI 摘要、OCR 文字、标签名称进行关键词匹配。

### 搜索高亮（Search Highlight）

搜索结果列表中，匹配到的关键词以珊瑚色（#cc785c）高亮标记，帮助用户快速定位匹配来源。

### 类型筛选（Type Filter）

按素材类型（image / video / audio / document）缩小范围。位于侧边栏最上方，展开显示全部类型及对应数量。与下方筛选条件取交集。

### 时间区间筛选（Time Range Filter）

分别提供创建时间和修改时间的日期区间筛选，使用原生 `<input type="date">` 控件。默认全部。

### 文件格式筛选（Format Filter）

下拉多选控件。默认显示「点击筛选」灰色占位文字；选择后显示「已选 N 项」珊瑚色文字及 ✕ 清除按钮。展开后多选格式切换（png, jpg, mp4, wav, md, txt, pdf, mov, avi, gif, webp, m4a）。默认全不选 = 全部。

### AI 状态筛选（AI Status Filter）

下拉多选控件。交互同文件格式筛选。选项：已完成、分析中、等待、失败。默认全不选 = 全部。

### 标签筛选（Tag Filter）

下拉多选控件。默认显示「点击筛选」灰色占位文字；选择后输入框内展示所有已选标签名（逗号分隔），高度自适应，末尾显示已选数量和 ✕ 清除按钮。展开后为可滚动多选面板，顶部显示已选数量及清除全部按钮。多选时取并集（OR）。

## AI 分析

### 视觉分析（Vision Analysis）

本地多模态模型对图片内容进行理解，输出场景描述和元素标签。

### OCR 文字提取（OCR Text Extraction）

视觉分析的一部分。模型识别图片中的文字并输出提取结果。提取的文字存入 ocr_text 字段，可被搜索索引。与视觉描述分开展示。

### 视频多帧采样（Multi-Frame Sampling）

对视频均匀提取 N 帧（默认 1 帧），每帧走一次视觉分析（含 OCR）。所有帧的标签合并去重后作为视频的 AI 标签，首帧描述作为视频的 AI 描述。

### 文本分析（Text Analysis）

本地模型对文档内容进行摘要和关键词提取。

### AI 分析队列（AI Queue）

AI 分析异步执行的任务队列。扫描时分析任务入队，后台线程串行消费。状态流转：pending → processing → done / failed。素材卡片在分析期间显示「AI 分析中...」。

重试策略：单次失败后在当前循环内立即重试（最多 3 次），重试间隔 2 秒。3 次全部失败后状态变为 failed，不再自动重试。用户可通过详情面板的「重试」按钮手动将 failed 任务重置为 pending。

请求超时可配置：通过 `ai.timeout` 控制每个 Ollama 请求的超时秒数（默认 300s），在 Web UI 设置面板或 `config.yaml` 中修改。

### AI 状态显示（AI Status Display）

素材网格视图和列表视图中展示 AI 分析的文字状态（等待分析 / 分析中... / 已完成 / 失败），无 AI 任务的素材不显示。详情面板 AI 状态行在失败时显示「重试」按钮。

### 标签确认（Tag Confirmation）

AI 生成的标签以虚线边框展示。用户点击确认后变为实线，来源从 auto 变为 manual。用户可移除不需要的 AI 标签。

### 语音转录（Speech Transcription）

对视频和音频文件使用 whisper 模型（faster-whisper, small）将语音转为文字。转录原文存储在 transcript 字段，可被全文搜索索引。

视频素材始终入队转录任务。transcriber 检测到无音轨时直接标记 done（不报错、不阻塞），不产生转录结果。

### 语音分析（Speech Analysis）

基于语音转录文本，通过 Ollama 提取主题标签和内容摘要。语音标签以虚线边框展示（同 AI 视觉标签）。语音摘要存入 ai_summary 字段。

### 视频综合总结（Video Combined Summary）

对视频素材，在语音分析和画面分析都完成后，将语音摘要与视觉描述/标签融合，通过一次 Ollama 调用生成视频的综合总结。结果存入 video_summary 字段。

### 重新分析（Re-Analysis）

手动触发素材的 AI 分析重新执行。支持单个素材重新分析和批量重新分析（网格/列表视图多选模式）。重新分析时所有分析任务（视觉/语音/文本）重新入队。素材记录最近一次分析完成时间（analyzed_at 字段）。

### AI Prompt 配置（AI Prompt Configuration）

AI 分析使用的 prompt 模板通过 `~/.asset-manager/prompts.yaml` 配置。包含分析/聚合/搜索三种类别共 10 个类型，每个类型结构：

- `system_format` — 系统固定追加的 JSON 格式指令，不可通过 UI 编辑
- `default` — 默认 prompt 模板（编号示例格式，用户可参考修改）
- `custom` — 用户当前的自定义 prompt，非空时优先于 default
- `presets` — 预定义的 prompt 模板列表，用户可选作自定义起点

**Prompt 生效逻辑：**
```
custom 非空 → custom + system_format
custom 为空 → default + system_format
```

**配置持久化：**
- `prompts.yaml` 首次启动时从 `DEFAULT_PROMPTS` 自动生成
- 后续启动时更新系统字段（default / system_format / presets），保留用户字段（custom）
- custom 为空字符串时视为未设置，等效于用 default

**JSON 解析：**
- 所有分析类型的 system_format 要求 LLM 输出 JSON
- 解析器提取 markdown 代码块或 `{...}` 中的 JSON
- 解析失败时返回空结果（无 regex 回退）

**Ollama 调用：**
- `think: false` 放在请求顶层关闭思考过程，返回无 `thinking` 字段，速度提升 20x+
- 当前使用 `think: true`（思考过程开启），输出更稳定但较慢
- `[Ollama prompt]` 和 `[Ollama]` 日志打印每次调用的完整请求/响应

**重新分析：**
- 清除旧的 ai_description / ocr_text / ai_summary / transcript / video_summary
- 删除旧 auto 标签后重新入队，手动标签不受影响
- AI 状态优先取 ai_queue 状态，无队列时检查 ai_description/ai_summary 判断是否已完成

### Provider（模型提供方）

AI 模型的服务来源。通过不同协议适配器调用：

- **Ollama** — 本地模型，`/api/chat` 协议，支持图片 base64
- **OpenAI 兼容** — 远端模型，`/v1/chat/completions` 协议，一套适配器覆盖 OpenAI / DeepSeek / OpenRouter / MiniMax
- **Anthropic**（未来）— `/v1/messages` 协议，独立适配器
- Provider 配置（名称/URL/Key）在模型管理页面管理，Key 存 `.env`，URL 存 `config.yaml`
- Provider 添加/删除即时保存，任务模型绑定手动保存
- AIWorker 每个任务重新读取磁盘配置，修改绑定无需重启
- 日志格式 `[provider] model=xxx` → `[provider prompt] ...` → `[provider] response`

### 模型目录（models.yaml）

`quickmedia/models.yaml` 为出厂模型目录，首次启动复制到 `~/.asset-manager/`，后续升级合并。按 provider 组织，每个 provider 包含 URL 和模型列表（名称+能力标注）。当前 5 个 provider 共 26 个模型。

Provider 配置在 `config.yaml` 的 `providers` 字段（URL + 模型列表），API Key 存在 `~/.asset-manager/.env`。按协议分类而非按公司分类。

### Task Model Binding（任务模型绑定）

将 AI 任务类型（vision / text / speech / video_summary / search_ai / aggregation）绑定到具体 provider + model。配置在 `config.yaml` 的 `task_models` 字段。search_ai 为 V15 新增的搜索任务类型，aggregation 为 V16 新增的聚合任务类型。

### Model Capabilities（模型能力）

标注模型支持的分析类型，用于设置面板下拉筛选可选模型。定义在 `quickmedia/models.yaml`（随项目发布），capabilities 包括：vision / text / speech。首次启动自动复制到 `~/.asset-manager/models.yaml`，升级时合并新增。

### think 参数

Ollama 请求顶层的布尔参数，控制是否输出思考过程。`think: false` 关闭后响应速度提升 20x+，无 `thinking` 字段。当前使用 `think: true`，输出更稳定。

### Embedding（向量化）

将文字内容转换为固定维度的向量（数字数组），使语义相似的文本在向量空间中距离更近。用于实现语义搜索和相似素材推荐。不同 embedding 模型的向量维度不同，不能混用。

### ChromaDB

轻量级开源向量数据库。`pip install chromadb` 即可安装，内嵌模式零配置，数据存本地文件。用于存储和查询素材的 embedding 向量。

### 语义搜索

通过 embedding 向量计算用户查询与素材内容的余弦相似度，找到语义相关的素材（例如搜"蓝色系"能找到蓝色调的图片，不需要精确匹配标签或文件名）。

### 搜索模式

- **AI** — 纯 LLM 单次调用，将全量素材（id+filename+type+tags）与用户自然语言查询一起送入模型，由模型直接返回相关 asset_ids。不经过关键词索引或向量检索。需要单独配置模型（task_models.search_ai），未配置时不可用（红点标记，默认回退到语义（K聚合））
- **语义（K聚合）** — 关键词匹配 + 语义搜索 RRF 融合排序
- **语义（纯向量）** — 纯 embedding 向量相似度搜索，不做关键词融合
- **关键词** — jieba 中文分词后的关键词 LIKE 搜索，按匹配度排序

默认搜索模式：AI 搜索（若已配置模型），否则语义（K聚合）。

### RRF（Reciprocal Rank Fusion）

融合多个排序列表的算法：`score = Σ 1/(60 + rank_i)`。不依赖原始分数绝对值，只关心相对排名。用于合并 BM25 关键词排名和语义向量排名。

### jieba 分词

轻量中文分词库（`pip install jieba`）。将中文查询文本拆分为语义 token，用于关键词搜索的 LIKE 匹配。

### 分字段向量化

每个素材存储 3 个独立向量：description（描述+摘要）、tags（标签名）、text（OCR/转录/文件名）。搜索时各字段分别查询，取最小距离（best-field）作为最终得分。

### search_terms（搜索词）

AI 分析输出的额外字段，专注检索意图。与 tags 不同：tags 描述内容（"狗、室内、地板"），search_terms 预判用户搜索行为（"宠物、小狗、家庭、家居、毛绒"）。每个词存独立向量，不展示给用户。v9 中 embedding 将 tags 与 search_terms 合并去重后统一向量化。

### ⭐ 重要匹配标记

语义搜索结果中，距离在第1名3倍以内且同时被关键词命中的素材，加金色星星标记。星数按距离比递减：≤1x→★★★★★，≤1.5x→★★★★，≤2x→★★★，≤2.5x→★★，≤3x→★。

### 搜索-筛选联动

v9 新增：综合/语义搜索结果基础上，侧栏筛选（类型/格式/AI状态/标签/日期）原地过滤，不重新调接口。

### 状态实时轮询

素材列表每3秒刷新处理中/待处理状态，详情面板每5秒全量刷新。批量/单文件重新分析后不刷新全列表。

### 文档预览

文档素材缩略图区显示前3行文字（TXT/MD/DOCX），格式筛选列表从 config 动态获取。

### Top-K 聚合

向量检索时，素材的 N 个 search_term 向量分别查询，取距离最小的 K 个求平均分。K 值可配，默认 2。

## V10 — 可配置扫描文件夹（新增术语）

### watch_paths

`config.yaml` 中配置的扫描目录数组。每条含 name/path/recursive/max_depth/enabled。v10 升级为结构体（之前为简单字符串数组），启动时自动迁移。

### showDirectoryPicker

浏览器原生 API，弹出系统文件夹选择控件。选中后获得持久化 FileSystemDirectoryHandle。v10 首次配置时自动调用。

### osascript choose folder

macOS AppleScript 命令，服务端拉起 Finder 文件夹选择对话框，返回 POSIX 真实路径。v10 作为文件夹选择的第二条通道。

### 热加载（watcher.reload）

保存配置后调用 watchdog Observer 的重启逻辑，新扫描路径即时生效，不需重启整个服务。

### 红点提示

设置入口指示灯——缺模型配置或缺文件夹路径时亮红点。Tab 红点独立，各自保存后消除。总红点需两项全部完成才消。


## V11 — MCP 对话式素材管理（新增术语）

### MCP（Model Context Protocol）

Anthropic 制定的 AI Agent 工具调用协议。Hermes 内置 MCP 客户端，QuickMedia 实现 MCP server 端。通过 stdio 传输，Hermes 启动时 spawn QuickMedia 子进程，自动发现工具并注册。

### mcp Python 库

，MCP 协议的 Python 实现。QuickMedia 用它实现 server 端（ 装饰器），Hermes 用它做客户端。

### quickmedia mcp

新增 CLI 子命令。启动 MCP server 进程，监听 stdio，向 Hermes 暴露 6 个素材管理工具。Hermes 配置：。

### QUICKMEDIA_HOME

环境变量，指定数据目录。默认 。MCP server 和 Web 版共享。

## V12 — 素材聚合（Aggregation）

### 聚合节点（Aggregation Node）

素材的语义分组单元。AI 分析全库素材内容后自动生成。每个节点有名称（name）和描述（description），可手动编辑。节点与素材为多对多关系：一个素材可以属于多个节点，一个节点包含多个素材。

### 聚合模式（Aggregation Mode）

三种手动触发的模式：

- **全量分析（full）** — 忽略已有节点，从零重新分析全库素材，生成全新节点和关联。适合初始聚合或彻底重建。
- **全量追加（full_append）** — 带已有节点关系 + 全量素材，AI 可以：增加新节点、追加素材到已有节点、修改已有节点关系。适合发现新聚合主题。
- **追加分析（append）** — 仅将新素材（未分配）分配到已有节点，不修改节点列表。轻量快速。

三种模式均由用户手动触发，无自动逻辑。Prompt 由函数根据 mode 参数组合，AI 不感知 mode。

### 聚合 Worker（Aggregation Worker）

独立的后台进程，使用独立的 SQLite 队列表（aggregation_queue），与现有 AI 分析队列（ai_queue）完全隔离。串行处理聚合任务，同一时间只允许一个任务，有任务运行时拒绝新提交。无自动重试，失败直接标记失败。

### 聚合任务状态

两种状态：分析中 / 完成。前端节点面板顶部黄色横幅显示状态。失败显示红色错误信息。通过轮询（~3s）检测完成。

### 节点素材关联（Node-Asset Relationship）

`node_assets(node_id, asset_id)` 多对多关联表。素材删除时级联清理关联记录。节点删除时素材变为未分配（不删素材）。

### 聚合粒度

中粒度（~10-30 个节点），按主题区分：猫的行为、狗的日常、家居收纳、购物记录、项目文档等。

### 聚合模型

通过 `task_models.aggregation` 配置 provider + model。未配置时聚合任务执行失败。

### 节点交互

- 左键点击节点 → 右侧素材面板显示节点关联素材（复用现有素材列表）
- 右键节点 → 弹出菜单：重命名、编辑描述、删除节点、手动添加素材
- 手动添加素材 → 弹出搜索框 + 全量素材列表（多选勾选 + 确认）
- 节点列表按素材数降序排列

### 侧边栏 Tab

侧边栏顶部增加 Tab 切换：
- Tab 1：搜索与筛选（现有功能）
- Tab 2：聚合节点（NodePanel 组件）

### 聚合 Prompt 配置

四种聚合 prompt 模板（full / full_append / append / analyze_append）迁入 `prompts.yaml`，与 vision/text/search_ai 等相同 custom/default/system_format 结构。模板可用占位符：`{assets}` 素材列表、`{nodes}` 已有节点、`{node_name}` 节点名、`{node_description}` 节点描述、`{existing_assets}` 已有素材摘要、`{candidates}` 候选素材。设置面板 AI 提示词 Tab 分为三组：分析 / 聚合 / 搜索。

### 代码组织

- 后端：`quickmedia/aggregation/` 子包（api.py / prompts.py / worker.py）
- 前端：`NodePanel.tsx` + `AddAssetModal.tsx`
- **架构演变**：最初设计为独立 Worker 进程轮询队列，后简化为 daemon 线程按需执行。`aggregation_queue` 仅用于状态追踪和防重复提交。

### 聚合线程（Aggregation Thread）

API 接收请求后 spawn daemon 线程执行，不再使用常驻后台 Worker。线程执行完自动结束。使用 `OpenAIAdapter.chat()` / `OllamaAdapter.chat()` 复用现有 AI 调用层。

### 追加分析空素材跳过

append / full_append 模式下，如果所有素材已全部分配到节点（unassigned=0），跳过 AI 调用直接标记 done。

### 扫描弹窗（Scan Popup）

侧边栏底部"扫描新素材"按钮点击弹出三个选项：
- 扫描配置路径 — 原有行为，POST /api/scan
- 选择文件 — macOS Finder 选文件 → POST /api/file-picker → POST /api/scan-file
- 选择文件夹 — macOS Finder 选文件夹 → POST /api/folder-picker → POST /api/scan-folder

### Scanner 重构（_ingest_file）

提取 `_insert_asset()` 和 `_ingest_file()` 两个公共方法，`scan_directory` 和 `scan_file` 共享同一入库逻辑。`_ingest_file` 三道防线：inode 匹配 → 哈希匹配 → 新增入库。

修复 `scan_file` 4 个历史 bug：`hash_file` 函数不存在 / `_os.time()` / INSERT 列名 `ext`→`extension` / `indexed_at`→`scanned_at`。

## V13 — 云图（Graph View）

### 云图（Graph View）

素材-节点关系的可视化网络拓扑图。占据主内容区（当前网格/列表位置），与网格/列表通过三按钮 Toggle 切换（☁ 云图 | ▦ 网格 | ☰ 列表）。

### API：GET /api/graph

新增端点，一次性返回全量节点-素材-关联关系，避免 N+1 请求：

```
{
  "nodes": [{"id": N, "name": "...", "asset_count": N, ...}],
  "edges": [{"node_id": N, "asset_id": N}, ...],
  "unassigned": [{"id": N, "filename": "...", "asset_type": "..."}, ...]
}
```

后端 `JOIN node_assets` + `NOT IN` 查未分配，返回最小字段集（ID、名字、类型）。

### 未分配节点（Unassigned Node）

前端虚拟构造的节点，数据库中不存在。`/api/graph` 返回 `unassigned` 素材列表，前端渲染时生成一个 "未分配" 节点并连线所有未分配素材。

- 视觉区分：灰色/虚线边框，和聚合节点不同颜色
- 无聚合节点时：云图自动显示"未分配"节点 + 全部素材

### 渲染方案

Cytoscape.js，npm 依赖。力导向布局、拖拽、缩放、框选开箱即用。

### 节点视觉规则

**聚合节点：**
- 大小 = 素材数量，素材多的节点气泡更大
- 颜色 = 素材数量梯度（多→暖，少→冷）

**素材节点：**
- zoom < 1.5x：小圆点，按类型着色
- zoom ≥ 1.5x：放大为缩略图 + 文件名
- 颜色方案（从现有调色板衍生）：
  - 图片 `#cc785c`（珊瑚）
  - 视频 `#b05a3e`（深赭）
  - 音频 `#a09888`（暖灰）
  - 文档 `#d4c8b0`（沙色）

**图例（Legend）：** 云图右上角固定说明文字，标注节点颜色含义和素材类型颜色。

### 共享边（Shared Edge）

两个聚合节点共享素材时生成的边，粗细 = 共享素材数量。

### 交互行为

- 单击节点 → 选中（绑定 `selectedNodeId`），素材列表筛选该节点素材
- 双击节点 → 展开/折叠素材节点，展开状态跨视图保留
- 单击素材节点 → 打开详情面板（和网格/列表行为一致）
- 单击空白区域 → 取消选中节点
- 📌 清除条 → 跨视图统一清除入口
- 缩放控件：左下角 +/− 按钮 + 居中复位 + 🔄 重新加载（手动拉取数据全量重绘）

### 搜索高亮

搜索后云图中匹配的素材/节点高亮，不匹配的半透明灰色弱化，保持全局布局不变。搜索框在侧边栏搜索筛选 Tab，两个 Tab 共用。

### 初始视口

全量全景，所有节点居中缩放到适配屏幕。

### 聚合运行时的实时更新

WebSocket 推送事件：后端数据变更（聚合完成、节点增删改、素材关联变化）→ 推送 `graph_changed` → 前端调 `GET /api/graph` → 增量重绘。保留当前视口位置和 zoom，保留仍存在的展开节点，仅更新连线和新增/删除节点。

### 素材展开

默认仅显示聚合节点，单击节点展开/折叠素材节点。素材节点无数量上限，力布局自然散开，zoom 自适应渲染保证可读性。

### 无聚合节点时

云图自动显示"未分配"节点 + 全部素材，不显示空状态提示。

## V14 — 节点增强（新增术语）

### 节点分析追加（Node Analyze-Append）

对单个聚合节点，AI 分析全库中未连接到此节点的所有素材，自动将匹配素材添加到该节点。与聚合追加（append mode）不同：
- 聚合追加是**全局视角**，仅处理未分配素材
- 节点分析追加是**单节点视角**，范围为全库所有未连接到此节点的素材（可跨节点）

触发方式：右键节点 → "分析追加到此节点"。执行期间节点行右侧显示旋转菊花指示器，hover 提示"分析中"。

### 手动移除素材（Remove Assets from Node）

从聚合节点中移除已有素材。右键节点 → "手动移除素材"，弹出搜索弹框（复用添加素材弹框样式），多选素材后确认移除。移除后节点素材数更新，主内容区同步刷新。

### 保存并分析（Save & Analyze）

新建聚合节点时提供"保存并分析"选项：创建节点后自动对其执行分析追加，AI 匹配全库未连接素材。适用于快速创建并一次性填充节点。

## V13 补充 — 云图视觉增强

### 节点素材计数

聚合节点和未分配节点圆圈内显示素材数量（白色粗体），字号随圆圈大小自适应。

### 颜色深度梯度

聚合节点颜色根据素材数量变化：素材少的浅珊瑚 → 素材多的深珊瑚。通过 HSL 动态计算饱和度和亮度。

## V15 — AI 搜索 + 节点树状列表

### 节点树状列表（Node Tree List）

聚合节点侧边栏的树形展示结构。每个节点前有独立箭头控件（▶/▼），点击展开/折叠节点内素材列表。默认全部折叠。展开后按需加载素材（get_node API），显示类型图标 + 文件名。点击素材打开右侧详情面板（复用 selA）。支持拖放素材到其他树节点或云图。节点素材发生变更（拖放、手动增删、分析追加、聚合完成）时精准刷新已展开节点。

### 未分配虚拟节点（树状列表）

节点树状列表中的虚拟条目，始终位于列表末尾。展示未分配到任何聚合节点的素材数量和列表。视觉上与云图未分配节点区分（灰色/虚线风格）。可展开/折叠查看素材，支持：展开后拖出素材到其他树节点（分配），从其他节点拖入素材到此节点（取消分配），从网格/云图拖素材到此节点（取消分配）。与云图中的未分配节点共享同一数据源（/api/graph.unassigned），拖放操作通过后端幂等处理。

### AI 搜索 Prompt 配置

`search_ai` prompt 模板位于 `~/.asset-manager/prompts.yaml`，与现有分析 prompt 相同的结构（system_format / default / custom / presets）。system_format 要求 LLM 输出 `{"asset_ids": [1,5,23]}`，无匹配返回 `{"asset_ids": []}`。prompts.yaml 首次启动自动从 DEFAULT_PROMPTS 生成，后续升级合并系统字段、保留用户 custom。\n\n## V17 — 国际化 (i18n)\n\n### 显示语言\n\nQuickMedia 支持简体中文 (zh) 和英文 (en)。首次访问时根据浏览器语言自动选择：简体/繁体中文 → 简体中文，其他 → 英文。用户可在设置面板"基础"Tab 手动切换，选择持久化在 localStorage。\n\n### Locale 文件\n\n前端翻译文本统一存放在 `frontend/src/locales/{lang}.json`，按模块内嵌命名空间。使用 react-i18next 加载。\n\n### 多语言 Prompt 模板\n\n`DEFAULT_PROMPTS` 拆分为中文 (`DEFAULT_PROMPTS_ZH`) 和英文 (`DEFAULT_PROMPTS_EN`) 两套，PromptConfig 初始化时根据语言选择对应 default 值。用户自定义 custom 不受语言切换影响。\n\n### 后端消息\n\n后端 API 不直接输出用户可见文字。错误和提示通过结构化字段返回，前端按当前语言翻译显示。\n\n### README\n\n`README.md` 为英文默认版本，`README.zh.md` 为中文版本。两份互相链接。

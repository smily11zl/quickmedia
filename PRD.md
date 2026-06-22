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

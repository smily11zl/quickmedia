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

AI 分析使用的 prompt 模板通过 `~/.asset-manager/prompts.yaml` 配置。包含四个分析类型（vision / text / speech / video_summary），每个类型结构：

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

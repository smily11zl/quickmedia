# QuickMedia v2 PRD

## Problem Statement

v1 的 AI 分析覆盖了核心场景（图片描述+标签、视频首帧、文档摘要），但存在三个缺口：

1. **图片中的文字无法被检索** — 截图是设计/开发工作中最常用的素材类型，但截图中包含的关键文字（按钮文案、错误信息、菜单项）无法被搜索。用户搜「WARNING」找不到那张包含警告信息的截图。

2. **视频分析只有首帧** — 一段 10 分钟的视频，用户可能在第 3 分钟才进入主题，但首帧只是开场的黑色画面。单帧代表不了视频的实际内容。

3. **AI 分析阻塞扫描** — v1 的 AI 分析是同步的，扫描一张图要等 AI 返回结果才能处理下一张。素材量大时，扫描体验差。

## Solution

v2 主攻 AI 分析增强：

- **OCR 文字提取** — 复用 Qwen 3.5 视觉模型的文字识别能力，在图片分析 prompt 中加入 OCR 指令。提取的文字独立存储，可被搜索。
- **视频多帧采样** — 均匀取 5 帧（首帧、尾帧、中间 3 帧），每帧走视觉分析+OCR。标签合并去重，首帧描述作为视频封面说明。
- **AI 异步化** — 仿照缩略图队列模式，AI 分析任务入队后台消费。扫描不阻塞，分析结果逐步到位。

附带以下体验改善：

- **搜索结果高亮** — 匹配关键词在列表中用珊瑚色标记
- **Finder 按钮** — 详情面板路径旁加文件夹图标，点击打开 Finder 定位
- **AI 重试按钮** — 失败任务的详情面板显示「重试」按钮，手动触发重新分析
- **AI 状态显示** — 网格和列表视图显示 AI 分析的文字状态
- **超时配置** — 设置面板可配置 Ollama 请求超时（默认 180s）
- **缩略图缓存破坏** — URL 携带修改时间戳参数，避免浏览器缓存旧缩略图

## User Stories

1. As a 设计师，I want 搜索截图中包含的按钮文字或错误信息，so that 我能从几百张截图中快速定位到需要的那张。

2. As a 视频编辑，I want 看到视频多帧的标签摘要（不只是首帧），so that 长视频也能获得准确的内容标签。

3. As a 用户，I want 扫描素材时不卡在 AI 分析上，so that 大量素材也能快速入库。

4. As a 素材管理者，I want 在搜索结果中一眼看到关键词高亮，so that 我能判断搜索结果的相关性。

5. As a macOS 用户，I want 点击素材详情中的文件夹图标直接打开 Finder 定位文件，so that 不需要手动拼路径。

6. As a 管理员，I want 在设置页配置视频采样帧数，so that 我能根据模型性能和素材数量调整分析深度。

7. As a 用户，I want AI 分析失败后能一键重试，so that 不需要手动改数据库。

8. As a 用户，I want 在网格和列表中看到每个素材的 AI 分析状态，so that 一眼就能知道哪些素材的分析有问题。

## Implementation Decisions

### OCR 文字提取

- 在 VisionAnalyzer 的图片分析 prompt 中追加 OCR 指令
- 响应解析新增「文字：」段提取
- 提取的文字存入新字段 ocr_text
- 搜索索引覆盖 ocr_text
- 详情面板展示 OCR 文字（在 AI 描述下方）

### 视频多帧采样

- 均匀采样 N 帧（默认 5 帧，在设置页可配置）
- 每帧走一次视觉分析（含 OCR）
- 所有帧的标签合并去重后作为视频的 AI 标签
- 首帧描述作为视频的 AI 描述
- 配置键：ai.video_frames（默认 5）

### AI 异步化

- 新增 ai_queue 表（结构仿照 thumbnail_queue）
- 扫描时 AI 分析任务入队，后台线程串行消费
- 状态流转：pending → processing → done / failed
- 素材卡片显示「AI 分析中...」状态

### Finder 按钮

- 详情面板路径字段旁新增文件夹图标
- 点击调用系统命令 `open -R <文件路径>`

### AI 重试按钮

- 新增 API 端点 `POST /api/assets/{id}/retry-ai`
- 将 failed 状态的 ai_queue 记录重置为 pending（attempt=0, error=NULL）
- 前端详情面板 AI 状态行，状态为 failed 时显示红色「重试」按钮

### AI 状态显示

- 列表 API `/api/assets` 返回 `ai_status` 字段（LEFT JOIN ai_queue）
- 网格视图：尺寸行后面显示灰色小字状态
- 列表视图：文件名和尺寸之间新增状态列

### 超时配置

- `ai.timeout` 控制每个 Ollama HTTP 请求的超时秒数（默认 180s）
- AIWorker 读取配置传入 VisionAnalyzer / TextAnalyzer
- Web UI 设置面板可修改，范围 30-600s

### AI 重试策略

- 单次失败后在当前 process_queue() 内立即重试（while 循环，最多 3 次）
- 重试间隔 2 秒（time.sleep(2)）
- 3 次全失败后标记为 failed，不再自动重试

### 缩略图缓存破坏

- 前端缩略图 URL 追加 `?t=<modified_at>` 参数
- 每个素材的修改时间不同，确保 Chrome 不会使用错误的缓存图片

### 搜索结果高亮

- 列表视图匹配关键词用珊瑚色（#cc785c）高亮
- 搜索范围：文件名、描述、AI 描述、AI 摘要、OCR 文字、标签名

### 数据库变更

- assets 表新增 ocr_text 列
- 新增 ai_queue 表（asset_id, task_type, status, attempt, error）

## Testing Decisions

- 新功能通过 API endpoints 验证（最高 seam）
- 搜索 API 测试覆盖 OCR 文字命中（英文 + 中文）
- 素材详情 API 验证返回体含 ocr_text 字段
- 配置 API 验证 ai.video_frames 读写
- AI 模块单元测试覆盖 OCR prompt 构造 + 响应解析
- 数据库测试覆盖 ai_queue 表结构和状态流转
- 现有 92 个测试作为回归基线，新功能不破坏已有行为

## Out of Scope

- 专用 OCR 引擎（Tesseract/PaddleOCR）
- 视频语音转录
- 音频转录
- 语义相似度搜索
- 重复文件展示
- 素材版本历史
- 已删除素材回收站
- 打包分发

## Further Notes

- v2 需求决策详见 docs/v2/plan.md
- 术语定义见 CONTEXT.md（OCR 文字提取、视频多帧采样、AI 分析队列、搜索高亮）
- roadmap 见 ROADMAP.md

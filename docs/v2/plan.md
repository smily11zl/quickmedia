# QuickMedia v2 Plan

> grill-me 需求决策记录。基于 v1 现有能力，v2 主攻 AI 分析增强 + 少量体验优化。

## 决策汇总

| # | 决策点 | 选择 |
|---|--------|------|
| 1 | 核心主题 | AI 增强：OCR、多帧采样、异步化 |
| 2 | OCR 结果存储 | 新字段 `ocr_text`，详情面板展示 |
| 3 | OCR 引擎 | Qwen 3.5 视觉 prompt 合并（不引入额外依赖） |
| 4 | 视频采样策略 | 固定帧数，均匀采样 |
| 5 | 多帧结果合并 | 标签合并去重，描述取首帧 |
| 6 | Finder 打开按钮 | 路径字段旁文件夹图标 |
| 7 | AI 异步化 | 任务队列模式（复用缩略图队列设计） |
| 8 | 采样帧数 | 默认 1 帧，设置页可配置 |
| 9 | OCR prompt | 与图片视觉分析 prompt 合并为单个调用 |
| 10 | 搜索高亮 | 列表视图中关键词珊瑚色高亮 |
| 11 | AI 队列状态 | 素材卡片显示「AI 分析中...」状态 |
| 12 | 体验优化 | 重复文件展示、版本历史、回收站延迟到后续 |
| 13 | 文档分析 | v1 已有，不重复 |

## 功能列表

### 1. OCR 文字提取

- 在 VisionAnalyzer 的图片分析 prompt 中追加 OCR 指令
- 响应解析增加「文字：」段落提取
- 提取的文字存入新字段 `ocr_text`（assets 表新增列）
- 搜索索引覆盖 ocr_text 字段
- 详情面板展示提取的文字（在 AI 描述下方）

### 2. 视频多帧采样

- 扫描视频时，提取 N 帧（默认 1 帧，可配置）
- 每帧走一次视觉分析（含 OCR）
- 所有帧的标签合并去重后作为视频的 AI 标签
- 首帧描述作为视频的 AI 描述
- 配置项：`ai.video_frames`（默认 5）

### 3. AI 分析异步化

- 新增 `ai_queue` 表（类似 `thumbnail_queue`）
- 扫描时 AI 分析任务入队，后台线程串行消费
- 状态流转：pending → processing → done / failed
- 素材卡片缩略图区域显示「AI 分析中...」状态
- 扫描不阻塞，分析结果逐步到位

### 4. Finder 打开按钮

- 详情面板路径字段旁增加文件夹图标按钮
- 点击调用 `open -R <文件路径>`（macOS）

### 5. 搜索结果高亮

- 列表视图下，匹配到的关键词用珊瑚色（#cc785c）高亮
- 搜索字段覆盖：文件名、描述、AI 描述、AI 摘要、OCR 文字、标签名

### 6. 视频帧数配置

- 设置页新增「视频采样帧数」配置项
- 默认 5，可修改
- 存储于 `ai.video_frames` 配置键

## 数据库变更

### assets 表新增列

```sql
ALTER TABLE assets ADD COLUMN ocr_text TEXT;
```

### 新增 ai_queue 表

```sql
CREATE TABLE ai_queue (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id  INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    task_type TEXT NOT NULL,  -- 'vision' | 'ocr' | 'frame'
    status    TEXT DEFAULT 'pending',
    attempt   INTEGER DEFAULT 0,
    error     TEXT,
    created   TEXT DEFAULT (datetime('now'))
);
```

## 配置变更

```yaml
ai:
  ollama_url: http://localhost:11434
  model: qwen3.5:9b
  video_frames: 5   # 新增
```

## 实现顺序

1. OCR 文字提取（ai.py prompt 扩展 + ocr_text 字段 + 解析）
2. 视频多帧采样（scanner.py 多帧逻辑 + 标签合并去重）
3. AI 异步队列（ai_queue 表 + 后台线程 + 状态显示）
4. Finder 按钮（前端 UI）
5. 搜索高亮（前端 UI）
6. 视频帧数配置（设置页 + 配置读写）

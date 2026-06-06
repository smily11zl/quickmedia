# QuickMedia v2 技术方案

> 基于 v1 技术架构（docs/v1/design.md）的增量设计。

## 变更范围

| 模块 | 变更类型 | 说明 |
|------|---------|------|
| ai.py | 扩展 | VisionAnalyzer prompt 追加 OCR 指令，响应解析新增「文字：」 |
| scanner.py | 扩展 | 视频多帧采样逻辑，AI 调用改为入队 |
| database.py | 扩展 | schema 迁移（ocr_text 列、ai_queue 表），搜索覆盖 ocr_text |
| thumbnailer.py | 复用模式 | ai_queue 结构仿照 thumbnail_queue |
| server.py | 扩展 | 素材详情返回 ocr_text，配置 API 支持 video_frames |
| App.tsx | 扩展 | OCR 文字展示、Finder 按钮、搜索高亮、AI 分析状态、帧数配置 |
| config.py | 扩展 | DEFAULT_CONFIG 新增 ai.video_frames |

## 数据库变更

### assets 表新增列

```sql
ALTER TABLE assets ADD COLUMN ocr_text TEXT;
```

### 新增 ai_queue 表

```sql
CREATE TABLE IF NOT EXISTS ai_queue (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id  INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    task_type TEXT NOT NULL,           -- 'vision' | 'frame'
    status    TEXT DEFAULT 'pending',  -- pending | processing | done | failed
    attempt   INTEGER DEFAULT 0,
    error     TEXT,
    created   TEXT DEFAULT (datetime('now'))
);
```

与 thumbnail_queue 的差异：多了 `task_type` 字段区分图片分析和视频帧分析。

## AI 分析变更

### VisionAnalyzer prompt 扩展

原有 prompt 追加：

```
如果图片中有文字，请识别并以逗号分隔输出。

输出格式：
描述：<描述文本>
标签：<标签1>, <标签2>, <标签3>, ...
文字：<文字1>, <文字2>, <文字3>, ...
```

### 响应解析扩展

`_parse_response` 新增文字提取：

```python
ocr_match = re.search(r"文字[：:]\s*(.+)", text)
if ocr_match:
    ocr_text = ocr_match.group(1).strip()
```

### 图片分析调用流程（v2）

```
新图片入库
    │
    ▼
1. 缩略图入队（thumbnail_queue）
    │
    ▼
2. AI 分析入队（ai_queue，task_type='vision'）
    │
    ▼
3. 后台线程消费 ai_queue
   ├─ PIL 读取 → 缩放 → base64
   ├─ 发送 Ollama（含 OCR prompt）
   ├─ 解析：description + tags + ocr_text
   ├─ 入库：ai_description, ocr_text, ai_tags
   └─ 状态标记：done / failed
```

## 视频多帧采样

### 采样策略

- 默认 N = 1 帧
- 采样位置：uniformly distributed（帧数 / (N+1) 作为间隔）
- 位置 1 = 首帧（时长 0 秒）
- 位置 2-4 = 等间隔采样
- 位置 5 = 尾帧

### 视频分析调用流程

```
新视频入库
    │
    ▼
1. 缩略图入队（thumbnail_queue）
    │
    ▼
2. ffprobe 提取总帧数/时长
    │
    ▼
3. 计算 N 个采样帧的时间点
    │
    ▼
4. 每个采样帧：
   ├─ ffmpeg 提取帧 → 临时 jpg
   ├─ AI 分析入队（ai_queue，task_type='frame'）
   └─ 关联到同一 asset_id
    │
    ▼
5. 后台线程消费该视频的所有帧任务：
   ├─ 收集所有帧的标签 → 合并去重
   ├─ 首帧描述 → 写入 ai_description
   ├─ 合并后标签 → 写入 asset_tags（source='auto'）
   └─ OCR 文字合并去重 → 写入 ocr_text
```

### 标签合并去重规则

```python
all_tags = set()
all_ocr = set()
first_desc = None

for frame_result in frame_results:
    if first_desc is None:
        first_desc = frame_result["description"]
    all_tags.update(frame_result["tags"])
    all_ocr.update(frame_result["ocr_text"])

# 入库
ai_description = first_desc
tags = list(all_tags)
ocr_text = ", ".join(all_ocr)
```

## 异步队列设计

### 架构

```
Scanner
    │
    ├─→ thumbnail_queue → Thumbnailer.process_queue() → 缩略图
    │
    └─→ ai_queue → AIWorker.process_queue() → Ollama → ai_description / ocr_text / ai_tags
```

### AIWorker 类

```python
class AIWorker:
    """后台消费 ai_queue，调用 Ollama 进行 AI 分析。"""

    MAX_RETRIES = 3

    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config
        timeout = config.get("ai.timeout") or 300
        self._vision = VisionAnalyzer(timeout=timeout, ...)
        self._text = TextAnalyzer(timeout=timeout, ...)

    def enqueue(self, asset_id: int, task_type: str) -> None:
        """将任务入队（幂等）。"""

    def process_queue(self) -> int:
        """消费所有 pending 任务。每个任务在 while 循环内最多
        重试 MAX_RETRIES 次，重试间隔 2 秒。3 次全失败标记 failed。"""
```

### 重试策略

失败后在当前 process_queue() 内立即通过 while 循环重试，不再延迟到下次轮询。每次重试间隔 2 秒，避免锤 Ollama。

### 超时配置

- 配置键 `ai.timeout`（默认 300s），控制每个 Ollama HTTP 请求的超时
- VisionAnalyzer / TextAnalyzer 构造函数接受 timeout 参数
- AIWorker 从配置读取并传入分析器
- Web UI 设置面板可编辑（范围 30-600s）

### 与 Thumbnailer 的复用

两者共享相同的队列模式：
- `enqueue()` — 幂等入队
- `process_queue()` — 批量消费
- 状态字段：status（pending/processing/done/failed）
- 错误字段：error, attempt

## API 变更

### 素材详情响应新增字段

```json
GET /api/assets/:id
{
  ...
  "ocr_text": "WARNING: Danger, OK, Cancel",
  "ai_status": "done"   // 新增：AI 分析状态
}
```

### 配置 API

```json
GET /api/config
{
  "ollama_url": "...",
  "model": "qwen3.5:9b",
  "video_frames": 1,
  "timeout": 300
}

PUT /api/config
{
  "video_frames": 3,
  "timeout": 300
}
```

### AI 重试 API

```
POST /api/assets/{id}/retry-ai
→ 将 failed 的 ai_queue 重置为 pending（attempt=0, error=NULL）
→ 200 {"ok": true} 或 404（无失败任务）
```

### 素材列表 API

```
GET /api/assets
→ items[] 新增 ai_status 字段
   通过 LEFT JOIN ai_queue 获取最新状态
   （done / processing / pending / failed / "-"）
```

## 前端变更

### OCR 文字展示

详情面板 AI 描述下方新增 OCR 文字区：

```
<div>
  <div className="text-[11px]">OCR 文字</div>
  <p className="text-xs">{selected.ocr_text}</p>
</div>
```

### Finder 按钮

路径字段旁新增文件夹图标：

```
路径 [📂] ← 点击执行 open -R <路径>
```

前端通过 `fetch('/api/finder/open', {method:'POST', body: JSON.stringify({path})})` 调用，后端新增端点执行 `subprocess.run(['open', '-R', path])`。

### 搜索高亮

列表视图中，对匹配的关键词进行标记。前端在渲染时根据搜索词做文本分割，匹配部分用珊瑚色样式。

### AI 分析状态

素材卡片缩略图区域，当 ai_status 为 pending 或 processing 时显示「AI 分析中...」动画。

网格视图和列表视图均显示 AI 分析的文字状态（等待分析 / 分析中... / 已完成 / 失败）。无 AI 任务的素材不显示状态标记。

详情面板 AI 状态行在状态为 failed 时显示红色「重试」按钮，点击调用 `POST /api/assets/{id}/retry-ai` 手动触发重新分析。

### 视频帧数配置

设置页新增输入项：

```
视频采样帧数: [1] ← 数字输入
请求超时(秒): [300] ← 数字输入（范围 30-600）
```

### 缩略图缓存破坏

缩略图 URL 携带 `?t=<modified_at>` 参数，避免 Chrome 浏览器缓存旧缩略图。

## 测试策略

| 层级 | 测试内容 | 文件 |
|------|---------|------|
| API | ocr_text 字段返回、搜索命中 OCR、配置 video_frames | test_api.py |
| AI 模块 | OCR prompt 构造、响应解析含文字段 | test_ai.py |
| 数据库 | ai_queue 表结构、状态流转、schema 迁移 | test_database.py |
| 扫描器 | 视频多帧提取、标签合并去重 | test_scanner.py |

所有新增测试先 RED，再 GREEN。

# QuickMedia v2 Tasks

> to-issues 输出。基于 docs/v2/plan.md 和 PRD.md。
> ✅ = 已完成，所有切片已交付。

## 依赖关系

```
Slice 2.1 (OCR)
  ├─→ Slice 2.2 (多帧采样)
  └─→ Slice 2.3 (异步队列)

Slice 2.4 (搜索高亮) — 独立
Slice 2.5 (Finder + 配置) — 独立
Slice 2.6 (重试 + 状态显示) — 独立，基于 Slice 2.3
Slice 2.7 (超时配置 + 缓存破坏) — 独立
```

---

## Slice 2.1: OCR 文字提取 ✅

- **类型**: AFK
- **阻塞**: 无
- **测试 seam**: API 层 — 搜索命中 OCR 文字，详情返回 ocr_text

### 任务清单

- [x] VisionAnalyzer prompt 追加 OCR 指令
- [x] 响应解析新增「文字：」段提取
- [x] assets 表新增 ocr_text 列（schema 迁移）
- [x] 扫描时 OCR 文字存入 ocr_text 字段
- [x] 搜索索引（database.search）覆盖 ocr_text
- [x] 详情面板展示 OCR 文字（在 AI 描述下方）

---

## Slice 2.2: 视频多帧采样 ✅

- **类型**: AFK
- **阻塞**: Slice 2.1
- **测试 seam**: API 层 — 视频素材标签来自多帧；配置 API 返回 video_frames

### 任务清单

- [x] 视频扫描时用 ffmpeg 提取 N 帧（默认 1，可配置）
- [x] 每帧走视觉分析 + OCR
- [x] 所有帧的标签合并去重
- [x] 首帧描述作为视频 AI 描述
- [x] 配置项 ai.video_frames（默认 1）

---

## Slice 2.3: AI 分析异步化 ✅

- **类型**: AFK
- **阻塞**: Slice 2.1
- **测试 seam**: 模块层 — ai_queue 表操作，状态流转

### 任务清单

- [x] 新增 ai_queue 表（同 thumbnail_queue 模式）
- [x] 扫描时 AI 分析任务入队（替代同步调用）
- [x] 后台线程串行消费队列
- [x] 状态流转：pending → processing → done / failed
- [x] 素材卡片显示「AI 分析中...」状态

---

## Slice 2.4: 搜索结果高亮 ✅

- **类型**: AFK
- **阻塞**: 无
- **测试 seam**: 前端 UI 层

### 任务清单

- [x] 搜索结果列表中对匹配文本做高亮标记（珊瑚色 #cc785c）

---

## Slice 2.5: Finder 按钮 + 视频帧数配置 ✅

- **类型**: AFK
- **阻塞**: 无
- **测试 seam**: 前端 UI 层

### 任务清单

- [x] 详情面板路径旁加文件夹图标按钮
- [x] 点击调用 open -R 在 Finder 中定位
- [x] 设置页新增「视频采样帧数」输入项（默认 1）
- [x] 配置读写 ai.video_frames

---

## Slice 2.6: AI 重试 + 状态显示 ✅

- **类型**: AFK
- **阻塞**: Slice 2.3
- **测试 seam**: API 层 — retry-ai 端点；列表 API 返回 ai_status

### 任务清单

- [x] AIWorker 重试策略：while 循环立即重试（最多 3 次，间隔 2s）
- [x] POST /api/assets/{id}/retry-ai 端点（failed → pending）
- [x] 详情面板 failed 状态时显示「重试」按钮（珊瑚色）
- [x] 列表 API LEFT JOIN ai_queue 返回 ai_status
- [x] 网格视图显示 AI 状态文字（尺寸行后面）
- [x] 列表视图新增 AI 状态列

---

## Slice 2.7: Ollama 超时配置 + 缩略图缓存破坏 ✅

- **类型**: AFK
- **阻塞**: 无
- **测试 seam**: API 层 — 配置 API 读写 timeout；前端缩略图 URL

### 任务清单

- [x] VisionAnalyzer / TextAnalyzer 接受 timeout 参数
- [x] AIWorker 从配置读取 ai.timeout 传入分析器（默认 300s）
- [x] ai.timeout 替换硬编码的 120s
- [x] 设置面板新增「请求超时(秒)」输入项（范围 30-600）
- [x] 配置 API 读写 timeout
- [x] 缩略图 URL 追加 ?t= 缓存破坏参数

---

## 完成统计

| 切片 | 测试数 | 状态 |
|------|--------|------|
| 2.1 OCR | test_ai.py (14) | ✅ |
| 2.2 多帧采样 | test_video_frames.py (5), test_ai.py | ✅ |
| 2.3 异步队列 | test_ai_worker.py (5) | ✅ |
| 2.4 搜索高亮 | App.tsx | ✅ |
| 2.5 Finder | test_api.py | ✅ |
| 2.6 重试+状态 | test_api.py (2), test_ai_worker.py (3) | ✅ |
| 2.7 超时+缓存 | test_api.py + 前端 | ✅ |
| **总计** | **111 tests** | ✅ |

# QuickMedia v3 Tasks

> to-issues 输出。基于 PRD.md。全部完成 ✅

## 依赖关系

```
Slice 3.1 (语音转录)
  └─→ Slice 3.2 (语音分析)
        └─→ Slice 3.3 (视频综合总结)

Slice 3.4 (重新分析) — 独立
```

---

## Slice 3.1: 语音转录 ✅

- **类型**: AFK
- **阻塞**: 无
- **覆盖**: US-1 (搜索对话), US-6 (查看转录文本), US-7 (无音轨不报错)

### 任务清单

- [x] 安装 faster-whisper (small)，新增 TranscriptionAnalyzer 类
- [x] 数据库 v3 migration：assets 新增 transcript 列
- [x] FTS 索引覆盖 transcript
- [x] ai_queue 支持 task_type='transcribe'
- [x] Scanner：音频和视频素材扫描时入队 transcribe 任务
- [x] AIWorker.process_queue() 处理 transcribe 任务
- [x] 无音轨视频直接标记 done，不报错
- [x] API 素材详情返回 transcript 字段
- [x] 前端详情面板展示语音转录文本

---

## Slice 3.2: 语音分析 ✅

- **类型**: AFK
- **阻塞**: Slice 3.1
- **覆盖**: US-1 (搜索对话), US-3 (音频摘要)

### 任务清单

- [x] TextAnalyzer 新增语音分析 prompt（基于转录文本提取标签+摘要）
- [x] AIWorker：转录完成后自动入队语音分析任务
- [x] 语音标签以虚线边框展示（source='auto'）
- [x] 语音摘要存入 assets.ai_summary
- [x] 前端详情面板展示语音标签和摘要（音频/视频素材）

---

## Slice 3.3: 视频综合总结 ✅

- **类型**: AFK
- **阻塞**: Slice 3.2
- **覆盖**: US-2 (视频整体理解)

### 任务清单

- [x] 数据库 migration：assets 新增 video_summary 列
- [x] FTS 索引覆盖 video_summary
- [x] AIWorker：语音分析+画面分析都完成后，入队 summarize 任务
- [x] 综合总结：一次 Ollama 调用融合语音摘要+视觉描述+标签
- [x] 结果存入 assets.video_summary
- [x] API 素材详情返回 video_summary
- [x] 前端详情面板展示视频综合总结

---

## Slice 3.4: 重新分析 ✅

- **类型**: AFK
- **阻塞**: 无
- **覆盖**: US-4 (单个重新分析), US-5 (批量重新分析)

### 任务清单

- [x] 数据库 migration：assets 新增 analyzed_at 列
- [x] POST /api/assets/{id}/reanalyze — 清除现有分析结果，所有任务类型重新入队
- [x] POST /api/assets/batch-reanalyze — 批量重新分析
- [x] 素材详情面板「重新分析」按钮
- [x] 网格/列表多选模式（checkbox + 操作栏「重新分析已选」）
- [x] AI 分析完成时更新 analyzed_at
- [x] DELETE /api/assets/{id} 素材删除端点
- [x] 详情面板 🗑 删除按钮（含确认弹窗）
- [x] POST /api/scan 扫描新素材端点
- [x] 侧边栏 🔍 扫描新素材按钮

---

## 完成统计

| 切片 | 状态 |
|------|------|
| 3.1 语音转录 | ✅ |
| 3.2 语音分析 | ✅ |
| 3.3 视频综合总结 | ✅ |
| 3.4 重新分析 | ✅ |
| **总计** | **129 tests** |

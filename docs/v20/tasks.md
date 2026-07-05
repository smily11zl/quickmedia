# V20 任务切片

> 3 切片，全部完成。✅

---

### s1: 排序修复

**类型**: AFK  
**阻塞**: 无

**内容**:
- `App.tsx:146` 移除 `if(smode==="keyword")` 条件，4 模式统一排序
- 新增 `score` 排序项，仅在 `smode === "semantic" || smode === "combined"` 时显示
- 默认排序：`semantic`/`combined` → score，`keyword`/`ai` → name
- locale 加 `sort_score` / `sort_hot`

### s2: 热度系统

**类型**: AFK  
**阻塞**: 无

**内容**:
- DB migration: `ALTER TABLE assets ADD COLUMN view_count INTEGER DEFAULT 0` + `open_count`
- `GET /api/assets/{id}` → view_count+1（仅 Web 端点击详情时调）
- `GET /api/files/{id}` → open_count+1（打开原文件）
- 前端热度排序项
- DB_VERSION=20

### s3: 详情页原图缩略图

**类型**: AFK  
**阻塞**: 无

**内容**:
- `GET /api/thumbnails/{id}?quality=full` 新增参数
- 详情面板切换高质量缩略图 src
- 列表保持不变


---
### s1 补充

- 最近添加排序（scanned_at 倒序）
- 热度排序权重：open_count × 3
- 热度等同 → scanned_at 降序（新添加优先）
- 排序切换仅热度刷新，其他不变
- sort_date 改名 "按修改时间"

### s2 补充

- click 计数模式（?click=1），轮询不触发
- 打开次数权重 ×3

### s3 补充

- 视频 ffmpeg 首帧提取（800px）
- RGBA/P/CMYK → RGB 转换

# V20 设计文档

## 1. 排序修复

### 排序项

- 按热度（view_count + open_count×3，等同→scanned_at）
- 按添加时间（scanned_at 倒序）
- 按修改时间（modified_at 倒序，原名"按时间"）
- 按名称 / 按大小
- 按相关性（语义/综合模式搜索时出现）

### 排序修复


前端的排序条件错误——`App.tsx:146` 只在 `smode==="keyword"` 时执行排序。

**修复**: 移除条件包装，排序项新增 `score`（语义/综合模式出现），`hot`（新高热度排序）。

```tsx
// Current (bug)
if(smode==="keyword") fs=[...fs].sort(...)

// Fixed: no condition, always sort
fs=[...fs].sort((a,b) => {
  if(sb === "score") return (a.score || 0) - (b.score || 0);
  if(sb === "hot") return (b.view_count + b.open_count) - (a.view_count + a.open_count);
  if(sb === "size") return b.size - a.size;
  if(sb === "date") return (b.modified_at || "").localeCompare(a.modified_at || "");
  return a.filename.localeCompare(b.filename);
})
```

## 2. 热度系统

### DB 迁移

```sql
ALTER TABLE assets ADD COLUMN view_count INTEGER DEFAULT 0;
ALTER TABLE assets ADD COLUMN open_count INTEGER DEFAULT 0;
```

### 计数 API

- `GET /api/assets/{id}` — 详情请求 → view_count+1
- `GET /api/files/{id}?open=1` — 原文件打开 → open_count+1

### 前端

- 详情面板 `selA(id)` 调详情 API 后 view_count 自然 +1
- 文件路径按钮 `window.open` 后 `fetch /api/files/{id}?open=1`
- 排序下拉新增"热度"

## 3. 详情页原图缩略图

### API

`GET /api/thumbnails/{id}?quality=full` — 用原始文件生成 800px 高质量缩略图，存 `thumbnails/{id}_full.jpg`。

### 前端

列表页 `/?{id}` 不变，详情页 `/?{id}&quality=full`。


## 补充实现

- **排序公式**: `热度 = view_count + open_count × 3`，等同→`scanned_at` 优先
- **最近添加排序**: 按 `scanned_at` 倒序
- **修改时间排序**: 改名为"按修改时间"（原名"按时间"，用 `modified_at`）
- **缩略图**: RGBA/P→RGB 防 JPEG 不兼容
- **计数**: `?click=1` 仅用户点击计数，5秒轮询不触发


## 4. RGBA 修复

详情页高清缩略图生成时，非 RGB/L 模式（RGBA/P/CMYK）自动转 RGB 再存 JPEG。
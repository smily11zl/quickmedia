# V18 技术设计

## 1. DB 迁移 — cancelled 状态

**文件**: `quickmedia/database.py`
**表**: `ai_queue`
**改动**: `_migrate()` 追加 `ALTER TABLE ai_queue ADD CHECK (status IN ('pending','processing','done','failed','cancelled'))`
**影响**: process_queue 只查 pending，cancelled 自然跳过

## 2. Worker was-cancelled 检查

**文件**: `quickmedia/ai_worker.py`
**位置**: `process_queue()` 重试循环（L170-175）
**改动**: 重试前 `SELECT status FROM ai_queue WHERE id=?` → 若 `cancelled` 则跳过

## 3. AI 状态颜色 + 筛选

**文件**: `frontend/src/App.tsx`
**改动**:
- `aiT()` 函数：新增颜色映射 `{done: "#5db872", processing: "#e8a55a", failed: "#c64545", pending: "#6c6a64", cancelled: "#8b75a6"}`
- 筛选下拉：`af` 选项新增 `{k:"cancelled", l:t("...")}` 
- locale 补 key：`asset.detail_ai_cancelled` / `asset.filter_cancelled`

## 4. 批量删除

**后端**: `quickmedia/api/server.py`
- 新增 `@app.post("/api/assets/batch-delete")` → 循环 `delete_asset_full()`
- `DELETE /api/assets/{id}` → 改为转发 `_batch_delete([id])`

**前端**: `frontend/src/App.tsx`
- 工具栏 `ms.size > 0` 区增加 «删除已选» 按钮
- 复用 `ConfirmModal` 弹窗确认

## 5. 队列全清

**后端**: `quickmedia/api/server.py`
- 新增 `@app.delete("/api/ai-queue")` → `DELETE FROM ai_queue`

**前端**: `frontend/src/App.tsx`
- 队列状态行 `qStat.pending` 旁加样式为链接的 «清除» 按钮
- ConfirmModal 确认后调用

## 6. MCP 字段对齐

**文件**: `quickmedia/mcp_server.py`
**改动**:
- `search_assets` 返回字段扩展：`SELECT *` → 返回完整 AssetDetail
- 类型标注 `AssetBasic` → `AssetDetail`
- 工具描述文档追加 `ai_status` 字段含义

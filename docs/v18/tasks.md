# V18 任务切片

> 6 切片，全部完成。

---

### s1: DB 迁移 — ai_status 列 + user_version ✅

**文件**: `quickmedia/database.py`

**实际实现**:
- `_migrate_v18()`: `ALTER TABLE assets ADD COLUMN ai_status TEXT` + `ai_status_updated_at TEXT`
- 回填老数据：`UPDATE assets SET ai_status=CASE WHEN ...`
- `PRAGMA user_version=18` 跳过后续连接迁移
- 启动时 `_cmd_serve` 额外回填 + 重置 stuck tasks

---

### s2: Worker cancelled + 存在性检查 ✅

**文件**: `quickmedia/ai_worker.py`

**实际实现**:
- 处理循环顶部检查 `assets.ai_status`（非 `ai_queue.status`）
- cancelled → break 跳过；素材不存在 → break 跳过
- AI 完成后二次检查 cancelled，防竞态
- 成功后：`assets.ai_status='done'` + `DELETE FROM ai_queue`
- 失败后：`assets.ai_status='failed'`
- 从 JOIN 获取 filename 避免二次查表崩溃

---

### s3: AI 状态颜色 + 筛选 ✅

**文件**: `frontend/src/App.tsx`, `frontend/src/locales/zh.ts`, `frontend/src/locales/en.ts`

**实际实现**:
- `aiT()` 5 色：done=#5db872/processing=#e8a55a/failed=#c64545/pending=#6c6a64/cancelled=#8b75a6
- 筛选下拉加 `cancelled` 项（带颜色）
- locale 补 `asset.detail_ai_cancelled` / `asset.filter_cancelled`
- 详情面板 cancelled 走 i18n
- 网格空状态 `detail.empty_hint` JSX 花括号修复

---

### s4: 批量删除 ✅

**文件**: `quickmedia/api/server.py`, `frontend/src/App.tsx`

**实际实现**:
- 后端：`POST /api/assets/batch-delete` → 复用 `delete_asset_full`（含 orphan tag 清理）
- 前端：工具栏 `«删除已选»` + `batchDeleteConfirm` state + `ConfirmModal`
- locale 补 `batch.delete_selected` / `batch.delete_confirm` / `common.delete`
- 确认按钮加 `confirmText`

---

### s5: 队列全清 ✅

**文件**: `quickmedia/api/server.py`, `frontend/src/App.tsx`

**实际实现**:
- 后端：`DELETE /api/ai-queue` → 先 `UPDATE assets SET ai_status='cancelled'` → `DELETE FROM ai_queue`
- 前端：队列状态行右侧 `«清除»` 按钮 → `ConfirmModal`
- locale 补 `queue.clear_all` / `queue.clear_confirm`

---

### s6: MCP 字段对齐 ✅

**文件**: `quickmedia/mcp_server.py`, `quickmedia/asset_ops.py`, `quickmedia/search.py`

**实际实现**:
- `AssetBasic` 扩为 19 字段（含 `ai_status`/`ai_status_updated_at`/`extension`/全描述字段）
- `AssetDetail` 加 `ai_status`/`ai_status_updated_at`
- `list_assets_filtered` SELECT 补全 16 字段
- `search.py` 3 处 SELECT 补全全字段
- 4 个核心工具 docstring 完全对齐模型声明

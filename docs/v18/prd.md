# V18 PRD

## v18 — 素材操作增强

### 问题

1. 多选素材后只能"重新分析"，无法批量删除
2. 队列卡住时无法清理，只能等重试耗尽
3. 网格/列表视图的 AI 状态标签全是灰色，与详情面板色值不统一
4. MCP search_assets 返回值不全，缺 video_summary/transcript/ocr_text 等关键字段

### 功能

#### 批量删除素材

- 工具栏多选后新增"删除已选"按钮（放在"重新分析已选"后面）
- 删除范围：素材记录 + 关联标签 + 向量索引 + 聚合节点关联 + 队列中相关任务
- 复用 ConfirmModal 弹窗确认
- 后端新增 `POST /api/assets/batch-delete`，内调 `delete_asset_full()` 循环
- 原有 `DELETE /api/assets/{id}` 改为转发到 `/batch-delete`（单一核心函数，多入口）
- MCP `delete_asset` 已有批量支持，无需改动

#### 队列全清

- 队列状态行"X 个待分析"右侧新增"清除"按钮
- 点击弹出 ConfirmModal 确认
- 后端新增 `DELETE /api/ai-queue`，清空 `ai_queue` 表（pending/processing/failed/cancelled）

#### AI 状态颜色

- `aiT` 函数新增颜色映射：done=绿 `#5db872`，processing=橙 `#e8a55a`，failed=红 `#c64545`，pending=灰 `#6c6a64`
- DB 新增 `cancelled` 状态（ai_queue CHECK 约束扩展）
- aiT 加 cancelled→紫 `#8b75a6`
- 筛选下拉新增"已取消"选项
- 队列统计不计入 cancelled
- Worker 重试前检查 was-cancelled，跳过

#### MCP 字段对齐

- `search_assets` 补全 video_summary、transcript、ocr_text、height、width、duration、hash 等字段
- 与 `get_asset` 返回值完全一致
- `ai_status` 字段含义写入工具描述：done=已完成(绿)、processing=分析中(橙)、pending=等待(灰)、failed=失败(红)、cancelled=已取消(紫)

### 未改动

- MCP `delete_asset` — 已有批量支持，不动
- 单素材删除 UI — 不动
- 队列统计组件 — 改处最小

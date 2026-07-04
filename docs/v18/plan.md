# V18 — 素材操作增强

> 状态：grill-me ✅ → grill-with-docs ✅ → to-prd ✅ → to-issues ✅ → tdd ✅ → **已完成**

## 功能

### 1. 批量删除素材
- 工具栏多选后增加"删除已选"按钮
- 删除范围：素材 + 标签 + 向量 + 聚合关联 + 队列任务
- 复用 ConfirmModal 确认弹窗

### 2. 队列全清
- 队列状态行右侧加"清除"按钮
- 全清 ai_queue（pending/processing/failed/cancelled）
- 弹窗确认

### 3. AI 状态颜色
- 网格/列表视图状态标签与详情面板统一色值
- 新增 cancelled=淡紫 `#8b75a6`
- 筛选下拉加"已取消"选项

### 4. MCP 字段对齐
- search_assets 补全 video_summary/transcript/ocr_text 等字段
- 与 get_asset 返回完全一致

## 决策记录

| # | 决策 | 结论 |
|---|------|------|
| Q1 | 批量删除范围 | C — 全关联清理 |
| Q2 | 删除按钮位置 | A — 工具栏同行 |
| Q3 | 队列清除 | B — 全清 + 确认弹窗 |
| Q3a | 清除按钮位置 | A — 状态行右侧 |
| Q4 | AI 颜色 | A — 详情面板同色 |
| Q5 | MCP 字段 | B — 完全对齐 |
| Q6 | cancelled 状态 | DB 新增字段 |
| Q7 | was-cancelled | 重试前检查 |
| Q8 | cancelled 颜色 | #8b75a6 |

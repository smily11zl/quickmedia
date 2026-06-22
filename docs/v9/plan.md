# QuickMedia v9 — 语义搜索优化 ✅ 完成

> 需求访谈记录。grill-me 时间：2026-06-18。完成时间：2026-06-22。

## 设计决策

### 1. search_terms 字段

新增 AI 输出字段，专注检索意图的搜索词。独立存储在 `asset_search_terms` 表。

✅ 最终方案：tags 与 search_terms 合并去重后统一向量化，不区分来源。

### 2. 覆盖范围

4 种分析类型全部输出 search_terms：vision / text / speech / video_summary。

✅ 新增 video_vision 独立类型（视频帧分析 prompt 独立）。

### 3. Prompt 结构

```
= default/custom（用户可编辑的分析指令）
+ system_format（固定 JSON 格式 + search_terms 生成规则）
```

system_format 包含：
- JSON schema：`{"description": ..., "tags": [...], "text": ..., "search_terms": [...]}`
- search_terms 规则（5-10 个）：从检索角度思考用户搜什么词

✅ 启动时自动同步 system_format，用户升级无需删 prompts.yaml。

### 4. 视频字段重构

| 旧字段 | 新字段 | 说明 |
|--------|--------|------|
| ai_description | visual_description | 帧画面描述 |
| video_summary | 不变 | 综合总结，视频主描述 |

✅ 无声视频自动填充 video_summary = visual_description。

### 5. 视频 search_terms 生成

| 视频类型 | 标签/搜索词来源 |
|---------|---------------|
| 有语音 | video_summary 分析 |
| 无声 | vision 帧分析 |

### 6. 向量化替换

search_terms 取代 tags 做语义匹配。每个 search_term 存独立向量，ID 格式 `search_{asset_id}_{term_index}`。

### 7. Top-K 聚合

- **K 值**：`config.yaml` 配置（默认 2）
- **算法**：每个 search_term 分别查询，取距离最小的 K 个求平均

### 8. 前端

- search_terms 不展示给用户
- ✅ ⭐ 智能标记：双重命中 + 距离比 1-5 星

### 9. 旧数据处理

清空全部素材，重启后重新扫码分析。

### 10. 额外决策（实施中追加）

- **多帧一次 API 调用**：Qwen-VL 多图批量分析，省 API 费用
- **PC 热加载**：修改自定义 prompt 无需重启
- **文档格式扩展**：CSV/JSON/XLSX/DOCX
- **搜索筛选联动**：结果上叠加筛选
- **纯语义模式**：独立于 RRF 融合
- **状态实时轮询**：列表 3s/详情 5s


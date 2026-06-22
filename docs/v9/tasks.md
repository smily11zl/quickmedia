# QuickMedia v9 任务拆分 ✅ 全部完成

## Slice 9.1 — 数据库 + Prompt 基础设施 ✅

**目标：** search_terms 表创建、prompt 更新、视频字段迁移。

- [x] `quickmedia/database.py`: ai_description → visual_description 迁移；asset_search_terms 新表
- [x] `prompts.yaml`: 所有 system_format 加 search_terms schema + 规则（vision/text/speech/video_summary/video_vision）
- [x] `quickmedia/config.py`: semantic.top_k 配置（默认 2）
- [x] 迁移脚本：启动时自动执行，幂等
- [x] `quickmedia/prompt_config.py`: 升级时自动补齐缺失字段；video_vision 新类型
- [x] 新增 docs/v9/ 四件套 + 更新 CONTEXT.md、PRD.md、ROADMAP.md

## Slice 9.2 — search_terms 生成与存储 ✅

**目标：** AI 分析输出解析 search_terms、入表、视频逻辑重构、标签合并嵌入。

- [x] `quickmedia/ai_worker.py`: `_save_search_terms` 方法 + 所有分析类型（vision/text/speech/video_summary/video_vision）调用
- [x] 视频逻辑：有语音走 video_summary 生成，无声复制 visual_description → video_summary
- [x] `quickmedia/api/server.py`: reanalyze（单/批）同步清理 tags/search_terms/ChromaDB
- [x] `quickmedia/ai.py`: VisionAnalyzer._parse_json_response 增 search_terms 字段；analyser_multi 多帧一次 API 调用
- [x] `quickmedia/ai.py`: merge_frame_results 包含 search_terms 去重
- [x] 文档支持扩展：CSV/JSON/XLSX 读取；`_read_text` 新增格式
- [x] `prompt_config.py`: 每次 `_load` 同步 system_format 确保代码更新即时生效
- [x] AIWorker `_pc()` 热加载 PromptConfig——保存自定义 prompt 无需重启
- [x] 文档分析 fallback 兜底统一引用 DEFAULT_PROMPTS
- [x] 文档分析绿色日志：区分传文件/提取文字模式
- [x] 格式筛选列表动态获取（/api/formats）

## Slice 9.3 — 向量化 + Top-K 检索 ✅

**目标：** search_terms + tags 合并做向量匹配，每词独立向量，Top-K 聚合。

- [x] `quickmedia/embedding.py`: `add` 支持 term_text metadata 存储；`query_search_terms` Top-K 聚合
- [x] `quickmedia/embedding.py`: `top_k_aggregate` 函数 + `delete` 同时清理 search_* 向量
- [x] `quickmedia/ai_worker.py`: embedding 任务合并 tags + search_terms 走统一向量化
- [x] `quickmedia/api/server.py`: 语义搜索 pure semantic 模式；combined 保留 RRF
- [x] 搜索模式日志区分：[Keyword search]、[Semantic search]、[RRF fusion]、[Search] mode=...
- [x] ⭐ 重要匹配逻辑：语义+关键词双重命中 按距离比显示 1-5 颗星

## Slice 9.4 — 前端适配 ✅

**目标：** 状态轮询、文档预览、搜索筛选联动、批量操作优化。

- [x] `ModelManager.tsx`: embedding 提示更新；模型能力标签（图片/文字/文档/视频/向量）+ 格式
- [x] 状态轮询：详情面板每 5s 实时刷新（不限状态）；素材列表 3s 刷新处理中/待处理状态
- [x] 文档类型缩略图区分：📕PDF 📝TXT/MD 📊CSV/XLSX 📋JSON 📄DOCX
- [x] 文档缩略图下方显示前 3 行文字预览（TXT/MD/DOCX）
- [x] 搜索与筛选联动：综合/语义搜索结果基础上叠加侧栏筛选
- [x] 文档缩略图预览文字 + 图标放大（12px 文字 + 5xl 图标）
- [x] 批量操作：已选 N 个 | 全选 | 取消选择 | 重新分析已选
- [x] ai_description → visual_description 字段适配
- [x] `App.tsx` 多文件格式：doc_preview、docI、searchResults、状态轮询

## v9 测试覆盖

| 测试类 | 数量 | 覆盖 |
|--------|------|------|
| TestV9DatabaseMigration | 2 | 新库字段 + 迁移 |
| TestV9ConfigAndPrompts | 4 | top_k + search_terms + 兜底 |
| TestV9SaveSearchTerms | 4 | search_terms 表读写 |
| TestV9SearchTermsEmbedding | 2 | 词向量 ID |
| TestV9TopKAggregation | 3 | Top-K 逻辑 |
| TestV9EmbeddingIntegration | 1 | 标签合并 |
| **总计** | **17** | 17/17 passed |

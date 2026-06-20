# QuickMedia v8 技术方案

## 最终架构

分字段向量化 + best-field 合并 + RRF 融合 + jieba 中文分词。

### 向量存储

每条素材存 3 个向量，ChromaDB ID 格式：`{field}_{asset_id}`

| 字段 | 内容来源 |
|------|---------|
| description | 图片/文档: ai_description+ai_summary；视频: video_summary(优先)+ai_description；音频: ai_summary |
| tags | 所有标签名拼接 |
| text | OCR文字 + 转录文本 + 文件名 |

### 搜索策略

1. **jieba 分词** — `cut_for_search("宠物狗粮")` → `["宠物","狗粮"]`
2. **关键词搜索** — 分词 token 做 OR LIKE，按匹配度排序（proxy BM25）
3. **语义搜索** — query_vector → 三字段分别查询 → best-field 取最小距离
4. **RRF 融合** — `score = 1/(60+bm25_rank) + 1/(60+vec_rank)`，综合排序

无距离阈值过滤，全部素材按得分展示。

### 相似素材

单字段查询：取素材 description 向量 → ChromaDB query → 返回 top N。

### 加权演化

- ~~平均值加权 （废弃）~~ — 描述 0.5 / 标签 0.3 / 文本 0.2
- **current: best-field** — 取三字段最小距离，标签命中直接推顶

## 依赖

```toml
embedding = ["chromadb>=0.5", "jieba>=0.42"]
```

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/search?q=...&mode=combined | RRF 融合（默认） |
| GET | /api/search?q=...&mode=semantic | 纯语义搜索 |
| GET | /api/search?q=...&mode=keyword | 关键词匹配 |
| GET | /api/assets/{id}/similar?limit=10 | 相似素材 |

## 修改文件

| 文件 | 变更 |
|------|------|
| `quickmedia/embedding.py` | _build_field_text 分字段；ChromaStore 多字段 ID + query_weighted + best-field |
| `quickmedia/ai_worker.py` | _process_embedding 分字段嵌入 ×3 |
| `quickmedia/api/server.py` | RRF 融合；jieba 分词；reanalyze 清 ChromaDB；相似端点 |
| `quickmedia/database.py` | search_tokens() OR LIKE + 匹配度排序 |
| `quickmedia/providers.py` | get_provider_url() |
| `pyproject.toml` | chromadb + jieba 依赖 |
| `frontend/src/App.tsx` | 搜索框 + 模式切换 + 加载遮罩 + 排序禁用 |
| `frontend/src/SimilarPanel.tsx` | 相似素材弹窗 |

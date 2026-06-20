# QuickMedia v8 PRD — 向量化 + 语义搜索

## Problem Statement

当前搜索仅支持关键词精确匹配。搜"蓝色风格"找不到蓝色调图片（标签是"纯色背景"而非"蓝色"），搜"会议相关"找不到会议录音。素材越多，精确匹配的局限性越大。

## Solution

通过 embedding 向量化实现语义理解，用户用自然语言描述即可找到相关素材。同时支持相似素材推荐。

### 核心功能

| 功能 | 说明 |
|------|------|
| Embedding 向量化 | 第 5 种分析类型，素材入库 → AI 分析 → embedding 自动入队 |
| 语义搜索 | 搜索框类型切换：综合 / 语义 / 匹配 |
| 相似素材推荐 | 详情页"找相似"按钮 → 叠加层展示相似结果 |
| 模型管理 | task_models 新增 embedding 类型，支持 Ollama/OpenRouter |

### Key Design Decisions

- 向量存储用 ChromaDB（`pip install chromadb`），内嵌模式
- **分字段向量化**：每个素材存 3 个向量（description/tags/text），格式 `{field}_{asset_id}`
- **best-field 合并**：三字段分别查询，取最小距离作为素材得分
- **RRF 融合搜索**：关键词排名 + 语义排名，`1/(60+k_rank) + 1/(60+v_rank)` 混合
- **jieba 中文分词**：查询文本拆分为语义 token，用于关键词 LIKE 匹配
- embedding 作为独立分析类型，通过 Provider 系统管理
- embedding 依赖 AI 分析结果，AI 分析完成后自动入队
- 入库和搜索必须用同一模型，切换模型需重建全量向量
- 无距离阈值过滤，全部素材按得分排序展示

## Testing Seam

| 层次 | seam |
|------|------|
| API 最高 | GET /api/search?mode=semantic\|combined，GET /api/assets/{id}/similar |
| 模块 | EmbeddingAdapter + ChromaDB → AIWorker embedding 任务 |
| 前端 | 搜索类型切换 + 相似素材叠加层 |
| 数据 | `~/.asset-manager/chroma_db/`，pyproject.toml chromadb 依赖 |

## Tasks

详见 [tasks.md](tasks.md)。

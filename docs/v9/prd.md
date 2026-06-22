# QuickMedia v9 PRD ✅ 完成

# QuickMedia v9 PRD — 语义搜索优化

## Problem Statement

当前语义搜索结果不理想——搜"宠物"时，短.mp4（纯红色背景）排名比有狗的20260615-164133.mp4还靠前。根因是 tags 向量的检索意图弱、描述字段区分度不足。

## Solution

1. AI 分析输出新字段 search_terms，从检索意图角度预先打标
2. 每个 search_term 存独立向量，Top-K 聚合匹配
3. 视频字段重构，统一描述数据流

### 核心功能

| 功能 | 说明 |
|------|------|
| search_terms | AI 输出 5-10 个搜索词，专注用户搜索行为预测 |
| 独立向量化 | 每个 search_term 一个向量，`search_{asset_id}_{term_index}` |
| Top-K 聚合 | 素材的 N 个词分别查询，取最近 K 个取平均（默认 K=2） |
| 视频字段重构 | `ai_description` → `visual_description`，视频主描述统一为 `video_summary` |
| Prompt 改进 | system_format 固定 search_terms 规则，用户编辑不涉及 |

### Key Design Decisions

- search_terms 存储于新表 `asset_search_terms`，无关 tags
- search_terms 取代 tags 做向量化匹配
- 有语音视频由 video_summary 生成 search_terms，无声由 vision 帧分析
- search_terms 不展示给用户，仅用于检索
- Top-K 的 K 值在 config.yaml 可配，默认 2
- 旧数据库清空，素材全部重新分析入库

### Testing Seam

| 层次 | seam |
|------|------|
| API | search_terms 存入/读取；向量查询 Top-K 聚合 |
| 模块 | Prompt 生成 function；数据库迁移；embedding 聚合逻辑 |
| 前端 | 任务配置提示更新（embedding 替换 tags 说明） |

## Tasks

详见 [tasks.md](tasks.md)。

# QuickMedia v9 技术方案 ✅ 完成

# QuickMedia v9 技术方案

## 数据库变更

### 迁移 SQL

```sql
-- 视频字段重命名
ALTER TABLE assets RENAME COLUMN ai_description TO visual_description;

-- search_terms 新表
CREATE TABLE asset_search_terms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL,
    term TEXT NOT NULL,
    UNIQUE(asset_id, term),
    FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE
);
```

## Prompt 变更

### vision（图片/无声视频）

```yaml
vision:
  system_format: |
    请严格按以下JSON格式输出（只输出JSON，不要有其他文字）：
    {"description": "图片描述", "tags": ["标签1", "标签2", "标签3"], "text": "文字", "search_terms": ["搜索词1", "搜索词2"]}
    如果没有识别到文字，text 为空字符串。

    search_terms 规则（5-10个）：
    - 从未来检索角度思考：用户可能用什么词搜到这张图
    - 覆盖主体、场景、风格、情绪、颜色、用途
    - 不需要和 tags 重复，专注可检索性
```

### text / speech / video_summary 同理

每个 system_format 加 `search_terms` 字段和相同规则。

## 向量变更

### 存储

| 旧格式 | 新格式 |
|--------|--------|
| tags_16 | 删除，不再使用 |
| text_16 | 保留 |
| description_16 | 保留 |
| — | search_16_0, search_16_1, ... |

### Top-K 聚合查询

```python
def query_search_terms(query_vector, asset_search_terms, k=2):
    # 对每个素材的每个 search_term 向量查距离
    # 取距离最小的 k 个求平均值
    # 返回 {asset_id: avg_distance}
```

## AI Worker 变更

### _process_vision 输出解析

解析 search_terms → 写入 asset_search_terms 表 → enqueue embedding。

### 视频逻辑

```python
if asset_type == "video":
    if transcript:  # 有语音
        # video_summary 生成 search_terms
    else:
        # vision 帧分析生成 search_terms
```

## config.yaml

```yaml
semantic:
  top_k: 2  # Top-K 聚合的 K 值
```

## 前端

- ModelManager：embedding 提示更新（"向量化使用 search_terms，非标签"）
- 无需新增 UI

## 清理

启动时检测 V9 schema 版本，执行迁移 SQL。用户手动清空素材重新扫描。

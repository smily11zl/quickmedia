# QuickMedia v4 技术方案

> 基于 v3 技术架构的增量设计。

## 变更范围

| 模块 | 变更类型 | 说明 |
|------|---------|------|
| server.py | 扩展 | API 新增筛选参数（date_from/to, formats, tags, ai_status） |
| scanner.py | 修改 | _auto_tags 不再生成时间/格式/类型标签 |
| database.py | 扩展 | 新增 _cleanup_v4_tags() 启动标签清理 |
| App.tsx | 重构 | 新增 FilterBar + PopoverMultiSelect + DateRangeFilter |
| cli.py | 扩展 | serve 命令启动时调用标签清理 |

## API 变更

### 素材列表 API 新增参数

```
GET /api/assets?type=image&date_from=2026-06-01&date_to=2026-06-07
                &formats=jpg,png&tags=1,2,3&ai_status=done,failed
```

### 筛选逻辑

```python
def list_assets(offset, limit, type, date_from, date_to,
                mdate_from, mdate_to, formats, tags, ai_status):
    # 构造 WHERE 子句
    conditions = ["a.status='active'"]
    params = []

    if type:
        conditions.append("a.asset_type=?")
        params.append(type)

    if date_from:
        conditions.append("a.created_at >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("a.created_at <= ?")
        params.append(date_to)

    if formats:
        fmt_list = formats.split(",")
        placeholders = ",".join("?" * len(fmt_list))
        conditions.append(f"a.extension IN ({placeholders})")
        params.extend(f".{f}" for f in fmt_list)

    if tags:
        tag_ids = [int(t) for t in tags.split(",")]
        conditions.append("a.id IN (SELECT asset_id FROM asset_tags WHERE tag_id IN (...))")
        # 取交集：asset 必须拥有所有指定 tag
        params.extend(tag_ids)

    if ai_status:
        status_list = ai_status.split(",")
        # 子查询：每个 asset 的最新 ai_queue status
        ...
```

## 标签清理

### 实现

```python
def _cleanup_v4_tags(db: Database) -> int:
    """Remove time/format/type auto-tags. Returns count removed."""
    import re
    removed = 0
    # 1. Time tags: "2026", "2026-06"
    time_tags = db.execute(
        "SELECT id, name FROM tags WHERE source='auto' AND "
        "(name GLOB '[0-9][0-9][0-9][0-9]' OR name GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]')"
    )
    # 2. Format tags: "PNG", "MP4", etc.
    format_tags = db.execute(
        "SELECT id, name FROM tags WHERE source='auto' AND name GLOB '[A-Z][A-Z0-9]*'"
    )
    # 3. Type tags: "图片", "视频", "音频", "文档"
    type_tags = db.execute(
        "SELECT id, name FROM tags WHERE source='auto' AND name IN ('图片','视频','音频','文档')"
    )
    ...
```

### Scanner 变更

`_auto_tags` 移除时间标签生成（year, year-month）、格式标签生成、类型标签生成。保留时长段标签。

## 前端变更

### FilterBar 组件结构

```
<FilterBar>
  <DateRangeFilter label="创建时间" />
  <DateRangeFilter label="修改时间" />
  <PopoverMultiSelect label="格式" options={formats} />
  <PopoverMultiSelect label="标签" options={tags} searchable />
  <PopoverMultiSelect label="AI 状态" options={statuses} />
</FilterBar>
```

### PopoverMultiSelect 组件

- 点击触发弹出面板
- 面板内可选搜索框
- 多选勾选列表
- 点击外部关闭
- 显示已选数量 badge

### DateRangeFilter 组件

- 快捷按钮行：今天 / 本周 / 本月 / 今年
- 自定义区间：开始日期 input + 结束日期 input
- 已选区间显示为 tag（如「2026-06-01 ~ 2026-06-07」）
- 清除按钮重置

## 测试策略

| 层级 | 测试内容 | 文件 |
|------|---------|------|
| API | 筛选参数组合返回正确结果 | test_api.py |
| Scanner | _auto_tags 不再生成旧标签 | test_scanner.py |
| 数据库 | 标签清理逻辑 | test_database.py |

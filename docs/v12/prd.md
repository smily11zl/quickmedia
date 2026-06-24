# V12 PRD — 素材聚合

> 版本切面副本，全版本汇总见 ../../PRD.md

## Problem Statement

素材通过 AI 分析获得了描述、标签、摘要，但所有素材仍然是以扁平列表呈现。用户没有"概念级"的素材组织方式——无法按主题（如"猫的照片"、"购物记录"）快速浏览跨类型的素材集合。

## Solution

AI 驱动的素材自动聚类。三种手动触发的聚合模式：全量分析（从头重建）、全量追加（增量发现新节点）、追加分析（新素材入已分配节点）。

## Key Features

- 三种聚合模式，全部手动触发
- AI 单次调用分析全库素材，返回 nodes + assignments
- 独立 Aggregation Worker 进程，独立 SQLite 队列表
- nodes + node_assets 多对多关系
- 节点右键菜单：重命名、编辑描述、删除、手动添加/移除素材
- 侧边栏顶部双 Tab：搜索与筛选 / 聚合节点
- 点击节点后右侧素材面板复用现有素材列表
- 删除素材时级联清理 node_assets

## API Endpoints

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/aggregation/run | 提交聚合任务 (body: {mode}) |
| GET | /api/aggregation/status | 查询任务状态 |
| GET | /api/nodes | 节点列表 |
| GET | /api/nodes/{id}/assets | 节点下的素材 |
| POST | /api/nodes | 创建节点 |
| PUT | /api/nodes/{id} | 编辑节点 |
| DELETE | /api/nodes/{id} | 删除节点 |
| POST | /api/nodes/{id}/assets | 手动关联素材 (body: {asset_ids}) |
| DELETE | /api/nodes/{id}/assets/{asset_id} | 取消关联 |

## Database

```sql
CREATE TABLE aggregation_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT NOT NULL,       -- full / full_append / append
    status TEXT DEFAULT 'pending',  -- pending / processing / done / failed
    error TEXT,
    created_at TEXT,
    completed_at TEXT
);

CREATE TABLE nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT
);

CREATE TABLE node_assets (
    node_id INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    PRIMARY KEY (node_id, asset_id)
);
```

## Code Organization

- **后端**: `quickmedia/aggregation/worker.py` (Worker进程+队列), `prompts.py` (prompt构建), `api.py` (路由)
- **前端**: `NodePanel.tsx` (侧边栏Tab2), `AddAssetModal.tsx` (手动添加素材弹窗)
- **测试**: `tests/test_v12.py`

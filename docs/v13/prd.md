# V13 PRD — 云图

> 版本切面副本，全版本汇总见 ../../PRD.md

## Problem Statement

素材聚合节点为扁平列表展示，用户无法直观看到节点间的语义关系、节点与素材的归属关系。节点间的共享素材关联完全不可见。

## Solution

ForceGraph2D (react-force-graph-2d) 力导向图可视化。聚合节点和素材作为图节点渲染，共享边展示节点间关系，支持展开/折叠素材节点、搜索/筛选高亮淡化、缩放拖拽，与现有网格/列表视图并列切换。

## Key Features

- 视图切换三按钮：☁ 云图 / ▦ 网格 / ☰ 列表
- 聚合节点按素材数量缩放 + 数量梯度着色
- 共享边（粗细=共享素材数）
- 未分配节点（前端虚拟构造，灰色虚线边框）
- 素材节点按类型着色，zoom ≥ 1.5x 显示缩略图+文件名
- 图例（右上角固定说明）
- 单击节点=选中，双击=展开/折叠素材节点
- 单击素材节点=打开详情面板
- 单击空白=取消选中，📌清除条跨视图统一入口
- 搜索高亮（匹配高亮，不匹配弱化）
- 缩放控件：+/− + 居中复位 + 🔄 重新加载
- WebSocket 增量推送 graph_changed 事件
- 展开状态跨视图保留
- 无节点时自动显示未分配节点+全部素材

## API Endpoints

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/graph | 返回 {nodes, edges, unassigned} 三段结构 |
| WS | /ws/graph | WebSocket 推送 graph_changed 事件 |

### GET /api/graph

```
{
  "nodes": [{"id": N, "name": "...", "asset_count": N, ...}],
  "edges": [{"node_id": N, "asset_id": N}, ...],
  "unassigned": [{"id": N, "filename": "...", "asset_type": "..."}, ...]
}
```

后端 JOIN node_assets + NOT IN 查未分配素材。

### WS /ws/graph

聚合完成、节点增删改、素材关联变化时推送：

```
{"event": "graph_changed"}
```

前端收到后调用 GET /api/graph 增量重绘。保留视口位置、zoom、仍存在的展开节点。

## Code Organization

- **后端**: `quickmedia/api/server.py` (GET /api/graph, WS /ws/graph)
- **前端**: `GraphView.tsx` (Cytoscape.js 渲染 + 交互)
- **测试**: `tests/test_v13.py`, `frontend/tests/GraphView.test.tsx`

## Testing Decisions

- 后端测试风格参考 `tests/test_v12.py`，用 FastAPI TestClient 测 `/api/graph` 和 WebSocket
- 前端测试参考 `frontend/tests/NodePanel.test.tsx`，vitest + testing-library
- 测试关注 API 响应结构正确性 + 前端组件交互，不测 Cytoscape 内部渲染

## Out of Scope

- 云图手动编辑（拖拽创建连线、手动建节点）
- 导出云图为图片
- 3D 视图

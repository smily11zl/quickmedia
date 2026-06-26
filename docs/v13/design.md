# V13 — 云图 架构设计

## 数据流

```
GET /api/graph
  → { nodes, edges, unassigned }
  → GraphView: sync useEffect 构建 nodeMap + linkMap + edgeMap
  → ForceGraph2D 渲染 d3-force 力导向图

WebSocket /ws/graph
  → graph_changed 事件
  → 增量重绘（nodeMap/linkMap 增量更新）
```

## 组件结构

```
App.tsx
├─ Header: QuickMedia + 素材统计 + gear
├─ Sidebar: 搜索/聚合节点 tab
├─ Main (flex-col)
│  ├─ 操作栏: ▦▦/☰/☁ 切换 + 排序 + 统计 (图模式隐藏排序)
│  └─ 内容区 (flex-1 relative)
│     ├─ GraphView (absolute inset-0, hidden 切换) ← 始终挂载
│     └─ 网格/列表 (absolute inset-0, hidden 切换)
└─ Details Panel: 素材详情
```

## GraphView 核心逻辑

### nodeMap 管理
- 聚合节点: `node-{id}`, isAgg=true, count, label
- 未分配节点: `unassigned`, isUnassigned=true
- 素材节点: `asset-{id}`, isAgg=false, assetType, label, aiSummary
- 环形布局: 展开时素材按 `angle = idx/assets * 2π, r=30` 分布

### 增量更新
- `graphVersion` state 仅在节点/边数量变化时递增
- `fgData = useMemo([graphVersion])` 只在结构变化时重建引用
- 缩略图加载通过 `fgRef.current?.refresh()` 仅刷 canvas
- WebSocket 推送 → `graphData()` setter → 无需 React 重渲染

### 力导向参数
| 参数 | 值 | 说明 |
|------|-----|------|
| charge | -20 → -1 | 初始扩散，冷却后永久 -1 |
| collision | agg:30, asset:15 | 按需排斥，无全局漂移 |
| link distance | radius + 60 | 动态，跟随节点大小 |
| center | 0 | 关闭中心引力 |
| cooldownTicks | 100 | 100 tick 冷却 |

### 搜索/筛选淡化
- `filteredAssets={fs}` 传入 GraphView
- `searchIdSet` 合并 filteredAssets 构建可见 Set
- `hasActiveFilter`: tf/ff/af/tgf/搜索/selectedNodeId 任一激活
- `visibleAggIds`: 聚合节点连接的素材有任意可见即保持不透明
- 未分配节点同理
- `nodeCanvasObject`: `ctx.globalAlpha` 控制淡化

### 单击交互
- 聚合节点: toggle 展开/折叠（不选中）
- 素材节点: onSelectAsset → serail 详情面板
- 空白: onBackgroundClick → 取消选中
- 侧边栏已选节点再次点击: 清除选中
- 缩略图点击区: nodePointerAreaPaint 5px 精准圆

### 重新加载 🔄
- onReload → fetch /api/graph → setGraphData + setExpandedNodes(全展开) + graphKey++ → 组件重挂载
- 不刷新页面

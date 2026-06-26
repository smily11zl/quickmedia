# QuickMedia v13 任务拆分

## Slice 13.1 — API: GET /api/graph

**目标：** 新增 `/api/graph` 端点，返回 `{nodes, edges, unassigned}` 三段结构。

- [x] `server.py`: GET /api/graph — JOIN nodes + node_assets + assets，NOT IN 查未分配素材
- [x] `server.py`: create_app() 中注册路由
- [x] 返回字段：nodes `{id, name, description, asset_count}`，edges `{node_id, asset_id, filename, asset_type, ai_summary, thumbnail_status}`，unassigned `{id, filename, asset_type, ai_summary, thumbnail_status}`
- [x] 测试: `tests/test_v13.py` — 有节点时返回正确三段 / 无节点时 nodes=[], unassigned=全素材 / 素材关联 multi-node

---

## Slice 13.2 — GraphView 基础渲染

**目标：** 安装 ForceGraph2D，GraphView 组件基础渲染 + 图例 + 缩放控件。

- [x] `npm install react-force-graph-2d`（替代 Cytoscape.js，d3-force 持续物理模拟）
- [x] `GraphView.tsx` — 接收 graphData prop，渲染 ForceGraph2D 实例
- [x] 聚合节点：大小=count，颜色=珊瑚 `#e8623a`
- [x] 素材节点：图片/视频显示等比缩略图(maxDim=60)，文档/音频彩色圆点+文件名
- [x] 配色方案：图片 `#5b9ecf` / 视频 `#c95a8a` / 音频 `#7eb84a` / 文档 `#c89e40`
- [x] 未分配节点：蓝灰 `#8698b0` 虚线边框，前端虚拟构造
- [x] 图例：右上角固定，含所有类型色块
- [x] 缩放控件：左下角 +/− 按钮 + zoom 百分比 + 居中复位(⌂) + 重新加载(🔄)
- [x] 调用 GET /api/graph 获取数据
- [x] 测试: `frontend/tests/GraphView.test.tsx` — 接收数据渲染节点/边

---

## Slice 13.3 — 视图 Toggle 集成

**目标：** App.tsx 加入云图按钮，条件渲染 GraphView。

- [x] App.tsx: 视图 Toggle 改为三按钮 ▦ 网格 / ☰ 列表 / ☁ 云图
- [x] vw state 扩展支持 "graph"
- [x] 主内容区：操作栏固定，内容区 absolute inset-0 重叠，hidden 切换（无重绘）
- [x] 云图模式下隐藏排序控件和清除条
- [x] GraphView 接收 selectedNodeId / selectedNodeName / searchResults / filteredAssets prop
- [x] 测试: 前端测试 Toggle 切换渲染正确组件

---

## Slice 13.4 — GraphView 交互

**目标：** 展开折叠/详情/搜索高亮/筛选淡化/空白取消。

- [x] 单击聚合节点 → 展开/折叠素材节点（不触发选中）
- [x] 单击素材节点 → 触发详情面板（复用现有 selA 逻辑）
- [x] 单击空白区域 → 取消选中（onBackgroundClick → onSelectNode(null)）
- [x] 搜索/筛选淡化：命中素材保持不透明，其余 15% alpha
- [x] 聚合节点可见性：连接的素材有任意命中即保持不透明
- [x] 未分配节点可见性：同理
- [x] 清除条（📌）可清除节点选中
- [x] 侧边栏点击已选中节点 = 清除选中
- [x] 素材节点文件名截断（>10 字符显示...）
- [x] 测试: 前端测试交互行为

---

## Slice 13.5 — WebSocket 后端

**目标：** FastAPI WebSocket 端点 + 广播触发。

- [x] `server.py`: WS /ws/graph — accept 连接，维护连接池
- [x] 广播函数 `broadcast_graph_changed()` — 推 `{"event": "graph_changed"}`
- [x] 聚合完成时广播
- [x] 节点 CRUD 时广播
- [x] 手动关联/取消关联素材时广播
- [x] 测试: TestClient.websocket_connect 验证收到事件

---

## Slice 13.6 — WebSocket 前端 + 状态持久 + 重新加载

**目标：** 前端接收 WebSocket 推送，增量重绘 + 视图状态保留 + 重新加载。

- [x] GraphView 挂载时建立 WS 连接，卸载时断开
- [x] 收到 graph_changed → 调 GET /api/graph → 增量重绘
- [x] 增量重绘：保留视口位置 + zoom + 仍存在的展开节点
- [x] 视图切换保留状态：absolute inset-0 + hidden，无重绘
- [x] 🔄 重新加载：fetch /api/graph + reset expandedNodes + key 重挂载（不刷新页面）
- [x] 测试: 前端测试 WS mock + 状态持久

---

## Slice 13.7 — 力导向参数调优（本会话新增）

**目标：** 优化力导向布局参数，稳定交互体验。

- [x] charge: 初始 -20，首次冷却后 -1（避免全局漂移）
- [x] collision: 聚合节点 30px，素材节点 15px（按需推开）
- [x] link distance: 动态 = 聚合节点半径 + 60px
- [x] center force: 0（关闭，避免节点拉回中心）
- [x] cooldownTicks: 100
- [x] 聚合节点初始位置：中心 (-200, 0)，范围 ±400 × ±300
- [x] 未分配节点初始位置：(700, -200)，右侧远离
- [x] 展开素材节点：环形布局（半径 30px）
- [x] 连线宽度：2px
- [x] nodePointerAreaPaint：聚合圆匹配视觉，素材 5px 精准点

## 当前力参数总览

| 参数 | 值 |
|------|-----|
| charge | -20 → -1 |
| collision(agg/asset) | 30 / 15 |
| link distance | radius + 60 |
| center | 0 |
| cooldownTicks | 100 |
| agg init x range | [-600, 200] |
| agg init y range | [-300, 300] |
| unassigned init | (700, -200) |

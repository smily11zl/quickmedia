# V14 技术方案

## API 变更

### 新增端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/nodes` | POST | 手动创建节点 {name, description} |
| `/api/nodes/{id}/analyze-append` | POST | 对节点执行分析追加 |

### 修改端点

| 端点 | 方法 | 变更 |
|------|------|------|
| `/api/nodes/{id}` | DELETE | `def` → `async def`，移除 `asyncio.run()` |
| `/api/nodes` | POST | 同上，移除 `asyncio.run()` |
| `/api/nodes/{id}` | PUT | 同上，移除 `asyncio.run()` |
| `/api/nodes/{id}/assets/{asset_id}` | DELETE | 同上，移除 `asyncio.run()` |

所有聚合模块 mutation 端点的 `broadcast_graph_changed()` 调用统一改为 `await`。

## 后端模块

### aggregation/prompts.py
新增 `build_append_prompt(node, candidates: list)` 函数，生成节点分析追加的 LLM prompt。

### aggregation/api.py
新增 `POST /api/nodes/{id}/analyze-append` 端点：
1. 查节点信息 + 现有素材
2. 查全库未连接到此节点的素材（`NOT IN (SELECT asset_id FROM node_assets WHERE node_id=?)`）
3. 无可分析素材 → 直接返回 `{ok: true, added: 0}`
4. 调 `build_append_prompt()` → `OpenAIAdapter.chat()` → JSON 解析
5. 批量 `INSERT OR IGNORE INTO node_assets`
6. `await broadcast_graph_changed()`
7. 返回 `{ok: true, added: N}`

### mcp_server.py
新增 7 个工具：
- `list_nodes()` → 节点列表
- `get_node(node_id)` → 节点详情
- `create_node(name, description)` → 新建节点
- `update_node(node_id, name, description)` → 更新节点
- `delete_node(node_id)` → 删除节点
- `add_assets_to_node(node_id, asset_ids)` → 手动分配
- `analyze_append_node(node_id)` → 分析追加（阻塞，30s 超时）

输出模型复用聚合模块的 Pydantic 结构。

## 前端组件

### NodePanel.tsx
- 新增 `+新建节点` 按钮，点击打开 `editNode` 弹框（空字段，标题"新建节点"，POST）
- 右键菜单新增"分析追加到此节点"
- 分析中状态：节点行右侧 16px coral 旋转菊花，hover tooltip
- 删除流程：弹确认框 → 菊花+禁用 → 消失动画 → `onSelectNode(null)`
- 聚合失败 `alert` → toast

### 通用组件（新增或抽取）

#### ConfirmModal
- 设计风格确认弹框，可配标题/描述/确认按钮文字/颜色
- 用于：删除节点、删除素材、删除 provider
- 确认中菊花 + 按钮禁用

#### Toast
- 顶部居中浮层，2.5s 自动消失
- z-index 最高
- 支持：info（coral）/ error（#c64545）/ success（#5db872）
- 多处替换：聚合失败、扫描结果、扫描配置缺失

### App.tsx
- 删 `useEffect` 中 `fetch("/api/config/watch-paths") + sso(true)`
- 素材删除 `confirm` → ConfirmModal
- 扫描 alert → Toast

### ModelManager.tsx
- Provider 删除 `confirm` → ConfirmModal

### AddAssetModal.tsx
- 新增 `mode` prop（"add" | "remove"）
- remove 模式：加载节点已有素材，批量调用 DELETE 取消分配
- remove 模式：标题"从节点移除素材"，按钮"确认移除 (N)"

### GraphView.tsx（云图视觉增强）
- 聚合节点圆圈内显示素材数量（白色粗体，字号 10-22px 随 r 自适应）
- 未分配节点也显示素材数量（字号固定 12px，浅蓝色文字）
- 颜色深度梯度：根据 radius 计算 `hsl(14, s%, l%)`，素材越多颜色越深
- 节点尺寸参数：radius 12-55（count×5），连线 radius+80

### MCP server（扩展）
- 新增 `trigger_scan` / `get_aggregation_status` / `reanalyze_asset`
- 新增 `add_asset_tag` / `remove_asset_tag` / `get_stats`
- `run_aggregation` 改为阻塞模式（300s 超时），覆盖 full/full_append/append 三种模式
- 输出模型新增 `NodeInfo` / `NodeDetail`
- 总计 21 个 MCP 工具

## 测试方案

- `tests/test_v14.py`：API 端点测试（CRUD + analyze_append）
- `tests/test_mcp_v14.py`：MCP 工具测试
- `frontend/tests/NodePanel.test.tsx`：节点交互测试
- `frontend/tests/Toast.test.tsx`：Toast 组件测试

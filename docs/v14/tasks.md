# V14 开发任务

## 切片 1: Toast 组件 + 替换全部 alert

**类型**: AFK
**阻塞**: 无

### What to build

创建通用 Toast 组件，替换项目中所有原生 `alert()` 调用。Toast 顶部居中浮层，coral 色背景白色文字，2.5s 自动消失，z-index 最高。支持 info/error/success 三种样式。

### Acceptance criteria

- [ ] Toast 组件渲染顶部居中，2.5s 自动消失
- [ ] info 样式 coral (#cc785c) / error (#c64545) / success (#5db872)
- [ ] z-index 最高，始终在最前
- [ ] NodePanel 聚合提交失败 `alert(d.detail)` → Toast error
- [ ] App.tsx 扫描无配置 `alert("请先配置扫描文件夹")` → Toast error
- [ ] App.tsx 扫描结果 `alert(d.message)` ×3 → Toast info
- [ ] 统一设计 token，遵循 DESIGN.md

### Blocked by

无 — 可立即开始

---

## 切片 2: ConfirmModal 组件 + 替换全部 confirm

**类型**: AFK
**阻塞**: 无

### What to build

创建通用 ConfirmModal 组件，替换项目中所有原生 `confirm()` 调用。复用现有编辑弹框风格（居中模态 + backdrop + hairline 边框），可配置标题、描述、确认按钮文字和颜色。确认按钮支持珊瑚色（普通确认）和 error 色（删除确认）。

### Acceptance criteria

- [ ] ConfirmModal 渲染与编辑弹框风格一致
- [ ] 可配置 title/description/confirmText/onConfirm/onCancel
- [ ] 支持 confirmColor 参数（coral 或 error）
- [ ] NodePanel 删除节点 `confirm("确认删除此节点？")` → ConfirmModal
- [ ] App.tsx 素材删除 `confirm("确认删除 xxx？")` → ConfirmModal
- [ ] ModelManager 删除 provider `confirm("确定删除 provider xxx？")` → ConfirmModal
- [ ] 遵循 DESIGN.md token

### Blocked by

无 — 可立即开始

---

## 切片 3: 修复节点删除 + 删除确认弹框

**类型**: AFK
**阻塞**: #2

### What to build

修复节点删除功能。后端：`delete_node` 改为 `async def`，`asyncio.run()` → `await broadcast_graph_changed()`。前端：删除时弹出 ConfirmModal（确认按钮 error 色，显示节点名），确认后按钮变菊花+禁用，成功后节点行渐变消失，调用 `onSelectNode(null)` 清选中。

### Acceptance criteria

- [ ] `DELETE /api/nodes/{id}` 正常返回 200，不再报 asyncio 错误
- [ ] `broadcast_graph_changed()` 正常推送 WebSocket 事件
- [ ] 删除确认弹框显示节点名，确认按钮 error 色
- [ ] 删除中确认按钮显示菊花 + 禁用
- [ ] 成功后节点行渐变消失
- [ ] 删除后 `selectedNodeId` 被清除
- [ ] 同样修复 create/update/assign 端点的 asyncio.run() 问题
- [ ] API 端点测试通过

### Blocked by

#2 — ConfirmModal 组件

---

## 切片 4: 手动新建节点

**类型**: AFK
**阻塞**: 无

### What to build

NodePanel 节点列表顶部加"+ 新建节点"按钮，复用现有编辑弹框（标题改为"新建节点"，空字段），保存调 `POST /api/nodes`，成功后刷新节点列表。

### Acceptance criteria

- [ ] 节点列表顶部显示"+ 新建节点"按钮
- [ ] 点击打开编辑弹框，标题"新建节点"，字段为空
- [ ] 名称必填，空时不可保存
- [ ] 保存调 POST /api/nodes，成功后刷新列表
- [ ] API 端点测试通过

### Blocked by

无 — 可立即开始

---

## 切片 5: 节点分析追加

**类型**: AFK
**阻塞**: #1

### What to build

右键菜单在"重命名"和"手动添加"之间新增"分析追加到此节点"。后端新增 `POST /api/nodes/{id}/analyze-append`，查全库未连接素材，调 `build_append_prompt()` + OpenAIAdapter，解析 JSON 后批量 INSERT。无素材或全连接时 toast 提示。执行中节点行右侧显示 16px coral 旋转菊花，hover tooltip"分析中..."。prompt 放 `aggregation/prompts.py`。

### Acceptance criteria

- [ ] 右键菜单"分析追加到此节点"在"重命名"和"手动添加"之间
- [ ] 分析范围：全库所有未连接到此节点的素材（NOT IN node_assets WHERE node_id=）
- [ ] 分析模型：复用 text 模型配置
- [ ] 无可分析素材时 toast "无可分析的素材"
- [ ] 执行中节点行右侧 coral 旋转菊花 + hover tooltip
- [ ] 成功后自动刷新节点列表（素材数更新）
- [ ] API 端点测试通过
- [ ] 前端组件测试通过

### Blocked by

#1 — 需要 Toast 组件提示无可分析素材

---

## 切片 5b: 手动移除节点素材

**类型**: AFK
**阻塞**: 无

### What to build

右键菜单"手动添加素材"下方新增"手动移除素材"。AddAssetModal 新增 `mode` prop（"add" | "remove"），remove 模式加载节点已有素材，多选后批量调用 `DELETE /api/nodes/{id}/assets/{aid}`。移除后刷新节点列表和主内容区。全量分析已有节点时弹出确认框。

### Acceptance criteria

- [ ] 右键菜单"手动移除素材"在"手动添加素材"下方
- [ ] AddAssetModal mode="remove" 加载节点已有素材列表
- [ ] 多选素材后"确认移除"按钮可用
- [ ] 移除后节点素材数更新
- [ ] 选中节点时主内容区同步刷新
- [ ] 全量分析已有节点时弹出确认框
- [ ] 前端组件测试通过

### Blocked by

无 — 可立即开始

---

## 切片 6: 去掉配置引导

**类型**: AFK
**阻塞**: 无

### What to build

删除 App.tsx useEffect 中 `fetch("/api/config/watch-paths").then(d => { if(!d.paths||d.paths.length===0) sso(true) })` 行。不影响扫描按钮的独立检查。

### Acceptance criteria

- [ ] 刷新页面不再自动弹出设置弹窗
- [ ] 扫描按钮"扫描配置路径"仍然检查文件夹是否为空
- [ ] 其他逻辑不受影响

### Blocked by

无 — 可立即开始

---

## 切片 7: MCP 节点管理工具

**类型**: AFK
**阻塞**: #3, #5

### What to build

MCP server 新增 7 个节点管理工具：list_nodes, get_node, create_node, update_node, delete_node, add_assets_to_node, analyze_append_node。analyze_append_node 使用阻塞模式（30s 超时）。输出模型使用 Pydantic，复用聚合模块结构。

### Acceptance criteria

- [ ] `list_nodes` 返回节点列表（含 asset_count）
- [ ] `get_node(node_id)` 返回节点详情 + 素材列表
- [ ] `create_node(name, description)` 手动创建节点
- [ ] `update_node(node_id, name, description)` 更新节点
- [ ] `delete_node(node_id)` 删除节点
- [ ] `add_assets_to_node(node_id, asset_ids)` 批量分配素材
- [ ] `analyze_append_node(node_id)` 阻塞执行分析追加，30s 超时
- [ ] 所有工具通过 MCP stdio 调用测试
- [ ] Pydantic 输出模型字段有完整 Field description

### Blocked by

#3 — 依赖删除节点修复完成
#5 — 依赖分析追加后端接口完成

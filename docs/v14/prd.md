# V14 产品需求文档

> 详见 PRD.md v14 节。此文件为 V14 版本快照。

## Problem Statement

聚合节点的管理能力不足：节点创建只能通过 AI 聚合，无法手动创建；节点删除有 bug 无法使用；单个节点缺少智能补充素材的能力。MCP 工具只覆盖素材操作，无法在对话中管理聚合节点。此外，刷新页面时配置引导弹框过于激进，原生 confirm/alert 弹窗与设计系统不一致。

## Solution

1. **节点分析追加**：右键节点触发，AI 分析全库未连接至此节点的素材，自动匹配添加
2. **手动创建节点**：聚合节点列表支持手动新建，输入名称和描述
3. **修复节点删除**：修复后端 asyncio 冲突 + 前端选中状态清理 + 删除确认弹框改为设计风格
4. **去掉配置引导**：移除页面刷新时自动弹出设置弹窗的逻辑
5. **统一弹框风格**：所有 confirm/alert 原生弹窗替换为设计系统风格的确认弹框和顶部居中 toast
6. **MCP 节点管理**：新增 7 个 MCP 工具覆盖节点 CRUD + 分析追加 + 手动分配素材

## User Stories

1. 作为素材库用户，我想对已有聚合节点一键分析还能加入什么素材，让节点自动补充遗漏的素材
2. 作为素材库用户，我想手动创建聚合节点并命名，不用必须依赖 AI 全量聚合
3. 作为素材库用户，我想删除不再需要的聚合节点，并且操作有确认、有反馈
4. 作为素材库用户，我不想在刷新页面时被自动弹出的设置窗口打断
5. 作为素材库用户，我想所有确认/提示弹窗都统一风格，不再看到浏览器原生的 alert/confirm
6. 作为 AI Agent 用户，我想在 Hermes 对话中直接管理聚合节点（查看、创建、删除、分析追加），不用切换到 Web UI

## Implementation Decisions

- 节点分析追加复用聚合模块的 AI 调用链路（OpenAIAdapter + JSON 解析），新增专属 prompt
- 分析追加使用 daemon 线程，执行期间前端节点行显示旋转菊花 + hover 提示
- 分析范围：全库所有未连接到此节点的素材（不受"未分配"限制），自动添加无需确认
- 无可分析素材时（节点无素材或全库已全连接），前端提示不调 AI
- 新建节点复用现有的编辑弹框样式，标题改为"新建节点"，保存调 POST
- 删除节点修复：后端 `def` → `async def`，`asyncio.run()` → `await broadcast_graph_changed()`
- 删除节点前端：调父组件 `onSelectNode(null)` 清选中，弹框内显示删除中菊花
- 统一弹框：所有 confirm 替换为编辑弹框风格确认框，所有 alert 替换为顶部居中 toast（2.5s）
- 全量分析已有节点时弹出确认框，警告将删除全部已有节点
- 手动移除素材复用 AddAssetModal 组件，支持多选批量取消分配
- 新建节点支持"保存并分析"：创建后自动分析追加
- 云图聚合节点圆圈内显示素材数量（白色粗体），颜色随素材数量梯度变化
- 未分配节点也显示素材数量
- MCP 新增 trigger_scan / get_aggregation_status / reanalyze_asset / add_asset_tag / remove_asset_tag / get_stats 工具，总计 21 个工具
- MCP `analyze_append_node` 阻塞 30s，`run_aggregation` 阻塞 300s（full/full_append/append），详见 ADR-0001

## Testing Decisions

- 最高 seam：API 端点（`POST/DELETE/GET /api/nodes`，`POST /api/nodes/{id}/analyze-append`）
- 次高 seam：MCP 工具（通过 stdio 调用验证工具输出结构）
- 前端组件测试：NodePanel 右键菜单交互、弹框/Toast 组件渲染
- 参考现有测试：`tests/test_v12.py`，V14 新增 `tests/test_v14.py`

## Out of Scope

- 节点分析追加不支持用户确认再添加（自动完成）
- 不修改其他聚合模式（full/full_append/append）的行为
- 不添加节点排序/搜索功能
- 不添加节点内素材的批量移除

## Further Notes

- 删除节点的修复同时也覆盖了 create/update/assign 端点的同类 asyncio.run() 问题
- Toast 组件作为通用组件抽取，后续所有提示均可复用

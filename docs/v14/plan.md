# V14 — 节点增强 + MCP 完善

> grill-me 访谈记录，2026-06-26

## 设计决策

| # | 决策 | 选项 | 结论 |
|---|------|------|------|
| 1 | 节点分析追加 UI | 菊花图标+hover tooltip | coral 旋转菊花 16px + hover 提示"分析中..." |
| 2 | 分析范围 | 全库未连接 vs 仅未分配 | 全库所有未连接到此节点的素材 |
| 3 | 分析结果处理 | 自动添加 vs 用户确认 | 自动添加 |
| 4 | 无可分析素材 | 提示 | toast "无可分析的素材" |
| 5 | 新建节点 UI | 编辑弹框复用 | 复用现有弹框，标题"新建节点"，空字段 |
| 6 | 删除节点修复 | 后端 asyncio | `def` → `async def`，`asyncio.run()` → `await` |
| 7 | 删除节点前端 | 选中状态清理 | 调 `onSelectNode(null)` |
| 8 | 删除确认弹框 | 设计风格 | 编辑弹框风格，显示节点名，删除中菊花 |
| 9 | 统一弹框 | 全部替换 | confirm→设计弹框，alert→顶部居中 toast |
| 10 | Toast 样式 | 顶部居中，coral 色 | 2.5s 自动消失，z-index 最高 |
| 11 | 去掉配置引导 | 删 fetch+sso(true) | 仅去自动弹窗，保留其他逻辑 |
| 12 | MCP 节点工具 | 7 个工具 | list/get/create/update/delete/add_assets/analyze_append |
| 13 | MCP analyze_append_node | 阻塞 vs 异步 | 阻塞 30s（ADR-0001） |
| 14 | 分析追加 prompt | 放 aggregation/prompts.py | 新增 `build_append_prompt()` |
| 15 | 分析追加模型 | 复用现有 | text 模型配置 |
| 16 | 右键菜单位置 | "重命名"和"手动添加"之间 | 逻辑分组 |
| 17 | 手动移除素材 | 右键菜单 | 放在"手动添加素材"下方，复用 AddAssetModal mode="remove" |
| 18 | 全量分析确认 | ConfirmModal | 已有节点时弹出警告确认 |
| 19 | 保存并分析 | 弹框按钮 | 新建节点时显示，创建后自动分析追加 |
| 20 | 云图节点计数 | 圆圈内数字 | 聚合+未分配节点显示素材数量，白色粗体 |
| 21 | 云图颜色梯度 | HSL 动态 | 素材越多颜色越深（浅珊瑚→深珊瑚） |
| 22 | 云图尺寸放大 | radius/count | 倍数 4→5, 上限 40→55, 连线 +60→+80 |
| 23 | MCP 扩展 | +6 工具 | trigger_scan/status/reanalyze/tag/stats/remove_tag |
| 24 | 聚合 MCP 阻塞 | full/full_append/append | 三种模式均阻塞等待完成（300s 超时） |

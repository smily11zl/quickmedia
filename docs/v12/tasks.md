# QuickMedia v12 任务拆分 ✅ 全部完成

## Slice 12.1 — 数据库新增 + 删除级联 ✅

**目标：** 新增 `aggregation_queue`、`nodes`、`node_assets` 三张表，`delete_asset_full` 补 `node_assets` 级联删除。

- [x] `database.py` schema 初始化新增 aggregation_queue / nodes / node_assets 表
- [x] `asset_ops.py` delete_asset_full() 补 `DELETE FROM node_assets WHERE asset_id=?`
- [x] 测试: 表创建 / node_assets 级联删除 / aggregation_queue 读写

---

## Slice 12.2 — Prompt 构建 + AI 调用 ✅

**目标：** 三种模式 prompt 构建，复用现有 OpenAIAdapter/OllamaAdapter 调用 AI。

- [x] `quickmedia/aggregation/__init__.py`
- [x] `quickmedia/aggregation/prompts.py`: build_prompt(mode, assets, nodes)
- [x] `quickmedia/aggregation/worker.py`: 共享工具函数 (mark_*/get_all_*/save_*)
- [x] `quickmedia/aggregation/api.py`: POST /api/aggregation/run 直接 spawn 线程执行
- [x] 复用 OpenAIAdapter.chat() / OllamaAdapter.chat()，避免手写 HTTP
- [x] 测试: 三种 mode prompt 输出正确 / 队列状态管理

**架构演变：** 最初设计为独立 Worker 进程轮询队列，后简化为点击时 spawn daemon 线程执行。`aggregation_queue` 表仅用于状态追踪和防重复提交。

---

## Slice 12.3 — API 端点 ✅

**目标：** 聚合任务提交/状态查询 + 节点 CRUD + 手动关联端点。

- [x] `quickmedia/aggregation/api.py`: register_aggregation_routes()
- [x] POST /api/aggregation/run — 提交任务 (单任务互斥，spawn 线程执行)
- [x] GET /api/aggregation/status — 查询当前任务状态
- [x] GET /api/nodes — 节点列表 (含素材数，按素材数降序)
- [x] POST /api/nodes — 创建节点
- [x] PUT /api/nodes/{id} — 编辑节点
- [x] DELETE /api/nodes/{id} — 删除节点 (级联 node_assets)
- [x] POST /api/nodes/{id}/assets — 手动关联素材
- [x] DELETE /api/nodes/{id}/assets/{asset_id} — 取消关联
- [x] GET /api/nodes/{id}/assets — 节点下素材列表
- [x] `server.py` create_app() 中注册路由
- [x] POST /api/file-picker — macOS Finder 选择文件
- [x] POST /api/scan-file — 单文件扫描入库
- [x] POST /api/scan-folder — 目录扫描入库 (max_depth=3)
- [x] 测试: 全部端点 + 单任务互斥 + 数据正确性

---

## Slice 12.4 — 前端 NodePanel + 侧边栏 Tab ✅

**目标：** 侧边栏顶部双 Tab 切换，Tab2 展示 NodePanel。

- [x] App.tsx: 侧边栏加入 Tab 切换 (activeTab state)
- [x] NodePanel.tsx: 节点列表 + 右键菜单 + 聚合完成自动刷新
- [x] 操作按钮 (全量分析/全量追加/追加分析，动态显示)
- [x] 状态横幅 + 轮询 /api/aggregation/status (3s)
- [x] 节点点击 → 右侧素材面板显示节点素材
- [x] 测试: vitest 9 tests

---

## Slice 12.5 — 前端 AddAssetModal + 手动管理 ✅

**目标：** 手动添加素材弹窗 + 节点编辑弹窗。

- [x] AddAssetModal.tsx: 搜索框 + 全量素材列表 + 多选 + 确认
- [x] 节点右键菜单: 重命名/编辑描述/删除/手动添加素材
- [x] 节点编辑弹窗
- [x] 测试: vitest 6 tests

---

## Slice 12.6 — 集成测试 + 全链路验证 ✅

- [x] `tests/test_v12.py`: 28 tests (数据库/Prompt/API/Worker)
- [x] `frontend/tests/NodePanel.test.tsx`: 9 tests
- [x] `frontend/tests/AddAssetModal.test.tsx`: 6 tests
- [x] 全量回归: 220/243 (0 new failures)
- [x] Scanner 重构: 提取 `_ingest_file()` 共享方法，修复 scan_file 4 个 bug
- [x] 同步更新 CONTEXT.md / PRD.md / ROADMAP.md

---

## 额外修复

- **Scanner.scan_file bug 修复：** `hash_file`→`self._compute_hash`，`_os.time`→`datetime.now()`，`ext`→`extension`，`indexed_at`→`scanned_at`
- **Scanner 重构：** 提取 `_insert_asset()` 和 `_ingest_file()`，scan_directory 和 scan_file 共享同一逻辑
- **聚合线程模型：** 从常驻 Worker 改为按需 spawn daemon 线程
- **追加分析优化：** 未分配素材为 0 时跳过 AI 调用
- **全量分析清空：** full 模式先 DELETE nodes 再 INSERT
- **AI 调用复用：** 使用 OpenAIAdapter.chat() / OllamaAdapter.chat()
- **扫描弹窗：** 三种扫描方式 (配置路径/选择文件/选择文件夹)
- **日志：** 7 个关键节点日志覆盖全流程

## v12 测试覆盖

| 来源 | 数量 | 通过 |
|------|------|------|
| tests/test_v12.py | 28 | 28 |
| frontend/tests | 15 | 15 |
| **总计** | **43** | **43/43** |
| 全量回归 | 243 | 220 (0 新增失败) |

# QuickMedia v11 任务拆分 ✅ 全部完成

## Slice 11.1 — MCP server 骨架 + CLI ✅

**目标：** FastMCP 驱动、CLI 子命令、Hermes 配置。

- [x] `quickmedia/mcp_server.py`: FastMCP 框架，6 工具骨架
- [x] `quickmedia/cli.py`: `quickmedia mcp` 子命令
- [x] `pyproject.toml`: `mcp` 可选依赖
- [x] Hermes config: `command: "quickmedia" args: ["mcp"]`
- [x] `/reload-mcp` 热加载支持

## Slice 11.2 — 核心查询工具 ✅

**目标：** search_assets / get_asset / find_similar 完整实现。

- [x] `search_assets`: keyword(分词+FTS) / semantic(向量) / combined(RRF融合) 三模式
- [x] `get_asset`: 单/批量查询，返回完整详情+标签
- [x] `find_similar`: ChromaDB 向量多词查询合并去重
- [x] `list_assets`: 类型+标签联合筛选

## Slice 11.3 — 管理工具 + 批量操作 ✅

**目标：** add_asset / delete_asset + 批量支持。

- [x] `add_asset`: 路径为文件→单文件添加(scan_file)；目录→递归扫描(scan_directory)
- [x] `delete_asset`: 完整清理(assets/asset_tags/search_terms/ai_queue/ChromaDB)
- [x] 批量: `get_asset(asset_ids=[...])` / `delete_asset(asset_ids=[...])`

## Slice 11.4 — 架构重构 + Bug 修复 ✅

**目标：** 消除重复代码，修复 4 个协议 bug。

- [x] `quickmedia/search.py`: 共享搜索引擎 + `get_embedding_adapter`
- [x] `quickmedia/asset_ops.py`: 共享资产操作(delete_asset_full/get_asset_detail)
- [x] `quickmedia/scanner.py`: `scan_file` 单文件添加方法
- [x] `api/server.py`: delete 端点复用 asset_ops
- [x] 修复: search_assets mode 参数接入 / list_assets tags 接入 SQL
- [x] 修复: add_asset 只添加单文件(非目录) / delete_asset 完整清理
- [x] 修复: test_v10.py Config() 污染用户配置 → Config(config_dir=tmp)

## Slice 11.5 — Pydantic 结构化输出 ✅

**目标：** 协议层暴露完整字段结构。

- [x] `AssetDetail` / `AssetBasic` / `Tag` / `ActionResult` / `ScanResult` Pydantic 模型
- [x] 全部 40 个字段使用 `Field(description=...)` 协议可见
- [x] 修复: `ext`→`extension` 数据库列名对齐 / `duration: float` / `modified_at: str`
- [x] `AssetBasic` 添加 `path` 字段

## v11 测试覆盖

| 测试类 | 数量 | 覆盖 |
|--------|------|------|
| TestV11MCPCommand | 1 | CLI 子命令 |
| TestV11MCPServerStartup | 2 | 进程启动+工具列表 |
| TestV11Tools | 2 | 工具调用(空查询/不存在ID) |
| TestV11ToolBugs | 4 | 4 个协议 bug 修复验证 |
| **总计** | **9** | 9/9 passed |

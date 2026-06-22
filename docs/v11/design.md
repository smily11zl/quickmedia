# QuickMedia v11 技术方案 ✅ 完成

## 涉及模块

| 文件 | 变更 |
|------|------|
| quickmedia/mcp_server.py | FastMCP 6 工具 + Pydantic 模型（新增） |
| quickmedia/search.py | 共享搜索引擎 + get_embedding_adapter（新增） |
| quickmedia/asset_ops.py | 共享资产操作: delete_asset_full/get_asset_detail（新增） |
| quickmedia/scanner.py | scan_file 单文件添加方法 |
| quickmedia/cli.py | mcp 子命令 |
| quickmedia/api/server.py | delete 端点复用 asset_ops, search 嵌入适配器复用 |
| pyproject.toml | mcp 可选依赖 |
| tests/test_v11.py | 9 个测试 |

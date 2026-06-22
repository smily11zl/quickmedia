# QuickMedia v11 — MCP 接 Hermes 对话式素材管理

> 需求访谈记录。grill-me 时间：2026-06-22。✅ 完成

## 设计决策

### 1. MCP 协议库

使用 `mcp` Python 官方库（和 Hermes 客户端同库）。

### 2. 启动命令

新增 `quickmedia mcp` CLI 子命令。Hermes 配置：

```yaml
mcp_servers:
  quickmedia:
    command: "quickmedia"
    args: ["mcp"]
```

### 3. 数据目录

默认 `~/.asset-manager/`，和 Web 版共享数据库、ChromaDB、配置文件。可通过 `QUICKMEDIA_HOME` 环境变量覆盖。

### 4. 工具列表（6 个）

| 工具 | 功能 | 参数 |
|------|------|------|
| `search_assets` | 语义搜索素材 | query, mode, limit |
| `get_asset` | 获取素材详情 | asset_id |
| `list_assets` | 按条件列出素材 | type, tags, limit |
| `find_similar` | 找相似素材 | asset_id, limit |
| `add_asset` | 手动添加素材 | path |
| `delete_asset` | 删除素材 | asset_id |

### 5. 初始化

MCP server 启动时自动调用 `Database()` + `Config()`，和 Web 版共享初始化逻辑。无需依赖 Web 先启动。

### 6. 错误处理

预期错误（文件不存在、搜索无结果）→ `{"error": "原因"}` JSON。意外异常抛出让 Hermes 打印日志。

### 7. 零配置开箱

`pip install quickmedia` → Hermes 加 3 行配置 → 重启即可用。新用户无需手动初始化数据库。

## 涉及文件

| 文件 | 变更 |
|------|------|
| `quickmedia/mcp_server.py` | MCP server 主文件（新增，~80 行） |
| `quickmedia/cli.py` | 加 `mcp` 子命令 |
| `pyproject.toml` | 加 `mcp` 可选依赖 |

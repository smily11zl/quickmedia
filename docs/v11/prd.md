# QuickMedia v11 PRD ✅ 完成

# QuickMedia v11 PRD — MCP 对话式素材管理

## Problem Statement

用户在 Hermes Agent 对话中想搜素材、取文件、找相似，必须切换到 QuickMedia Web 界面手动操作。两个工具割裂，工作流打断。

## Solution

QuickMedia 作为 MCP server 接入 Hermes。用户在 Hermes 对话中自然语言搜素材（"找一张狗的图片"），Agent 自动调用 QuickMedia 工具返回结果。零切换，一个对话窗口完成。

## User Stories

1. 作为 Hermes 用户，我在对话中说"找一张蓝色的图"，Agent 自动调 search_assets 返回匹配素材
2. 作为 Hermes 用户，我选中一个素材后可以查看它的描述、标签、路径
3. 作为 Hermes 用户，我可以说"找和这张类似的图"，Agent 调 find_similar 返回候选
4. 作为 Hermes 用户，我可以让 Agent 列出所有图片/视频/文档类型的素材
5. 作为新用户，安装 QuickMedia 后只需在 Hermes 加 3 行配置即可使用 MCP
6. 作为新用户，首次使用无需手动初始化数据库——MCP server 启动时自动建库
7. 作为开发者，MCP server 失败时 Hermes 不会崩溃，只提示"QuickMedia 不可用"
8. 作为用户，搜索无结果时收到明确的"未找到匹配素材"提示，不卡住

## Implementation Decisions

- **MCP 库**：`mcp` Python 官方库，Hermes 客户端同库，协议兼容性保证
- **启动方式**：`quickmedia mcp` CLI 子命令，stdio 传输
- **Hermes 配置**：
  ```yaml
  mcp_servers:
    quickmedia:
      command: "quickmedia"
      args: ["mcp"]
  ```
- **数据目录**：默认 `~/.asset-manager/`，通过 `QUICKMEDIA_HOME` 覆盖
- **初始化**：启动时自动调 `Database()` + `Config()`，复用现有逻辑，无需 Web 版先启动
- **工具实现**：6 个工具函数 ≈ 10 行/个，复用现有 `api/server.py` 的同名逻辑
- **错误处理**：预期错误返回 `{"error": "..."}` JSON，意外异常抛出让 Hermes 打印
- **新增文件**：`quickmedia/mcp_server.py`（~80 行）
- **修改文件**：`quickmedia/cli.py`（加 `mcp` 子命令，~10 行）、`pyproject.toml`（加 `mcp` 可选依赖）

## Testing Decisions

- **集成测试**：spawn `quickmedia mcp` 子进程 → `list_tools()` 发现 6 个工具 → 调各工具验证返回
- **单元测试**：直接调 handler 函数验证搜索/详情/相似逻辑
- **CLI 测试**：验证 `quickmedia mcp` 子命令注册
- **参考**：`test_v8_search.py` 的 HTTP 测试风格，`test_v10.py` 的 Config 测试

## Out of Scope

- MCP server 热加载（需重启 Hermes 才生效）
- HTTP/SSE 传输（仅 stdio）
- 工具参数复杂筛选（list_assets 仅支持 type/tags/limit）
- 素材上传/修改（仅查询类工具）

## Further Notes

- 安装 `pip install mcp` 后依赖生效
- 与 QuickMedia Web 版共享同一套数据库
- Hermes 用户无需理解 QuickMedia 技术术语，自然语言即可驱动

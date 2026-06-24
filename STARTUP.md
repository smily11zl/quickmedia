# QuickMedia 启动指南

本地素材管理工具 — 扫描、标签、AI 分析。

## 环境要求

- Python 3.11+
- Node.js（前端构建）
- ffmpeg（视频元数据/首帧提取）
- Ollama（AI 分析，可选）

## 依赖安装

### Python 依赖

项目自带 `pyproject.toml`，推荐使用虚拟环境安装：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
```

### 系统依赖

```bash
# ffmpeg（视频处理）
brew install ffmpeg

# Ollama + AI 模型（可选，AI 功能需要）
brew install ollama
ollama serve &
ollama pull qwen3.5:9b
ollama pull qwen3-embedding:8b  # 语义搜索嵌入模型
```

### 前端构建（开发时，已构建则跳过）

```bash
cd frontend
npm install
npm run build
```

## 启动

```bash
cd /Users/zengle/Documents/quickmedia

# 方式一：使用项目虚拟环境
.venv/bin/quickmedia serve

# 方式二：直接调用
.venv/bin/python -m quickmedia serve

# 指定端口
.venv/bin/quickmedia serve 8088
```

启动后自动：
1. 扫描配置的监控路径
2. 生成缩略图
3. 启动 fsevents 文件监听
4. 打开浏览器访问 `http://localhost:8088`

## CLI 命令

```bash
quickmedia scan <路径>      # 扫描目录
quickmedia list [--type image]  # 列出素材
quickmedia search <关键词>      # 搜索
quickmedia tag <ID> <标签>      # 打标签
quickmedia edit <ID>            # 编辑描述
quickmedia stats                # 统计
quickmedia serve [端口]         # Web UI
quickmedia mcp                  # 启动 MCP server (供 AI Agent 调用)
```

## MCP 集成（AI Agent 对话式素材管理）

QuickMedia 可作为 MCP server 供 Hermes / Claude Desktop / Codex CLI 等 AI 工具调用。

### Hermes 配置

编辑 `~/.hermes/config.yaml`，添加：

```yaml
mcp_servers:
  quickmedia:
    command: "/path/to/quickmedia/.venv/bin/python"
    args: ["-m", "quickmedia.mcp_server"]
```

替换 `/path/to/quickmedia` 为实际项目路径。重启 Hermes 即可使用 `search_assets`、`get_asset`、`list_assets`、`find_similar`、`add_asset`、`delete_asset` 等工具。

### Claude Desktop 配置

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "quickmedia": {
      "command": "/path/to/quickmedia/.venv/bin/python",
      "args": ["-m", "quickmedia.mcp_server"]
    }
  }
}
```

重启 Claude Desktop 后，在对话中可直接搜索和管理素材。

### Codex CLI 配置

```bash
codex mcp add quickmedia -- /path/to/quickmedia/.venv/bin/python -m quickmedia.mcp_server
```

## 配置

配置文件：`~/.asset-manager/config.yaml`

监控路径配置示例：

```bash
# 用 CLI 设置
python -m quickmedia config
```

或编辑 `~/.asset-manager/config.yaml`：

```yaml
ai:
  ollama_url: http://localhost:11434
  model: qwen3.5:9b
watch_paths:
  - path: ~/Desktop/test_media
    recursive: true
    max_depth: 2
```

## 测试

```bash
cd /Users/zengle/Documents/quickmedia
python -m pytest tests/ -q
```

## 项目结构

```
quickmedia/
├── quickmedia/          # Python 后端
│   ├── cli.py           # CLI 入口
│   ├── config.py        # 配置管理
│   ├── database.py      # SQLite 数据库
│   ├── scanner.py       # 扫描引擎
│   ├── metadata.py      # 元数据提取
│   ├── thumbnailer.py   # 缩略图生成
|   ├── ai.py            # AI 视觉/文本分析
|   ├── watcher.py       # fsevents 监听
|   ├── aggregation/     # V12 素材聚合
|   ├── mcp_server.py    # MCP server
|   └── api/server.py    # FastAPI 服务
├── frontend/            # React 前端
|   ├── dist/            # 构建输出
|   └── tests/           # 前端测试 (vitest)
├── tests/               # Python 测试
├── docs/                # 版本文档 (v1-v12)
├── CONTEXT.md           # 领域术语表
├── PRD.md               # 产品需求（全版本）
├── ROADMAP.md           # 版本路线图
├── STARTUP.md           # 启动指南
├── DESIGN.md            # UI 设计规范
└── AGENTS.md            # AI Agent 项目指南
```

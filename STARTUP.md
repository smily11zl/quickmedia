# QuickMedia 启动指南

本地素材管理工具 — 扫描、标签、AI 分析。

## 环境要求

- Python 3.11+
- Node.js（前端构建）
- ffmpeg（视频元数据/首帧提取）
- Ollama（AI 分析，可选）

## 依赖安装

### Python 依赖

```bash
pip install pyyaml pillow fastapi uvicorn watchdog
```

或使用项目提供的虚拟环境（推荐）：

```bash
~/.hermes/hermes-agent/.venv/bin/pip install pyyaml pillow fastapi uvicorn watchdog
```

### 系统依赖

```bash
# ffmpeg（视频处理）
brew install ffmpeg

# Ollama + AI 模型（可选，AI 功能需要）
brew install ollama
ollama serve &
ollama pull qwen3.5:9b
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

# 方式一：系统 Python
python3 -m quickmedia serve

# 方式二：Hermes 虚拟环境
~/.hermes/hermes-agent/.venv/bin/python -m quickmedia serve

# 指定端口
~/.hermes/hermes-agent/.venv/bin/python -m quickmedia serve 8088
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
│   ├── ai.py            # AI 视觉/文本分析
│   ├── watcher.py       # fsevents 监听
│   └── api/server.py    # FastAPI 服务
├── frontend/            # React 前端
│   └── dist/            # 构建输出
├── tests/               # 测试
├── QUICKMEDIA_DESIGN.md # 设计文档
├── DESIGN.md            # UI 设计规范
└── TASKS.md             # 任务文档
```

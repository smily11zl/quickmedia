# QuickMedia

本地素材管理工具 — 扫描、标签、搜索，AI 驱动的素材索引系统。

## 功能

- **扫描索引** — SHA256 去重 + inode 追踪，不碰原文件
- **元数据提取** — 图片尺寸、视频分辨率/时长、音频信息
- **AI 分析** — 图片场景描述 + 元素标签，文档摘要 + 关键词（Qwen 3.5 本地模型）
- **全文搜索** — 按文件名、描述、标签、AI 摘要搜索
- **扁平标签** — 手动打标 + AI 自动标签，多选交集筛选
- **Web UI** — 网格/列表视图，详情面板，标签管理，暖色调设计
- **实时监听** — fsevents 文件增删改自动感知
- **缩略图** — 异步生成，256px

## 快速开始

```bash
# 安装依赖
pip install pyyaml pillow fastapi uvicorn watchdog

# 扫描素材
python -m quickmedia scan ~/Desktop/test_media

# 启动 Web UI
python -m quickmedia serve
# → http://localhost:8088
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `scan <路径>` | 扫描目录 |
| `list [--type image]` | 列出素材 |
| `search <关键词>` | 搜索 |
| `tag <ID> <标签>` | 打标签 |
| `edit <ID>` | 编辑描述 |
| `stats` | 统计 |
| `serve [端口]` | 启动 Web UI |

## AI 分析（可选）

需要 Ollama + Qwen 3.5：

```bash
ollama serve &
ollama pull qwen3.5:9b
```

扫描时自动对图片、视频、文档进行 AI 分析。

## 技术栈

Python / FastAPI / SQLite / React / TailwindCSS / Ollama

## 详细文档

- [设计文档](docs/v1/design.md)
- [UI 设计规范](DESIGN.md)
- [启动指南](STARTUP.md)
- [任务文档](docs/v1/tasks.md)
- [路线图](ROADMAP.md)

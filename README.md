# QuickMedia

本地素材管理工具 — 扫描、标签、AI 分析。支持本地 + 云端多模型。

## 功能

- **素材扫描** — SHA256 去重 + inode 追踪，不碰原文件
- **元数据提取** — 图片尺寸、视频分辨率/时长、音频信息
- **AI 分析（多模型）** — 图片场景描述 + 标签 + OCR，文档摘要 + 关键词，语音转写 + 摘要，视频帧分析 + 综合总结
- **多模型支持** — Ollama / DeepSeek / OpenRouter / OpenAI / MiniMax，不同任务可选不同模型
- **自定义 Prompt** — 每个分析类型可编辑分析指令、切换预设模板
- **全文搜索** — 按文件名、描述、标签、AI 摘要搜索
- **标签系统** — 手动打标 + AI 自动标签，多选筛选
- **Web UI** — 网格/列表视图，详情面板，暖色调设计

## 快速开始

### 系统依赖

```bash
# macOS
brew install ffmpeg   # 视频缩略图、元数据提取

# Linux
sudo apt install ffmpeg
```

### 安装

```bash
# 进入项目目录，创建虚拟环境
cd quickmedia
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e ".[all]"

# 扫描素材目录
quickmedia scan ~/Desktop/test_media

# 启动 Web UI
quickmedia serve
# → http://localhost:8088
```

## 数据存储

所有索引和配置文件存储在 `~/.asset-manager/`：

| 文件 | 说明 |
|------|------|
| `data.db` | SQLite 素材索引 |
| `config.yaml` | 应用配置（端口、监视路径、Provider） |
| `.env` | API Key（远端模型需要） |
| `prompts.yaml` | AI 分析提示词模板 |
| `models.yaml` | 可用模型目录 |
| `thumbnails/` | 缩略图缓存 |

## AI 分析

### 本地模型（Ollama）

```bash
brew install ollama
ollama serve &
ollama pull qwen3.5:9b
```

启动后 QuickMedia 自动检测并连接。

### 远端模型

支持 DeepSeek / OpenRouter / OpenAI / MiniMax。在 Web UI **设置 → 模型管理** 中添加 Provider 并填入 API Key。Key 存储在 `~/.asset-manager/.env`：

```
DEEPSEEK_API_KEY=***
OPENROUTER_API_KEY=***
MINIMAX_API_KEY=***
OPENAI_API_KEY=***
```

### 分析类型

| 类型 | 适用素材 | 分析内容 |
|------|---------|---------|
| 图片分析 | jpg/png/webp/gif | 场景描述、元素标签、OCR 文字 |
| 文档分析 | txt/md/pdf | 摘要、关键词 |
| 语音分析 | wav/mp3/m4a | Whisper 转写 + 摘要 |
| 视频分析 | mp4/mov/avi | 帧分析 + 语音总结 |

每种分析类型可在设置中绑定不同模型，例如图片用 GPT-4o、文档用 DeepSeek。

## CLI 命令

| 命令 | 说明 |
|------|------|
| `quickmedia scan <路径>` | 扫描目录 |
| `quickmedia stats` | 统计 |
| `quickmedia list [--type image]` | 列出素材 |
| `quickmedia search <关键词>` | 搜索 |
| `quickmedia serve [端口]` | 启动 Web UI（默认 8088） |
| `quickmedia tag <ID> <标签>` | 打标签 |
| `quickmedia edit <ID>` | 编辑描述 |

## 技术栈

Python / FastAPI / SQLite / React / TailwindCSS / Ollama / faster-whisper

## 文档

- [启动指南](STARTUP.md) — 环境要求、依赖安装细节
- [设计规范](DESIGN.md) — UI 色彩、字体、组件规范
- [路线图](ROADMAP.md) — 版本计划和已完成功能
- [领域术语](CONTEXT.md) — Asset、Scan、Provider 等概念
- [设计文档](docs/v1/design.md) — 技术方案（schema/API/架构）

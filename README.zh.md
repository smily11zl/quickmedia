# QuickMedia

[English](README.md) | 中文

本地素材管理工具 — 扫描、标签、AI 分析、语义搜索、素材聚合。

## 核心功能

### 素材扫描与管理
- 目录扫描（SHA256 去重 + inode 追踪）
- 实时文件监听（fsevents）
- 元数据提取（图片尺寸、视频分辨率/时长、音频信息）
- 缩略图异步生成
- 手工扫描（Web UI 点击触发，支持配置路径 / 选择文件 / 选择文件夹）
- 素材删除（仅移除索引，源文件不受影响）

### AI 智能分析
- 图片视觉描述 + 元素标签
- 视频多帧采样 + 首帧分析 + 综合总结
- 音频/视频语音转录（whisper，可通过模型管理配置）
- 语音总结分析（基于转录文本的 LLM 分析）
- 文档摘要 + 关键词
- OCR 图片文字提取
- AI 任务队列（异步，不阻塞扫描）
- 重试机制（3 次，2s 间隔）+ 手动重试/重新分析
- 自定义 AI Prompt（图片/文档/语音/视频四类独立模板 + 预设）
- 多模型支持（Ollama / OpenAI / DeepSeek / OpenRouter / MiniMax / Whisper）
- 任务模型绑定，按能力过滤（每个任务仅显示兼容模型）

### 搜索
- 语义搜索（ChromaDB 向量，`qwen3-embedding`）
- RRF 融合排序（BM25 关键词 + 语义向量混合）
- 三种模式：综合 / 语义 / 匹配
- jieba 中文分词
- 搜索结果关键词高亮
- 相似素材推荐（详情页叠加层）

### 标签系统
- 三种来源：auto（系统自动）/ ai（AI 生成）/ manual（手动）
- 扁平结构（无层级），取并集筛选
- AI 标签确认/删除

### 素材聚合（v12-v14）
- AI 自动聚类：全量分析 / 全量追加 / 追加分析
- 聚合节点多对多关联（素材可属于多个节点）
- 侧边栏双 Tab：搜索筛选 / 聚合节点
- 节点管理：新建、重命名、编辑描述、删除
- 手动添加/移除素材（多选批量操作）
- 节点分析追加：AI 自动匹配未连接素材到节点
- 选中节点状态持久（跨 Tab 保留，主内容区清除条）
- 全量分析确认（防止误删已有节点）

### 云图（v13）
- 力导向图可视化节点-素材关系
- 视图切换三按钮：☁ 云图 / ▦ 网格 / ☰ 列表
- 聚合节点按素材数量缩放 + 颜色深度梯度
- 节点圆圈内显示素材数量
- 素材节点按类型着色，zoom 自适应缩略图
- 展开/折叠素材节点、共享边（粗细=共享素材数）
- 未分配节点（蓝色虚线）
- 搜索高亮 + WebSocket 增量推送

### 筛选
- 类型筛选（图片/视频/音频/文档），数量实时反映当前结果集
- 创建/修改时间日期区间
- 文件格式下拉多选
- AI 状态下拉多选（已完成/分析中/等待/失败）
- 标签多选筛选（取并集）
- 批量选择 + 重新分析
- 排序（名称/大小/时间）

### MCP 工具（v11/v14）
- FastMCP 驱动，stdio 传输
- 21 个工具：素材管理（6）+ 聚合节点管理（8）+ 聚合分析 + 扫描 + 标签管理 + 统计 + 重分析
- Hermes / Claude Desktop / Codex CLI 均可用

### Web UI
- 设置页面：监控路径配置、模型管理、AI Prompt 模板
- 文档预览（txt/md/docx），素材详情（路径/尺寸/时长/AI 结果）
- 批量操作（多选 + 重新分析）

## 安装

### 快速安装（macOS/Linux）

```bash
chmod +x scripts/setup.sh && ./scripts/setup.sh
```

### 基础环境

- Python 3.11+
- ffmpeg（视频元数据、缩略图提取）

```bash
# macOS
brew install ffmpeg

# Linux (Debian/Ubuntu)
sudo apt install ffmpeg

# Windows
# 下载 https://ffmpeg.org/download.html 或 winget install ffmpeg
```

### Python 包安装

核心依赖（必装）：Pillow、PyYAML、watchdog

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"   # 安装全部功能包
```

可选按需安装，替代 `[all]`：

```bash
pip install -e ".[web]"        # Web UI（FastAPI + Uvicorn）
pip install -e ".[audio]"      # 语音转录（Whisper）
pip install -e ".[text]"       # 文档解析（PyMuPDF + openpyxl）
pip install -e ".[embedding]"  # 语义搜索 + 聚合（ChromaDB + jieba）
pip install -e ".[mcp]"        # MCP 工具接口
```

### 前端构建

需要 Node.js。构建一次即可，产物在 `frontend/dist/` 下，运行时无需 Node。

```bash
cd frontend && npm install && npm run build && cd ..
```

### AI 模型（可选）

需要 Ollama 或其他兼容服务。未配置时 AI 分析/搜索功能不可用，素材管理、扫描功能正常。

```bash
# macOS
brew install ollama
ollama serve &

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# 下载 https://ollama.com/download/windows
```

拉取模型：
```bash
ollama pull qwen3.5:9b              # 视觉/文本分析
ollama pull qwen3-embedding:8b      # 语义搜索嵌入
```

## 启动

```bash
quickmedia serve
```

首次启动会自动弹出配置页面，添加监控文件夹后即可扫描。

## MCP 集成

### Hermes

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  quickmedia:
    command: "quickmedia"
    args: ["mcp"]
```

### Claude Desktop

```json
{
  "mcpServers": {
    "quickmedia": {
      "command": "quickmedia",
      "args": ["mcp"]
    }
  }
}
```

### Codex CLI

```bash
codex mcp add quickmedia -- quickmedia mcp
```

## 支持的模型

通过 Web UI 设置页 → 模型管理配置。不同分析任务可绑定不同模型。

| Provider | 模型 | 图片 | 视频 | 音频 | 文本 |
|----------|------|:----:|:----:|:----:|:----:|
| **Ollama** (本地) | `qwen3.5:9b` | ✓ | ✓ | | ✓ |
| | `qwen3-embedding:8b` | | | | 嵌入 |
| **OpenAI** | `gpt-4o` | ✓ | | | ✓ |
| | `gpt-4o-mini` | ✓ | | | ✓ |
| | `gpt-5.5` | ✓ | | | ✓ |
| | `gpt-5.4` | ✓ | | | ✓ |
| **DeepSeek** | `deepseek-chat` | | | | ✓ |
| | `deepseek-reasoner` | | | | ✓ |
| | `deepseek-v4-flash` | | | | ✓ |
| | `deepseek-v4-pro` | | | | ✓ |
| **OpenRouter** | `openai/gpt-4o` | ✓ | | | ✓ |
| | `openai/gpt-4o-mini` | ✓ | | | ✓ |
| | `anthropic/claude-sonnet-4` | ✓ | | | ✓ |
| | `anthropic/claude-haiku-4` | | | | ✓ |
| | `google/gemini-2.5-flash` | ✓ | ✓ | ✓ | ✓ |
| | `google/gemini-2.5-pro` | ✓ | ✓ | ✓ | ✓ |
| | `deepseek/deepseek-chat` | | | | ✓ |
| | `deepseek/deepseek-v4-pro` | | | | ✓ |
| | `deepseek/deepseek-r1` | | | | ✓ |
| | `qwen/qwen3.5-plus-02-15` | ✓ | ✓ | | ✓ |
| | `qwen/qwen3.5-max` | ✓ | ✓ | | ✓ |
| | `qwen/qwen3.5-coder` | | | | ✓ |
| | `qwen/qwen3.7-plus` | ✓ | ✓ | | ✓ |
| | `qwen/qwen3.7-max` | ✓ | ✓ | | ✓ |
| | `qwen/qwen3-embedding-8b` | | | | 嵌入 |
| | `openai/whisper-large-v3` | | | ✓ | |
| | `openai/whisper-large-v3-turbo` | | | ✓ | |
| | `qwen/qwen3-asr-flash` | | | ✓ | |
| | `anthropic/claude-haiku-4.5` | ✓ | | | ✓ |
| | `anthropic/claude-opus-4.7` | ✓ | | | ✓ |
| | `anthropic/claude-opus-4.8` | ✓ | | | ✓ |
| | `anthropic/claude-sonnet-4.6` | ✓ | | | ✓ |
| | `anthropic/claude-sonnet-5` | ✓ | | | ✓ |
| | `google/gemini-3-flash` | ✓ | ✓ | ✓ | ✓ |
| | `google/gemini-3.5-flash` | ✓ | ✓ | ✓ | ✓ |
| **MiniMax** | `MiniMax-M3` | | | | ✓ |
| | `MiniMax-M2.7` | | | | ✓ |
| | `MiniMax-M2.5` | | | | ✓ |
| | `MiniMax-M2.1` | | | | ✓ |
| | `MiniMax-M2` | | | | ✓ |
| | `MiniMax-M1` | | | | ✓ |
| **Whisper** (本地) | `small` | | | ✓ | |

> 嵌入模型用于语义搜索和素材聚合。图片/视频分析需要多模态模型。各 Provider 需要配置对应的 API Key。

## 数据存储

- 数据库：`~/.asset-manager/data.db`
- 配置文件：`~/.asset-manager/config.yaml`
- 模型目录：`~/.asset-manager/models.yaml`
- Prompt 模板：`~/.asset-manager/prompts.yaml`
- 向量库：`~/.asset-manager/chroma_db/`
- 缩略图：`~/.asset-manager/thumbnails/`

## 项目结构

```
quickmedia/
├── quickmedia/           # Python 后端
│   ├── api/server.py     # FastAPI 路由
│   ├── aggregation/      # 聚合模块（prompts/worker/api）
│   ├── database.py       # SQLite + 迁移
│   ├── scanner.py        # 文件扫描器
│   ├── search.py         # 语义搜索
│   ├── mcp_server.py     # MCP 服务（21 工具）
│   ├── ai.py             # AI 分析器
│   ├── cli.py            # CLI 入口
│   └── ...
├── frontend/             # React 前端
│   └── src/
│       ├── App.tsx       # 主组件
│       ├── GraphView.tsx # 云图视图
│       ├── NodePanel.tsx # 聚合节点面板
│       ├── AddAssetModal.tsx  # 添加/移除素材弹框
│       ├── Toast.tsx      # 消息提示
│       ├── ConfirmModal.tsx # 确认弹框
│       └── ...
├── tests/                # Pytest 测试
└── docs/v*/              # 版本文档（plan/PRD/design/tasks）
```

## 开发

```bash
# 运行测试
python -m pytest tests/ -q

# 前端开发模式
cd frontend && npm run dev

# 前端测试
cd frontend && npx vitest run
```

> ⚠️ 修改前端代码后，必须运行 `npm run build` 并将 `frontend/dist/` 提交到 Git。仓库内的 dist 是其他用户直接使用的构建产物，不更新会导致其他用户看到旧版 UI。

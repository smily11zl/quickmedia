[English](README.md) | [中文](README.zh.md)

# QuickMedia — Local Asset Intelligence

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-green)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-frontend-61dafb)](https://react.dev/)

Scan, tag, AI-analyze, semantically search, and aggregate your local assets.

## Core Features

### Asset Scanning & Management
- Directory scanning (SHA256 deduplication + inode tracking)
- Real-time file watching (fsevents)
- Metadata extraction (image dimensions, video resolution/duration, audio info)
- Async thumbnail generation
- Manual scanning (Web UI triggered, configurable paths / file selection / folder selection)
- Asset deletion (index only, source files unaffected)

### AI Analysis
- Image visual description + element tags
- Video multi-frame sampling + frame analysis + comprehensive summary
- Audio/video speech transcription (configurable: local Whisper or OpenRouter API)
- Speech summary analysis (LLM-powered transcript summarization)
- Document summaries + keywords
- OCR text extraction from images
- AI task queue (async, non-blocking during scanning)
- Retry mechanism (3 attempts, 2s interval) + manual retry/re-analyze
- Custom AI prompts (independent templates + presets for image/document/speech/video)
- Multi-model support (Ollama / OpenAI / DeepSeek / OpenRouter / MiniMax / Whisper)
- Task-to-model binding with capability filtering

### Search
- Semantic search (ChromaDB vectors, `qwen3-embedding`)
- RRF fusion ranking (BM25 keyword + semantic vector hybrid)
- Three modes: Combined / Semantic / Keyword
- jieba Chinese word segmentation
- Search result keyword highlighting
- Similar asset discovery (detail panel overlay)

### Tag System
- Three sources: auto (system) / ai (AI-generated) / manual (user-added)
- Flat structure (no hierarchy), union-based filtering
- AI tag confirmation / deletion

### Asset Aggregation (v12-v14)
- AI auto-clustering: Full analysis / Full append / Incremental append
- Aggregation node many-to-many associations (assets can belong to multiple nodes)
- Sidebar dual-tab: Search & Filter / Aggregation Nodes
- Node management: create, rename, edit description, delete
- Manual add/remove assets (multi-select batch operations)
- Node analyze-append: AI auto-matches unconnected assets to node
- Node selection persistence (across tabs, clear indicator in main area)
- Full analysis confirmation (prevents accidental deletion of existing nodes)

### Graph View (v13)
- Force-directed graph visualizing node-asset relationships
- Three view buttons: ☁ Graph / ▦ Grid / ☰ List
- Aggregation nodes scaled by asset count + color depth gradient
- Asset count inside node circles
- Asset nodes colored by type, zoom-adaptive thumbnails
- Expand/collapse asset nodes, shared edges (width = shared asset count)
- Unassigned node (blue dashed line)
- Search highlighting + WebSocket incremental updates

### Filtering
- Type filter (Image/Video/Audio/Document), counts reflect current result set
- Created/Modified date range pickers
- File format multi-select dropdown
- AI status multi-select (Done/Processing/Pending/Failed)
- Tag multi-select filter (union logic)
- Batch select + re-analyze
- Sort (name/size/modified/added/hot/score), unified across all search modes
- Hot sort: weighted by view_count + open_count×3, most-viewed first
- Score sort (semantic/combined modes): by vector relevance

### MCP Tools (v11/v14)
- FastMCP driven, stdio transport
- 22 tools: Asset management (6) + Node management (8) + Aggregation + Scan + Tags + Stats + Re-analyze
- Compatible with Hermes / Claude Desktop / Codex CLI

### Web UI
- Settings page: watch path configuration, model management, AI prompt templates
- Document preview (txt/md/docx), asset details (path/size/duration/AI results)
- High-res detail thumbnails (800px from original file, cached)
- View/open tracking (hot sort weighted)
- Batch operations (multi-select + re-analyze)
- i18n: English / Chinese (auto-detected from browser, adjustable in settings)

## Installation

### Quick Install (macOS/Linux)

```bash
chmod +x scripts/setup.sh && ./scripts/setup.sh
# Quick start after install:
chmod +x scripts/serve.sh && ./scripts/serve.sh
```

### Prerequisites

- Python 3.11+
- ffmpeg (video metadata, thumbnail extraction)

```bash
# macOS
brew install ffmpeg

# Linux (Debian/Ubuntu)
sudo apt install ffmpeg
```

### Python Packages

Core dependencies (required): Pillow, PyYAML, watchdog

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"   # all features
```

Optional installs (replace `[all]`):

```bash
pip install -e ".[web]"        # Web UI (FastAPI + Uvicorn)
pip install -e ".[audio]"      # Speech transcription (Whisper)
pip install -e ".[text]"       # Document parsing (PyMuPDF + openpyxl)
pip install -e ".[embedding]"  # Semantic search + aggregation (ChromaDB + jieba)
pip install -e ".[mcp]"        # MCP tool interface
```

### Frontend Build

Requires Node.js. Build once; output served from `frontend/dist/`. No Node needed at runtime.

```bash
cd frontend && npm install && npm run build && cd ..
```

### AI Models (Optional)

Requires Ollama or compatible service. Without configuration, AI analysis/search is unavailable but asset management and scanning work normally.

```bash
# macOS
brew install ollama
ollama serve &
```

Pull models:
```bash
ollama pull qwen3.5:9b              # vision/text analysis
ollama pull qwen3-embedding:8b      # semantic search embedding
```

## Quick Start

```bash
quickmedia serve
```

On first run, a config page opens automatically. Add watch folders to begin scanning.

## MCP Integration

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

## Supported Models

Configure via Web UI → Settings → Model Management. Different analysis tasks can bind different models.

| Provider | Model | Vision | Video | Audio | Text |
|----------|------|:------:|:-----:|:-----:|:----:|
| **Ollama** (local) | `qwen3.5:9b` | ✓ | ✓ | | ✓ |
| | `qwen3-embedding:8b` | | | | embed |
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
| | `qwen/qwen3-embedding-8b` | | | | embed |
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
| **Whisper** (local) | `small` | | | ✓ | |


> Embedding models are used for semantic search and aggregation. Vision/video analysis requires multimodal models. Each provider requires a corresponding API key.

## Data Storage

- Database: `~/.asset-manager/data.db`
- Config: `~/.asset-manager/config.yaml`
- Models: `~/.asset-manager/models.yaml`
- Prompt templates: `~/.asset-manager/prompts.yaml`
- Vector DB: `~/.asset-manager/chroma_db/`
- Thumbnails: `~/.asset-manager/thumbnails/`

## Project Structure

```
quickmedia/
├── quickmedia/           # Python backend
│   ├── api/server.py     # FastAPI routes
│   ├── aggregation/      # Aggregation module (prompts/worker/api)
│   ├── database.py       # SQLite + migrations
│   ├── scanner.py        # File scanner
│   ├── search.py         # Semantic search
│   ├── mcp_server.py     # MCP server (22 tools)
│   ├── ai.py             # AI analyzers
│   ├── ai_worker.py      # AI task queue worker
│   ├── cli.py            # CLI entry point
│   └── ...
├── frontend/             # React frontend
│   └── src/
│       ├── i18n.ts       # Internationalization
│       ├── locales/      # Translation files (zh/en)
│       ├── App.tsx       # Main component
│       ├── GraphView.tsx # Graph visualization
│       ├── NodePanel.tsx # Aggregation node panel
│       └── ...
├── tests/                # Pytest tests
└── docs/v*/              # Version docs (plan/PRD/design/tasks)
```

## Development

```bash
# Run tests
python -m pytest tests/ -q

# Frontend dev mode
cd frontend && npm run dev

# Frontend tests
cd frontend && npx vitest run
```

> ⚠️ After modifying frontend code, run `npm run build` and commit `frontend/dist/`. The dist in the repository is the built artifact used directly by other users; failing to update it will show stale UI.

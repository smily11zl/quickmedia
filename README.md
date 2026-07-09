[English](README.md) | [中文](README.zh.md)


# QuickMedia

## Your local AI-powered second brain for photos, videos and documents.

Transform your messy media folders into an intelligent knowledge base. Search, organize and understand your files with local AI.

![Stars](https://img.shields.io/github/stars/smily11zl/quickmedia?style=social)
![License](https://img.shields.io/github/license/smily11zl/quickmedia)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![React](https://img.shields.io/badge/React-Frontend-blue)
![Ollama](https://img.shields.io/badge/AI-Ollama-black)

[![FastAPI](https://img.shields.io/badge/FastAPI-backend-green)](https://fastapi.tiangolo.com/)

Scan, tag, AI-analyze, semantically search, and aggregate your local assets.

## ✨ Core Features

### 🧠 AI-Powered Media Understanding

QuickMedia uses multimodal AI models to understand your local files.

Automatically analyze:
- 🖼️ **Images** — generate descriptions, tags, and understand visual content
- 🎬 **Videos** — analyze key frames and understand video content
- 📄 **Documents** — extract summaries and important keywords
- 🔤 **OCR** — recognize text inside images
- 🎵 **Audio & Video** — convert speech into searchable text
- 📝 **AI Summaries** — summarize transcripts and extracted content

Your files become searchable by meaning, not just filenames.

Supports multiple AI providers:
- Local AI models through Ollama
- OpenAI-compatible APIs
- DeepSeek / OpenRouter / MiniMax
- Whisper speech recognition models

### 📂 Intelligent Asset Management

Automatically organize and index your growing media library.

Features:
- Scan folders and automatically index files
- Detect duplicate files using content hashing
- Monitor file changes in real time
- Extract metadata from images, videos, audio, and documents
- Generate thumbnails asynchronously
- Manage assets without modifying original files

Your original files stay untouched. QuickMedia only builds an intelligent index for them.

### 🔍 Natural Language Search

Find your files based on what they mean, not only their names.

Supports:
- Semantic search powered by AI embeddings
- Keyword search
- Hybrid search combining semantic and traditional search
- Chinese text understanding
- Search result highlighting
- Similar asset discovery

Examples:

"photos of my dog playing outside"

"documents about artificial intelligence"

"videos from my Japan trip"

### 🏷️ Smart Tag System

Organize your assets with flexible tags.

Supports:
- AI-generated tags
- System-generated tags
- User-created tags
- Tag-based filtering
- Batch tag management

Tags work together with AI search to improve asset discovery.

### 🧩 AI-Powered Asset Organization

Turn thousands of scattered files into meaningful collections.

QuickMedia can automatically discover relationships between your assets and create intelligent groups.

Features:
- AI-powered automatic clustering
- Create custom collections
- Assets can belong to multiple collections
- AI-assisted collection expansion
- Manual organization and editing

Example:

Travel
├── Chinese Travel
└── Family Trip

Pets
├── Dogs
└── Outdoor Activities

### 🕸️ Media Knowledge Graph

Explore your digital memories through relationships.

QuickMedia visualizes connections between:
- Images
- Videos
- Documents
- Topics
- Collections

Features:
- Interactive force-directed graph
- Expand and collapse relationships
- Visual asset grouping
- Search highlighting
- Multiple views:
  - Graph View
  - Grid View
  - List View

Your media library becomes a personal knowledge graph.

### 🎯 Advanced Filtering & Management

Quickly find and manage exactly what you need.

Filter by:
- File type:
  - Images
  - Videos
  - Audio
  - Documents
- Date range
- File format
- AI analysis status
- Tags
- Search relevance

Additional tools:
- Batch operations
- Re-analysis
- Multiple sorting options
- Most-used asset ranking

### 🤖 AI Agent Integration (MCP)

Control QuickMedia through AI assistants.

Built-in MCP support provides tools for:
- Asset search
- Asset management
- Collection management
- Folder scanning
- Tag operations
- Statistics
- AI re-analysis

Compatible with:
- Claude Desktop
- Codex CLI
- Hermes

### 🌐 Modern Web Interface

A full-featured local web application.

Includes:
- Asset dashboard
- Settings management
- Asset detail viewer
- Document preview
- High-resolution thumbnails
- Search and filtering interface
- Batch operations
- Multi-language support:
  - English
  - Chinese

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

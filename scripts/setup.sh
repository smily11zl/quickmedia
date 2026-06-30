#!/bin/bash
# QuickMedia one-click setup script
# Create venv, install deps, verify frontend dist.

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== QuickMedia Setup ===\n"

# 1. Create venv if missing
if [ ! -d ".venv" ]; then
    echo "→ Creating virtual environment..."
    python3 -m venv .venv
else
    echo "→ Virtual environment already exists at .venv/"
fi

# 2. Activate
source .venv/bin/activate

# 3. Install dependencies
echo "→ Installing Python dependencies..."
pip install --upgrade pip -q
pip install -e ".[all]" -q

# 4. Verify frontend dist
if [ -d "frontend/dist" ]; then
    echo "→ Frontend dist found. (Install Node.js + run 'cd frontend && npm run build' if you modify the UI.)"
else
    echo "→ Frontend dist NOT found. Build it: cd frontend && npm install && npm run build"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Start:   .venv/bin/quickmedia serve"
echo "MCP:     .venv/bin/quickmedia mcp"
echo "Tests:   .venv/bin/python -m pytest tests/ -q"
echo ""

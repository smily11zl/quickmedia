#!/bin/bash
# QuickMedia — auto-build frontend and serve
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "[QuickMedia] Building frontend..."
cd "$PROJECT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "[QuickMedia] Installing frontend dependencies..."
    npm install
fi
npm run build

echo "[QuickMedia] Starting server..."
cd "$PROJECT_DIR"
PORT="${1:-8088}"
.venv/bin/quickmedia serve "$PORT"

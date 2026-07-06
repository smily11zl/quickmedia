#!/bin/bash
# QuickMedia one-click setup script
# Create venv, install deps, verify frontend dist.

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== QuickMedia Setup ===\n"

# 0. Find a suitable Python (prefer 3.11+)
PYTHON_BIN=""
for py in python3.11 python3.12 python3.13 python3; do
    if command -v "$py" &>/dev/null; then
        VER=$("$py" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0")
        MAJ=$(echo "$VER" | cut -d. -f1)
        MIN=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJ" -gt 3 ] || { [ "$MAJ" -eq 3 ] && [ "$MIN" -ge 11 ]; }; then
            PYTHON_BIN="$py"
            break
        fi
    fi
done
if [ -z "$PYTHON_BIN" ]; then
    echo "⚠ Python 3.11+ required."
    echo ""
    echo "Install with:"
    echo "  # macOS (install Homebrew first if needed)"
    echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    echo "  brew install python@3.11"
    echo "  sudo apt install python3.11       # Debian/Ubuntu"
    echo "  sudo dnf install python3.11       # Fedora"
    exit 1
fi
echo "→ Using $PYTHON_BIN ($VER detected)\n"

# 1. Create venv if missing
if [ ! -d ".venv" ]; then
    echo "→ Creating virtual environment..."
    $PYTHON_BIN -m venv .venv
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
    echo "→ Frontend dist found."
else
    echo "→ Frontend dist not found, trying auto-build..."
    if command -v node &>/dev/null; then
        cd frontend
        npm install --silent && npm run build
        cd ..
        echo "→ Frontend built successfully."
    else
        echo "→ Node.js not found. Install it, then: cd frontend && npm install && npm run build"
    fi
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Start:   .venv/bin/quickmedia serve"
echo "MCP:     .venv/bin/quickmedia mcp"
echo "Tests:   .venv/bin/python -m pytest tests/ -q"
echo ""

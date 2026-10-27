#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

echo "========================================"
echo " Setting up Recruit Lens Development Environment"
echo "========================================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "--> Setting up Python 3.11 virtual environment via uv..."
cd "$ROOT_DIR/backend"
uv python install 3.11
uv sync --all-extras

echo "--> Installing Node.js frontend dependencies..."
cd "$ROOT_DIR/frontend"
npm install

echo "--> Creating local data directory if not present..."
mkdir -p "$ROOT_DIR/data"

echo "========================================"
echo " Setup complete! Ready for development."
echo "========================================"

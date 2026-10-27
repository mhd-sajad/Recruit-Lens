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

echo "--> Checking local gitleaks installation..."
if ! command -v gitleaks &> /dev/null; then
  echo "WARNING: gitleaks is required for local secret detection and pre-commit hooks."
  echo "Please install gitleaks (e.g., download from https://github.com/gitleaks/gitleaks/releases or install via brew/pacman)."
else
  echo "✓ gitleaks is installed: $(gitleaks version)"
fi

echo "--> Installing git pre-commit hooks..."
cd "$ROOT_DIR"
if command -v pre-commit &> /dev/null; then
  pre-commit install
fi

echo "========================================"
echo " Setup complete! Ready for development."
echo "========================================"

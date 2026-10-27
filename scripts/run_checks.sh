#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

echo "========================================"
echo " Running Recruit Lens Quality Checks"
echo "========================================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "--> Checking Backend..."
cd "$ROOT_DIR/backend"
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests
uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=80

echo "--> Checking Frontend..."
cd "$ROOT_DIR/frontend"
npm run lint
npm run build
npm test

echo "========================================"
echo " All Quality Checks Passed Successfully!"
echo "========================================"

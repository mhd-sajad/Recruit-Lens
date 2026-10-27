#!/usr/bin/env bash
# Wrapper to run parser measurement
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")/../backend"
uv run python ../scripts/measure_parser.py

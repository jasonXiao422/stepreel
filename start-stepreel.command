#!/bin/bash
# macOS / Linux one-click launcher
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
command -v stepreel >/dev/null || uv tool install .
stepreel ui

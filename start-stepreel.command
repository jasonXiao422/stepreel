#!/bin/bash
# macOS / Linux one-click launcher (tries China mirrors first, then official sources)
cd "$(dirname "$0")"
VER=0.5.2
MARK="$HOME/.stepreel-$VER"
export PATH="$HOME/.local/bin:$PATH"
export UV_HTTP_TIMEOUT=600
if [ ! -f "$MARK" ]; then
  if ! command -v uv >/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh || { echo "uv 安装失败，请检查网络"; read; exit 1; }
    export PATH="$HOME/.local/bin:$PATH"
  fi
  echo "首次使用：正在安装 stepreel $VER（约 1 GB）"
  UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple uv tool install . --force \
  || UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple uv tool install . --force \
  || uv tool install . --force \
  || { echo "安装失败，请检查网络后重试"; read; exit 1; }
  touch "$MARK"
fi
stepreel ui

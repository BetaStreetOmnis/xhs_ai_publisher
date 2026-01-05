#!/bin/bash
echo "🚀 启动小红书AI发布助手..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONUTF8=1
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.xhs_system/ms-playwright}"

if [[ -x "venv/bin/python" ]]; then
  "venv/bin/python" main.py
else
  echo "⚠️ 未找到虚拟环境 venv，尝试使用系统 python3 启动..."
  python3 main.py
fi

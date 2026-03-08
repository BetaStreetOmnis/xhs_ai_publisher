#!/usr/bin/env bash
set -euo pipefail

echo "🚀 启动小红书AI发布助手..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export PYTHONUTF8=1
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.xhs_system/ms-playwright}"

is_working_python() {
  local candidate="$1"
  [[ -n "$candidate" ]] || return 1
  [[ -x "$candidate" ]] || return 1
  "$candidate" -c 'import sys' >/dev/null 2>&1
}

is_recommended_python() {
  local candidate="$1"
  "$candidate" -c 'import sys; raise SystemExit(0 if (3,8) <= sys.version_info[:2] < (3,13) else 1)' >/dev/null 2>&1
}

choose_system_python() {
  local candidate
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

VENV_PY="venv/bin/python"
PYTHON_CMD=""

if [[ -e "$VENV_PY" || -L "$VENV_PY" ]]; then
  if is_working_python "$VENV_PY"; then
    PYTHON_CMD="$VENV_PY"
    echo "✅ 使用虚拟环境: $VENV_PY ($($PYTHON_CMD -V 2>&1))"
  else
    echo "⚠️ 检测到 venv，但 $VENV_PY 不可用（可能是失效软链或环境已损坏）。"
  fi
else
  echo "ℹ️ 未找到可用的 venv/bin/python。"
fi

if [[ -z "$PYTHON_CMD" ]]; then
  PYTHON_CMD="$(choose_system_python || true)"
  if [[ -z "$PYTHON_CMD" ]]; then
    echo "❌ 未找到可用的 Python 解释器（已尝试 python3 / python）。"
    echo "💡 请先运行 ./install.sh 创建虚拟环境，或安装系统 Python 后重试。"
    exit 1
  fi

  echo "⚠️ 回退到系统 Python: $PYTHON_CMD ($($PYTHON_CMD -V 2>&1))"
fi

if ! is_recommended_python "$PYTHON_CMD"; then
  echo "⚠️ 当前 Python 版本不在推荐范围内（建议 3.8 - 3.12）。若启动异常，请先运行 ./install.sh 重新创建环境。"
fi

exec "$PYTHON_CMD" main.py

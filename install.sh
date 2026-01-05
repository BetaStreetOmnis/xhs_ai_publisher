#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

usage() {
  cat <<'EOF'
Usage:
  ./install.sh [--with-browser] [--skip-browser] [--recreate-venv]

Options:
  --with-browser    Force install Playwright Chromium (downloads ~100MB+)
  --skip-browser    Skip Playwright browser check/install
  --recreate-venv   Delete and recreate ./venv
EOF
}

WITH_BROWSER=0
SKIP_BROWSER=0
RECREATE_VENV=0

for arg in "$@"; do
  case "$arg" in
    --with-browser) WITH_BROWSER=1 ;;
    --skip-browser) SKIP_BROWSER=1 ;;
    --recreate-venv) RECREATE_VENV=1 ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "❌ Unknown argument: $arg"
      usage
      exit 2
      ;;
  esac
done

if [[ ! -f "requirements.txt" ]] || [[ ! -f "main.py" ]]; then
  echo "❌ Please run this script in the project root (needs requirements.txt + main.py)."
  exit 1
fi

check_python_version() {
  "$1" -c 'import sys; raise SystemExit(0 if (3,8) <= sys.version_info[:2] < (3,13) else 1)' >/dev/null 2>&1
}

choose_python() {
  for cmd in python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
      if check_python_version "$cmd"; then
        echo "$cmd"
        return 0
      fi
    fi
  done
  return 1
}

if [[ "$RECREATE_VENV" == "1" ]] && [[ -d "venv" ]]; then
  echo "🗑️  Removing existing venv/ ..."
  rm -rf venv
fi

VENV_PY="venv/bin/python"
if [[ -x "$VENV_PY" ]]; then
  if ! check_python_version "$VENV_PY"; then
    echo "❌ Existing venv uses unsupported Python version: $("$VENV_PY" -V 2>&1)"
    echo "💡 Please recreate venv with Python 3.11/3.12:"
    echo "   ./install.sh --recreate-venv"
    exit 1
  fi
else
  PYTHON_CMD="$(choose_python || true)"
  if [[ -z "${PYTHON_CMD:-}" ]]; then
    echo "❌ Python 3.8–3.12 not found. Please install Python 3.11/3.12 (recommended) then re-run."
    exit 1
  fi

  echo "✅ Using Python: $PYTHON_CMD ($($PYTHON_CMD -V 2>&1))"

  echo "🐍 Creating venv/ ..."
  "$PYTHON_CMD" -m venv venv
fi

echo "✅ Using venv: $VENV_PY ($($VENV_PY -V 2>&1))"
export PYTHONUTF8=1
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/.xhs_system/ms-playwright}"
PIP_ARGS=(--timeout 120 --retries 3 --prefer-binary)

echo "📦 Upgrading pip ..."
"$VENV_PY" -m pip install --upgrade pip setuptools wheel "${PIP_ARGS[@]}" || true

echo "📦 Installing dependencies ..."
"$VENV_PY" -m pip install -r requirements.txt "${PIP_ARGS[@]}"

echo "✅ Verifying imports ..."
"$VENV_PY" -c "import PyQt5; import sqlalchemy; import playwright; print('ok')"

check_playwright() {
  "$VENV_PY" - <<'PY'
import sys

try:
    from playwright.sync_api import sync_playwright
except Exception:
    sys.exit(1)

def main() -> int:
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True, timeout=30_000)
            browser.close()
            return 0
        except Exception as e:
            msg = str(e)
            if "Executable doesn't exist" not in msg and "not found" not in msg.lower() and "找不到" not in msg:
                return 1

        for channel in ("chrome", "msedge"):
            try:
                browser = p.chromium.launch(channel=channel, headless=True, timeout=30_000)
                browser.close()
                return 0
            except Exception:
                continue

    return 2

if __name__ == "__main__":
    sys.exit(main())
PY
}

if [[ "$SKIP_BROWSER" == "1" ]]; then
  :
elif [[ "$WITH_BROWSER" == "1" ]]; then
  echo "🌐 Installing Playwright Chromium ..."
  echo "   PLAYWRIGHT_BROWSERS_PATH=$PLAYWRIGHT_BROWSERS_PATH"
  if [[ -z "${PLAYWRIGHT_DOWNLOAD_HOST:-}" ]]; then
    echo "   Tip (CN): export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright"
  fi
  "$VENV_PY" -m playwright install chromium
else
  set +e
  check_playwright
  PW_RC=$?
  set -e
  if [[ "$PW_RC" != "0" ]]; then
    echo "🌐 Playwright browser not available yet; installing Chromium ..."
    echo "   PLAYWRIGHT_BROWSERS_PATH=$PLAYWRIGHT_BROWSERS_PATH"
    if [[ -z "${PLAYWRIGHT_DOWNLOAD_HOST:-}" ]]; then
      echo "   Tip (CN): export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright"
    fi
    "$VENV_PY" -m playwright install chromium || true
  fi
fi

echo
echo "🎉 Done."
echo "Start:"
echo "  ./启动程序.sh"
echo "  # or"
echo "  $VENV_PY main.py"

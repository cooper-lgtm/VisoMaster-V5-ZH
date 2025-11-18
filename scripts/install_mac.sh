#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
FALLBACK_INDEX_URL="${FALLBACK_INDEX_URL:-https://pypi.org/simple}"

echo "[1/4] Creating virtual environment (${VENV_DIR}) ..."
if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

echo "[2/4] Activating virtual environment ..."
# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip setuptools || python -m pip install --index-url "$FALLBACK_INDEX_URL" --upgrade pip setuptools
# Try to ensure wheel is present, but do not fail if mirror has issues
python -m pip install --upgrade wheel || python -m pip install --index-url "$FALLBACK_INDEX_URL" --upgrade wheel || true

echo "[3/4] Installing Python dependencies (requirements-mac.txt) ..."
pip install -r requirements-mac.txt || pip install --index-url "$FALLBACK_INDEX_URL" -r requirements-mac.txt
# Optional: virtual camera output (best-effort)
pip install pyvirtualcam || pip install --index-url "$FALLBACK_INDEX_URL" pyvirtualcam || true
# Optional: qdarktheme (best-effort) - UI can run without it due to code guards
pip install qdarktheme || pip install --index-url "$FALLBACK_INDEX_URL" qdarktheme || true

echo "[4/4] Checking ffmpeg (optional, for recording/export) ..."
if ! command -v ffmpeg >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    echo "ffmpeg not found. Installing via Homebrew ..."
    brew install ffmpeg || true
  else
    echo "ffmpeg not found and Homebrew is not installed. You can install ffmpeg manually if you need recording/export."
  fi
fi

echo
echo "Done."
echo "To launch the UI:"
echo "  ${PROJECT_ROOT}/scripts/run_mac.sh"
echo "or"
echo "  source ${VENV_DIR}/bin/activate && python main.py"
echo


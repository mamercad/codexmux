#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/usr/local/bin}"

command -v python3 >/dev/null 2>&1 || { echo "python3 required"; exit 1; }
command -v tmux    >/dev/null 2>&1 || { echo "tmux required";    exit 1; }
command -v codex   >/dev/null 2>&1 || echo "warning: codex CLI not found (needed at runtime)"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="${SCRIPT_DIR}/codexmux"

if [ ! -f "$SRC" ]; then
  echo "codexmux not found in ${SCRIPT_DIR}"
  exit 1
fi

if [ -w "$INSTALL_DIR" ]; then
  cp "$SRC" "${INSTALL_DIR}/codexmux"
  chmod +x "${INSTALL_DIR}/codexmux"
else
  sudo cp "$SRC" "${INSTALL_DIR}/codexmux"
  sudo chmod +x "${INSTALL_DIR}/codexmux"
fi

echo "codexmux installed to ${INSTALL_DIR}/codexmux"
echo "run: codexmux --help"

#!/usr/bin/env bash
set -euo pipefail

MODEL="${SEARCHPARS_MODEL:-qwen3.5:4b}"

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=()
else
  SUDO=(sudo)
fi

if ! command -v curl >/dev/null 2>&1; then
  "${SUDO[@]}" apt-get update
  "${SUDO[@]}" apt-get install -y curl
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "[SearchPars] Ollama kuruluyor"
  curl -fsSL https://ollama.com/install.sh | sh
fi

if command -v systemctl >/dev/null 2>&1; then
  "${SUDO[@]}" systemctl enable --now ollama
fi

echo "[SearchPars] ${MODEL} yerel yapay zekâ modeli indiriliyor"
ollama pull "${MODEL}"

echo
echo "Yerel yapay zekâ hazır. SearchPars'ı yeniden açın."

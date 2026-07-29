#!/usr/bin/env bash
set -euo pipefail

MODEL="${SEARCHPARS_MODEL:-qwen3.5:4b}"
OLLAMA_INSTALL_URL="https://ollama.com/install.sh"

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=()
else
  SUDO=(sudo)
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "[SearchPars] curl kuruluyor"
  "${SUDO[@]}" apt-get update
  "${SUDO[@]}" apt-get install -y curl
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "[SearchPars] Ollama kuruluyor"
  installer="$(mktemp)"
  trap 'rm -f "${installer:-}"' EXIT
  curl --fail --location --show-error --silent \
    "${OLLAMA_INSTALL_URL}" \
    --output "${installer}"
  sh "${installer}"
  rm -f "${installer}"
  trap - EXIT
fi

if ! command -v ollama >/dev/null 2>&1; then
  echo "[SearchPars] Ollama kuruldu fakat komutu bulunamadı." >&2
  exit 1
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "[SearchPars] systemd bulunamadı; Pardus 25 üzerinde kurulum yapın." >&2
  exit 1
fi

echo "[SearchPars] Ollama servisi başlatılıyor"
"${SUDO[@]}" systemctl daemon-reload
"${SUDO[@]}" systemctl enable --now ollama.service

echo "[SearchPars] Ollama servisinin hazır olması bekleniyor"
ollama_ready=0
for _attempt in $(seq 1 60); do
  if ollama list >/dev/null 2>&1; then
    ollama_ready=1
    break
  fi
  sleep 1
done

if [[ "${ollama_ready}" -ne 1 ]]; then
  echo "[SearchPars] Ollama servisi 60 saniye içinde hazır olmadı." >&2
  "${SUDO[@]}" systemctl status ollama.service --no-pager || true
  exit 1
fi

echo
echo "[SearchPars] ${MODEL} modeli indiriliyor"
echo "[SearchPars] Bu indirme birkaç GB olabilir; terminali kapatmayın."
ollama pull "${MODEL}"

echo "[SearchPars] Model doğrulanıyor"
ollama show "${MODEL}" >/dev/null

echo
echo "Yerel yapay zekâ hazır: ${MODEL}"

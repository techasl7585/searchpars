#!/usr/bin/env bash
set -euo pipefail

MODEL="${SEARCHPARS_MODEL:-qwen3.5:4b}"
STATE_DIR="/var/lib/searchpars"
READY_FILE="${STATE_DIR}/ai-ready"
LOG_FILE="/var/log/searchpars-ai-setup.log"

install -d -m 0755 "${STATE_DIR}"
exec >>"${LOG_FILE}" 2>&1

echo "[$(date --iso-8601=seconds)] SearchPars yapay zeka kurulumu başladı."

if ! command -v ollama >/dev/null 2>&1; then
    echo "Ollama kuruluyor."
    curl --fail --silent --show-error --location https://ollama.com/install.sh | sh
fi

if command -v systemctl >/dev/null 2>&1; then
    systemctl enable --now ollama.service
fi

for _attempt in $(seq 1 30); do
    if ollama list >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

echo "${MODEL} modeli indiriliyor."
ollama pull "${MODEL}"
printf '%s\n' "${MODEL}" >"${READY_FILE}"
chmod 0644 "${READY_FILE}"

echo "[$(date --iso-8601=seconds)] SearchPars yapay zekası hazır."

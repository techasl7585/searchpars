#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_DIR}"

echo "SearchPars Pardus kurucusu"
echo "=========================="
echo "Uygulama, sistem bağımlılıkları, Ollama ve yapay zekâ modeli kurulacak."
echo

exec bash "${PROJECT_DIR}/install-pardus.sh" "$@"

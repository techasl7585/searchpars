#!/usr/bin/env bash
set -euo pipefail

MODEL="${SEARCHPARS_MODEL:-qwen3.5:4b}"
OLLAMA_ARCHIVE_URL="https://ollama.com/download/ollama-linux-amd64.tar.zst"
INSTALL_PREFIX="${SEARCHPARS_OLLAMA_PREFIX:-/usr/local}"
CACHE_DIR="${SEARCHPARS_CACHE_DIR:-/var/cache/searchpars}"
SYSTEMD_DIR="${SEARCHPARS_SYSTEMD_DIR:-/etc/systemd/system}"
SERVICE_USER="${SEARCHPARS_SERVICE_USER:-ollama}"
OLLAMA_HOME="${SEARCHPARS_OLLAMA_HOME:-/usr/share/ollama}"
ARCHIVE="${CACHE_DIR}/ollama-linux-amd64.tar.zst"
OLLAMA_BIN=""
DOWNLOADED_OLLAMA=0

if [[ "${EUID}" -ne 0 ]]; then
  echo "[SearchPars] Yapay zekâ kurulumu yönetici yetkisiyle başlatılıyor…"
  exec sudo --preserve-env=SEARCHPARS_MODEL bash "$0" "$@"
fi

if ! command -v systemctl >/dev/null 2>&1; then
  echo "[SearchPars] systemd bulunamadı; Pardus 25 üzerinde kurulum yapın." >&2
  exit 1
fi

missing_tools=()
for tool in wget zstd tar; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    missing_tools+=("${tool}")
  fi
done
if [[ "${#missing_tools[@]}" -gt 0 ]]; then
  echo "[SearchPars] İndirme araçları kuruluyor: ${missing_tools[*]}"
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y wget zstd tar
fi

if command -v ollama >/dev/null 2>&1; then
  OLLAMA_BIN="$(command -v ollama)"
fi

needs_ollama_install=0
if [[ -z "${OLLAMA_BIN}" ]]; then
  needs_ollama_install=1
elif ! systemctl cat ollama.service >/dev/null 2>&1; then
  echo "[SearchPars] Ollama komutu bulundu fakat servisi eksik; kurulum onarılıyor."
  needs_ollama_install=1
fi

if [[ "${needs_ollama_install}" -eq 1 ]]; then
  echo "[SearchPars] Ollama kaldığı yerden devam edebilen yöntemle indiriliyor."
  echo "[SearchPars] Bağlantı kesilirse kısmi dosya ${CACHE_DIR} içinde korunur."
  install -d -m 0755 "${CACHE_DIR}" "${INSTALL_PREFIX}"

  download_ok=0
  for attempt in $(seq 1 10); do
    echo
    echo "[SearchPars] Ollama indirme denemesi ${attempt}/10"
    if wget \
      --continue \
      --tries=3 \
      --timeout=30 \
      --waitretry=5 \
      --progress=bar:force:noscroll \
      --output-document="${ARCHIVE}" \
      "${OLLAMA_ARCHIVE_URL}"; then
      download_ok=1
      break
    fi
    echo "[SearchPars] Bağlantı kesildi; 10 saniye sonra kaldığı yerden devam edilecek."
    sleep 10
  done

  if [[ "${download_ok}" -ne 1 ]]; then
    echo "[SearchPars] Ollama indirilemedi. Kısmi indirme silinmedi." >&2
    echo "Bağlantı geldiğinde bu komutu yeniden çalıştırın:" >&2
    echo "  sudo /opt/searchpars/setup-local-ai.sh" >&2
    exit 1
  fi

  echo "[SearchPars] Ollama arşivi doğrulanıyor"
  if ! zstd --test "${ARCHIVE}"; then
    echo "[SearchPars] İndirilen Ollama arşivi bozuk. Yeniden indirme gerekiyor." >&2
    rm -f "${ARCHIVE}"
    exit 1
  fi

  echo "[SearchPars] Ollama dosyaları kuruluyor"
  rm -rf "${INSTALL_PREFIX}/lib/ollama"
  zstd --decompress --stdout "${ARCHIVE}" | tar -xf - -C "${INSTALL_PREFIX}"
  OLLAMA_BIN="${INSTALL_PREFIX}/bin/ollama"
  if [[ ! -x "${OLLAMA_BIN}" ]]; then
    echo "[SearchPars] Ollama arşivi açıldı fakat çalıştırılabilir dosya bulunamadı." >&2
    exit 1
  fi
  DOWNLOADED_OLLAMA=1
fi

if [[ -z "${OLLAMA_BIN}" ]] || [[ ! -x "${OLLAMA_BIN}" ]]; then
  echo "[SearchPars] Ollama komutu bulunamadı." >&2
  exit 1
fi

if [[ "${SERVICE_USER}" == "ollama" ]]; then
  if ! id ollama >/dev/null 2>&1; then
    echo "[SearchPars] Ollama sistem kullanıcısı oluşturuluyor"
    useradd -r -s /bin/false -U -m -d "${OLLAMA_HOME}" ollama
  fi
  install -d -m 0755 -o ollama -g ollama "${OLLAMA_HOME}"

  for group in render video; do
    if getent group "${group}" >/dev/null 2>&1; then
      usermod -a -G "${group}" ollama
    fi
  done
  if [[ -n "${SUDO_USER:-}" ]] && id "${SUDO_USER}" >/dev/null 2>&1; then
    usermod -a -G ollama "${SUDO_USER}"
  fi
else
  install -d -m 0755 -o "${SERVICE_USER}" -g "${SERVICE_USER}" "${OLLAMA_HOME}"
fi

install -d -m 0755 "${SYSTEMD_DIR}"
cat >"${SYSTEMD_DIR}/ollama.service" <<EOF
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=${OLLAMA_BIN} serve
User=${SERVICE_USER}
Group=${SERVICE_USER}
Restart=always
RestartSec=3
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=multi-user.target
EOF
chmod 0644 "${SYSTEMD_DIR}/ollama.service"

echo "[SearchPars] Ollama servisi başlatılıyor"
systemctl daemon-reload
systemctl enable --now ollama.service

echo "[SearchPars] Ollama servisinin hazır olması bekleniyor"
ollama_ready=0
for _attempt in $(seq 1 60); do
  if "${OLLAMA_BIN}" list >/dev/null 2>&1; then
    ollama_ready=1
    break
  fi
  sleep 1
done

if [[ "${ollama_ready}" -ne 1 ]]; then
  echo "[SearchPars] Ollama servisi 60 saniye içinde hazır olmadı." >&2
  systemctl status ollama.service --no-pager || true
  exit 1
fi

if [[ "${DOWNLOADED_OLLAMA}" -eq 1 ]]; then
  rm -f "${ARCHIVE}"
fi

echo
echo "[SearchPars] ${MODEL} modeli indiriliyor"
echo "[SearchPars] Bağlantı kesilirse model indirmesi otomatik tekrar denenecek."
model_ready=0
for attempt in $(seq 1 10); do
  echo "[SearchPars] Model indirme denemesi ${attempt}/10"
  if "${OLLAMA_BIN}" pull "${MODEL}"; then
    model_ready=1
    break
  fi
  echo "[SearchPars] Model indirmesi kesildi; 10 saniye sonra yeniden denenecek."
  sleep 10
done

if [[ "${model_ready}" -ne 1 ]]; then
  echo "[SearchPars] Model indirilemedi; indirilen parçalar korunuyor." >&2
  echo "Bağlantı geldiğinde bu komutu yeniden çalıştırın:" >&2
  echo "  sudo /opt/searchpars/setup-local-ai.sh" >&2
  exit 1
fi

echo "[SearchPars] Model doğrulanıyor"
"${OLLAMA_BIN}" show "${MODEL}" >/dev/null

echo
echo "Yerel yapay zekâ hazır: ${MODEL}"

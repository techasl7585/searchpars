#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL="${SEARCHPARS_MODEL:-qwen3.5:4b}"

fail() {
  local exit_code=$?
  echo
  echo "[SearchPars] Kurulum tamamlanamadı (satır ${BASH_LINENO[0]})." >&2
  echo "Yukarıdaki hata mesajını kontrol edip ./kur.sh komutunu yeniden çalıştırın." >&2
  exit "${exit_code}"
}
trap fail ERR

if [[ "${EUID}" -ne 0 ]]; then
  echo "Kurulum yönetici yetkisiyle başlatılıyor…"
  exec sudo --preserve-env=SEARCHPARS_MODEL bash "$0" "$@"
fi

INSTALL_DIR="/opt/searchpars"
TARGET_USER="${SUDO_USER:-}"
INSTALL_AI=1

if [[ "${1:-}" == "--skip-ai" ]]; then
  INSTALL_AI=0
fi

if [[ ! -f "${PROJECT_DIR}/searchpars/app.py" ]]; then
  echo "Kurulum dosyaları eksik. ZIP dosyasını tamamen çıkarıp ./kur.sh çalıştırın." >&2
  exit 2
fi

if [[ "$(dpkg --print-architecture)" != "amd64" ]]; then
  echo "Bu paket yalnızca 64 bit x86 (amd64) Pardus bilgisayarlar içindir." >&2
  exit 2
fi

echo "[SearchPars] Pardus bağımlılıkları kuruluyor"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 \
  python3-gi \
  gir1.2-gtk-3.0 \
  libgtk-3-bin \
  ca-certificates \
  curl \
  desktop-file-utils \
  poppler-utils \
  xdg-utils

echo "[SearchPars] Uygulama kuruluyor"
install -d \
  "${INSTALL_DIR}" \
  /usr/local/bin \
  /usr/share/applications \
  /usr/share/icons/hicolor/scalable/apps
cp -a "${PROJECT_DIR}/searchpars" "${INSTALL_DIR}/"
install -m 0755 "${PROJECT_DIR}/bin/searchpars" "${INSTALL_DIR}/searchpars-launcher"
install -m 0755 "${PROJECT_DIR}/setup-local-ai.sh" "${INSTALL_DIR}/setup-local-ai.sh"
install -m 0755 "${PROJECT_DIR}/uninstall.sh" "${INSTALL_DIR}/uninstall.sh"
install -m 0644 \
  "${PROJECT_DIR}/data/com.pars.SearchPars.desktop" \
  /usr/share/applications/com.pars.SearchPars.desktop
install -m 0644 \
  "${PROJECT_DIR}/data/searchpars.svg" \
  /usr/share/icons/hicolor/scalable/apps/searchpars.svg

cat > /usr/local/bin/searchpars <<'EOF'
#!/usr/bin/env bash
export PYTHONPATH="/opt/searchpars${PYTHONPATH:+:${PYTHONPATH}}"
exec /usr/bin/python3 /opt/searchpars/searchpars-launcher "$@"
EOF
chmod 0755 /usr/local/bin/searchpars
update-desktop-database /usr/share/applications || true
gtk-update-icon-cache -f /usr/share/icons/hicolor >/dev/null 2>&1 || true

if [[ -n "${TARGET_USER}" ]] && command -v xfconf-query >/dev/null 2>&1; then
  if ! sudo -u "${TARGET_USER}" xfconf-query \
      -c xfce4-keyboard-shortcuts \
      -p '/commands/custom/<Super>space' >/dev/null 2>&1; then
    sudo -u "${TARGET_USER}" xfconf-query \
      -c xfce4-keyboard-shortcuts \
      -p '/commands/custom/<Super>space' \
      -n -t string -s 'searchpars' >/dev/null 2>&1 || true
  fi
fi

if [[ "${INSTALL_AI}" -eq 1 ]]; then
  echo
  echo "[SearchPars] Yerel yapay zekâ kuruluyor: ${MODEL}"
  echo "[SearchPars] Model indirme ilerlemesi bu terminalde görünecek."
  SEARCHPARS_MODEL="${MODEL}" bash "${INSTALL_DIR}/setup-local-ai.sh"
fi

echo
echo "SearchPars başarıyla kuruldu."
echo "Uygulamalar menüsünden SearchPars'ı açabilirsiniz."
echo "Uygunsa Super+Space klavye kısayolu da ayarlandı."
if [[ "${INSTALL_AI}" -eq 0 ]]; then
  echo "Yerel yapay zekâyı daha sonra kurmak için:"
  echo "  sudo /opt/searchpars/setup-local-ai.sh"
else
  echo "Yerel yapay zekâ modeli hazır: ${MODEL}"
fi

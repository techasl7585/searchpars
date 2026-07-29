#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi

rm -f /usr/local/bin/searchpars
rm -f /usr/share/applications/com.pars.SearchPars.desktop
rm -f /usr/share/icons/hicolor/scalable/apps/searchpars.svg
rm -rf /opt/searchpars
update-desktop-database /usr/share/applications || true
gtk-update-icon-cache -f /usr/share/icons/hicolor >/dev/null 2>&1 || true

echo "SearchPars kaldırıldı. Kullanıcının arama dizini korunmuştur."

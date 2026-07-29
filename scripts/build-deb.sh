#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' <"${PROJECT_DIR}/VERSION")"
BUILD_DIR="${PROJECT_DIR}/build/deb-root"
TEMP_DIR="${PROJECT_DIR}/build/tmp"
DIST_DIR="${PROJECT_DIR}/dist"
PACKAGE_FILE="${DIST_DIR}/SearchPars_${VERSION}_amd64.deb"

rm -rf "${BUILD_DIR}"
install -d \
    "${BUILD_DIR}/DEBIAN" \
    "${BUILD_DIR}/opt/searchpars/searchpars" \
    "${BUILD_DIR}/usr/bin" \
    "${BUILD_DIR}/usr/share/applications" \
    "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps" \
    "${BUILD_DIR}/usr/lib/systemd/system" \
    "${TEMP_DIR}" \
    "${DIST_DIR}"

cp -a "${PROJECT_DIR}/searchpars/." "${BUILD_DIR}/opt/searchpars/searchpars/"
find "${BUILD_DIR}/opt/searchpars/searchpars" -type d -name __pycache__ -prune -exec rm -rf {} +
find "${BUILD_DIR}/opt/searchpars/searchpars" -type f -name '*.pyc' -delete

install -m 0755 \
    "${PROJECT_DIR}/bin/searchpars" \
    "${BUILD_DIR}/opt/searchpars/searchpars-launcher"
install -m 0755 \
    "${PROJECT_DIR}/packaging/setup-local-ai-system.sh" \
    "${BUILD_DIR}/opt/searchpars/setup-local-ai-system.sh"
install -m 0755 \
    "${PROJECT_DIR}/packaging/searchpars-wrapper" \
    "${BUILD_DIR}/usr/bin/searchpars"
install -m 0644 \
    "${PROJECT_DIR}/data/com.pars.SearchPars.desktop" \
    "${BUILD_DIR}/usr/share/applications/com.pars.SearchPars.desktop"
install -m 0644 \
    "${PROJECT_DIR}/data/searchpars.svg" \
    "${BUILD_DIR}/usr/share/icons/hicolor/scalable/apps/searchpars.svg"
install -m 0644 \
    "${PROJECT_DIR}/packaging/searchpars-ai-setup.service" \
    "${BUILD_DIR}/usr/lib/systemd/system/searchpars-ai-setup.service"

sed "s/@VERSION@/${VERSION}/g" \
    "${PROJECT_DIR}/packaging/debian/control" \
    >"${BUILD_DIR}/DEBIAN/control"
install -m 0755 "${PROJECT_DIR}/packaging/debian/postinst" "${BUILD_DIR}/DEBIAN/postinst"
install -m 0755 "${PROJECT_DIR}/packaging/debian/prerm" "${BUILD_DIR}/DEBIAN/prerm"
install -m 0755 "${PROJECT_DIR}/packaging/debian/postrm" "${BUILD_DIR}/DEBIAN/postrm"

find "${BUILD_DIR}" -type d -exec chmod 0755 {} +
TMPDIR="${TEMP_DIR}" dpkg-deb --root-owner-group --build "${BUILD_DIR}" "${PACKAGE_FILE}"

echo
echo "Paket hazır: ${PACKAGE_FILE}"

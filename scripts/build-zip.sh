#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' <"${PROJECT_DIR}/VERSION")"
BUILD_DIR="${PROJECT_DIR}/build/zip"
PACKAGE_DIR="${BUILD_DIR}/SearchPars-${VERSION}"
DIST_DIR="${PROJECT_DIR}/dist"
ZIP_FILE="${DIST_DIR}/SearchPars_${VERSION}_Pardus.zip"

rm -rf "${BUILD_DIR}"
install -d \
  "${PACKAGE_DIR}/bin" \
  "${PACKAGE_DIR}/data" \
  "${PACKAGE_DIR}/searchpars" \
  "${DIST_DIR}"

cp -a "${PROJECT_DIR}/searchpars/." "${PACKAGE_DIR}/searchpars/"
install -m 0755 "${PROJECT_DIR}/bin/searchpars" "${PACKAGE_DIR}/bin/searchpars"
install -m 0755 "${PROJECT_DIR}/kur.sh" "${PACKAGE_DIR}/kur.sh"
install -m 0755 "${PROJECT_DIR}/install-pardus.sh" "${PACKAGE_DIR}/install-pardus.sh"
install -m 0755 "${PROJECT_DIR}/setup-local-ai.sh" "${PACKAGE_DIR}/setup-local-ai.sh"
install -m 0755 "${PROJECT_DIR}/uninstall.sh" "${PACKAGE_DIR}/uninstall.sh"
install -m 0644 \
  "${PROJECT_DIR}/data/com.pars.SearchPars.desktop" \
  "${PACKAGE_DIR}/data/com.pars.SearchPars.desktop"
install -m 0644 \
  "${PROJECT_DIR}/data/searchpars.svg" \
  "${PACKAGE_DIR}/data/searchpars.svg"
install -m 0644 "${PROJECT_DIR}/README.md" "${PACKAGE_DIR}/README.md"
install -m 0644 "${PROJECT_DIR}/VERSION" "${PACKAGE_DIR}/VERSION"

find "${PACKAGE_DIR}" -type d -name __pycache__ -prune -exec rm -rf {} +
find "${PACKAGE_DIR}" -type f -name '*.pyc' -delete

rm -f "${ZIP_FILE}" "${DIST_DIR}/SHA256SUMS"
(
  cd "${BUILD_DIR}"
  zip -q -r "${ZIP_FILE}" "SearchPars-${VERSION}"
)
(
  cd "${DIST_DIR}"
  sha256sum "$(basename "${ZIP_FILE}")" > SHA256SUMS
)

echo "ZIP hazır: ${ZIP_FILE}"

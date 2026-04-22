#!/usr/bin/env bash
set -euo pipefail

# Minimal installer for a dedicated freeviewer virtual environment.
VENV_NAME="freeviewer"
VENV_DIR="${VENV_NAME}"
PACKAGE_SPEC="${1:-freeview}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required but was not found in PATH."
  exit 1
fi

echo "Creating virtual environment: ${VENV_DIR}"
python3 -m venv "${VENV_DIR}"

PY_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"

if [[ ! -x "${PY_BIN}" || ! -x "${PIP_BIN}" ]]; then
  echo "Error: virtual environment creation failed."
  exit 1
fi

echo "Upgrading pip in ${VENV_DIR}"
"${PY_BIN}" -m pip install --upgrade pip

echo "Installing package: ${PACKAGE_SPEC}"
"${PIP_BIN}" install "${PACKAGE_SPEC}"

echo
echo "Installed successfully in ./${VENV_DIR}"
echo "Run the app with:"
echo "  ./${VENV_DIR}/bin/freeview serve"
echo "Optional cert setup:"
echo "  ./${VENV_DIR}/bin/freeview cert"

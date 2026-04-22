#!/usr/bin/env bash
set -euo pipefail

# Uninstall freeview from dedicated virtual environment and remove env folder.
VENV_NAME="freeviewer"
VENV_DIR="${VENV_NAME}"
PIP_BIN="${VENV_DIR}/bin/pip"

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Virtual environment '${VENV_DIR}' not found. Nothing to remove."
  exit 0
fi

if [[ -x "${PIP_BIN}" ]]; then
  echo "Uninstalling freeview from ${VENV_DIR}"
  "${PIP_BIN}" uninstall -y freeview || true
fi

echo "Removing virtual environment directory: ${VENV_DIR}"
rm -rf "${VENV_DIR}"

echo "Done. ${VENV_DIR} has been removed."

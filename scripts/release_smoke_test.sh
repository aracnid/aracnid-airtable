#!/usr/bin/env bash
set -euo pipefail

PKG="aracnid-airtable"
MOD="aracnid_airtable"
VENV_DIR="${TMPDIR:-/tmp}/aracnid-airtable-smoke"

python -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
pip install dist/*.whl

python - <<'PY'
import importlib
m = importlib.import_module("aracnid_airtable")
print("smoke import ok:", m.__name__)
PY

deactivate
rm -rf "$VENV_DIR"
echo "Smoke test passed."
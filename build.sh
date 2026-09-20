#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$PROJECT_DIR/source"
VENV_DIR="$SOURCE_DIR/.venv-build"
VENV_PYTHON="$VENV_DIR/bin/python"
REQUIREMENTS_FILE="$SOURCE_DIR/requirements-build.txt"
REQUIREMENTS_STAMP="$VENV_DIR/.requirements-build.sha256"

for command_name in python3 make arm-none-eabi-gcc arm-none-eabi-g++ zip unzip sha256sum awk nproc tail; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        printf 'Missing required command: %s\n' "$command_name" >&2
        exit 1
    fi
done

if [[ ! -x "$VENV_PYTHON" ]]; then
    printf 'Creating build environment at %s\n' "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

requirements_hash="$(sha256sum "$REQUIREMENTS_FILE" | awk '{print $1}')"
installed_hash=""
if [[ -f "$REQUIREMENTS_STAMP" ]]; then
    installed_hash="$(<"$REQUIREMENTS_STAMP")"
fi

if [[ "$installed_hash" != "$requirements_hash" ]]; then
    printf 'Installing firmware build dependencies...\n'
    "$VENV_PYTHON" -m pip install --disable-pip-version-check -r "$REQUIREMENTS_FILE"
    printf '%s\n' "$requirements_hash" >"$REQUIREMENTS_STAMP"
fi

export HOST_PYTHON="$VENV_PYTHON"
exec "$SOURCE_DIR/build.sh" "$@"

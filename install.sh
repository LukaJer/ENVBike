#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKIP_APT=0
SKIP_FRONTEND=0

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Install system dependencies, Python virtual environments (mda-server & mda-publishers),
and build the frontend bundle for EnvBike on a new machine.

Options:
  --no-apt        Skip apt-get system package installation
  --no-frontend   Skip npm install and webpack bundle build
  -h, --help      Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-apt)
            SKIP_APT=1
            shift
            ;;
        --no-frontend)
            SKIP_FRONTEND=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

echo "==> Installing EnvBike in $ROOT_DIR"

if [[ "$SKIP_APT" -eq 0 ]]; then
    if command -v apt-get >/dev/null 2>&1; then
        APT_PKGS=(python3 python3-venv python3-pip git)
        if [[ "$SKIP_FRONTEND" -eq 0 ]]; then
            APT_PKGS+=(nodejs npm)
        fi
        echo "==> Installing system packages via apt-get: ${APT_PKGS[*]}"
        sudo apt-get update
        sudo apt-get install -y "${APT_PKGS[@]}"
    else
        echo "==> apt-get not found; checking prerequisites on PATH..."
        for cmd in python3; do
            if ! command -v "$cmd" >/dev/null 2>&1; then
                echo "Error: Required command '$cmd' not found. Please install it with your package manager." >&2
                exit 1
            fi
        done
        if [[ "$SKIP_FRONTEND" -eq 0 ]]; then
            for cmd in node npm; do
                if ! command -v "$cmd" >/dev/null 2>&1; then
                    echo "Error: Required command '$cmd' not found. Install Node.js/npm or pass --no-frontend." >&2
                    exit 1
                fi
            done
        fi
    fi
fi

if [[ -d "$ROOT_DIR/.git" ]] && command -v git >/dev/null 2>&1; then
    if [[ ! -f "$ROOT_DIR/mda-server/app.py" || ! -f "$ROOT_DIR/mda-publishers/main.py" ]]; then
        echo "==> Initializing git submodules..."
        git -C "$ROOT_DIR" submodule update --init --recursive
    fi
fi

setup_venv() {
    local name="$1"
    local dir="$2"
    local req="$dir/requirements.txt"
    local venv_dir="$dir/venv"

    echo "==> Setting up Python venv for $name ($venv_dir)"
    if [[ ! -x "$venv_dir/bin/python" ]]; then
        python3 -m venv "$venv_dir"
    fi
    "$venv_dir/bin/python" -m pip install --upgrade pip
    "$venv_dir/bin/pip" install -r "$req"
}

setup_venv "mda-server" "$ROOT_DIR/mda-server"
setup_venv "mda-publishers" "$ROOT_DIR/mda-publishers"

mkdir -p "$ROOT_DIR/mda-server/static/maps" "$ROOT_DIR/mda-server/instance"

if [[ "$SKIP_FRONTEND" -eq 0 ]]; then
    echo "==> Installing frontend packages & building bundle.js"
    (
        cd "$ROOT_DIR/mda-server/static"
        npm install
        npm run build
    )
fi

if ! id -nG "$USER" | grep -qwE '(dialout|uucp)'; then
    echo ""
    echo "Tip: User '$USER' is not in the 'dialout' (Debian/Ubuntu) or 'uucp' (Arch) group."
    echo "     For USB-serial sensors (GPS, Grimm, UMB), run one of:"
    echo "       sudo usermod -aG dialout \"$USER\"   # Debian/Ubuntu/RPi OS"
    echo "       sudo usermod -aG uucp \"$USER\"      # Arch Linux"
    echo "     Then log out and back in."
fi

cat <<EOF

==> EnvBike installation complete!

Next steps:
  1. (Optional) Drop offline .mbtiles maps into:
       $ROOT_DIR/mda-server/static/maps/
  2. Start the server:
       cd $ROOT_DIR/mda-server && venv/bin/python app.py
       # Or via gunicorn (production):
       # cd $ROOT_DIR/mda-server && MDA_ENABLE_TERMINAL=1 venv/bin/gunicorn --workers 1 --threads 8 --bind 0.0.0.0:5000 'app:create_app()'
  3. Start the sensor publishers:
       cd $ROOT_DIR/mda-publishers && venv/bin/python main.py
EOF

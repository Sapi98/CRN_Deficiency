#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$PROJECT_DIR"

mode="${1:-}"
if [[ -z "$mode" ]]; then
    echo "CRNTAnalysis automatic setup"
    echo "You must already have either Python 3.9+ or Conda installed."
    echo "You only need the prerequisite for the option you choose."
    echo ""
    echo "  1) Python virtual environment (requires Python 3.9+; recommended)"
    echo "  2) Conda environment (requires Miniconda or Anaconda)"
    if [[ -t 0 ]]; then
        read -r -p "Choose 1 or 2 [1]: " choice
    else
        choice="1"
    fi
    mode="${choice:-1}"
fi

case "$mode" in
    1|venv|--venv)
        if ! command -v python3 >/dev/null 2>&1; then
            echo "Error: Python 3.9 or newer is required but python3 was not found."
            echo "Install Python from https://www.python.org/downloads/ and run this script again."
            exit 1
        fi
        python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' || {
            echo "Error: Python 3.9 or newer is required."
            exit 1
        }
        echo "Creating the virtual environment in .venv ..."
        python3 -m venv .venv
        echo "Installing CRNTAnalysis and its dependencies ..."
        "$PROJECT_DIR/.venv/bin/python" -m pip install --upgrade pip
        "$PROJECT_DIR/.venv/bin/python" -m pip install "$PROJECT_DIR"
        cat <<'EOF'

Setup complete.

Each time you open a new terminal, go to this project folder and run:
  source .venv/bin/activate

Then launch the desktop application with:
  crntanalysis-gui

Or analyze an example from the command line with:
  crntanalysis Example_Data/crn1.react

When finished, leave the environment with:
  deactivate
EOF
        ;;
    2|conda|--conda)
        if ! command -v conda >/dev/null 2>&1; then
            echo "Error: Conda was not found."
            echo "Install Miniconda or Anaconda, or rerun this script and choose option 1."
            exit 1
        fi
        if conda run --name crntanalysis python --version >/dev/null 2>&1; then
            echo "Reusing the existing Conda environment named crntanalysis."
        else
            echo "Creating the Conda environment named crntanalysis ..."
            conda create --name crntanalysis python=3.12 pip --yes
        fi
        echo "Installing CRNTAnalysis and its dependencies ..."
        conda run --name crntanalysis python -m pip install --upgrade pip
        conda run --name crntanalysis python -m pip install "$PROJECT_DIR"
        cat <<'EOF'

Setup complete.

Each time you open a new terminal, activate the environment with:
  conda activate crntanalysis

Then launch the desktop application with:
  crntanalysis-gui

Or analyze an example from the command line with:
  crntanalysis Example_Data/crn1.react

When finished, leave the environment with:
  conda deactivate
EOF
        ;;
    *)
        echo "Usage: bash setup.sh [--venv|--conda]"
        exit 2
        ;;
esac

#!/usr/bin/env bash
set -e

echo "Installing Bergendy..."

# Check if pipx is available
if command -v pipx &> /dev/null; then
    echo "Using pipx..."
    pipx install bergendy
    echo "Bergendy installed via pipx."
elif command -v pip3 &> /dev/null; then
    echo "pipx not found, using pip3 --user..."
    pip3 install --user bergendy
    echo "Bergendy installed to ~/.local/bin (ensure it's in your PATH)."
elif command -v pip &> /dev/null; then
    echo "pipx not found, using pip --user..."
    pip install --user bergendy
    echo "Bergendy installed to ~/.local/bin (ensure it's in your PATH)."
else
    echo "Error: pipx or pip not found. Install Python 3.10+ and try again."
    exit 1
fi

echo ""
echo "Verify installation: bergendy --version"

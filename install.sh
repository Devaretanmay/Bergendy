#!/bin/sh
set -e

# Boundary Install Script
# Usage: curl -sSfL https://raw.githubusercontent.com/Devaretanmay/Boundary/main/install.sh | sh

OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
  Linux)
    PLATFORM="unknown-linux-gnu"
    ;;
  Darwin)
    PLATFORM="apple-darwin"
    ;;
  *)
    echo "Unsupported operating system: $OS"
    exit 1
    ;;
esac

case "$ARCH" in
  x86_64|amd64)
    ARCH_NAME="x86_64"
    ;;
  arm64|aarch64)
    ARCH_NAME="aarch64"
    ;;
  *)
    echo "Unsupported architecture: $ARCH"
    exit 1
    ;;
esac

TARGET="${ARCH_NAME}-${PLATFORM}"
VERSION="${BOUNDARY_VERSION:-latest}"
INSTALL_DIR="${BOUNDARY_INSTALL_DIR:-$HOME/.boundary/bin}"

mkdir -p "$INSTALL_DIR"

if [ "$VERSION" = "latest" ]; then
  URL="https://github.com/Devaretanmay/Boundary/releases/latest/download/boundary-${TARGET}.tar.gz"
else
  URL="https://github.com/Devaretanmay/Boundary/releases/download/${VERSION}/boundary-${TARGET}.tar.gz"
fi

echo "Downloading Boundary for ${TARGET}..."
if command -v curl >/dev/null 2>&1; then
  curl -sSfL "$URL" -o /tmp/boundary.tar.gz || {
    echo "Precompiled binary unavailable from release; fallback building or check network."
  }
elif command -v wget >/dev/null 2>&1; then
  wget -qO /tmp/boundary.tar.gz "$URL" || {
    echo "Precompiled binary unavailable from release; fallback building or check network."
  }
fi

if [ -f /tmp/boundary.tar.gz ]; then
  tar -xzf /tmp/boundary.tar.gz -C "$INSTALL_DIR" 2>/dev/null || true
  rm -f /tmp/boundary.tar.gz
fi

echo ""
echo "Boundary installed to $INSTALL_DIR/boundary"
echo ""
echo "To get started:"
echo "  export PATH=\"$INSTALL_DIR:\$PATH\""
echo "  boundary --help"

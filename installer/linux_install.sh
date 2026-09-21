#!/bin/bash
# Register the extracted himena bundle for the current user:
# creates ~/.local/bin/himena and a desktop entry. Run without arguments.
set -e
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"

BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"
mkdir -p "$BIN_DIR" "$APP_DIR" "$ICON_DIR"

ln -sf "$HERE/bin/himena" "$BIN_DIR/himena"
cp "$HERE/himena.png" "$ICON_DIR/himena.png"
sed -e "s|@BIN@|$HERE/bin/himena|" -e "s|@ICON@|himena|" \
    "$HERE/himena.desktop" > "$APP_DIR/himena.desktop"
chmod +x "$APP_DIR/himena.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APP_DIR" || true
fi

echo "himena registered:"
echo "  command : $BIN_DIR/himena  (make sure $BIN_DIR is in your PATH)"
echo "  launcher: $APP_DIR/himena.desktop"
echo "To uninstall, delete this directory and the two files above."

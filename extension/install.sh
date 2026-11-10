#!/usr/bin/env bash
# Install (or update) the Floatbeat GNOME Shell extension for the current user.
#
# The first time, GNOME only scans the extensions directory at login, so log out
# and back in after running this. Later updates can be applied by logging out and
# back in too (GNOME 50 does not implement ReloadExtension).
set -euo pipefail

UUID="floatbeat@rarroy2.github.io"
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/$UUID"

mkdir -p "$DEST"
cp "$SRC/metadata.json" "$SRC/extension.js" "$SRC/avatar.js" "$DEST/"

echo "Installed to $DEST"
echo
echo "If this is the first time: log out and back in, then run"
echo "  gnome-extensions enable $UUID"
echo
echo "Disable with:"
echo "  gnome-extensions disable $UUID"

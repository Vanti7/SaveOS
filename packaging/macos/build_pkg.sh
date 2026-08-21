#!/usr/bin/env bash
# Construit l'installeur macOS de l'agent SaveOS : dist/saveos-agent (binaire
# PyInstaller) -> .pkg (pkgbuild/productbuild, avec postinstall enregistrant
# le service launchd) -> .dmg (hdiutil) contenant ce .pkg.
#
# Invocation (depuis la racine du dépôt, sur un runner/machine macOS) :
#   packaging/macos/build_pkg.sh <version>
set -euo pipefail

VERSION="${1:?Usage: build_pkg.sh <version>}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

BIN_PATH="$REPO_ROOT/dist/saveos-agent"
if [ ! -f "$BIN_PATH" ]; then
  echo "❌ $BIN_PATH introuvable — construire avec pyinstaller packaging/saveos-agent.spec d'abord" >&2
  exit 1
fi

INSTALL_ROOT="$WORK_DIR/root/usr/local/bin"
mkdir -p "$INSTALL_ROOT"
cp "$BIN_PATH" "$INSTALL_ROOT/saveos-agent"
chmod 755 "$INSTALL_ROOT/saveos-agent"

SCRIPTS_DIR="$WORK_DIR/scripts"
mkdir -p "$SCRIPTS_DIR"
cat > "$SCRIPTS_DIR/postinstall" <<'EOF'
#!/usr/bin/env bash
set -e
/usr/local/bin/saveos-agent service install || true
exit 0
EOF
chmod 755 "$SCRIPTS_DIR/postinstall"

OUT_DIR="$REPO_ROOT/dist/installers"
mkdir -p "$OUT_DIR"
PKG_PATH="$WORK_DIR/SaveOS-Agent-$VERSION.pkg"

pkgbuild \
  --root "$WORK_DIR/root" \
  --scripts "$SCRIPTS_DIR" \
  --identifier "com.saveos.agent" \
  --version "$VERSION" \
  --install-location "/" \
  "$PKG_PATH"

DMG_PATH="$OUT_DIR/SaveOS-Agent-$VERSION-macos.dmg"
DMG_STAGING="$WORK_DIR/dmg"
mkdir -p "$DMG_STAGING"
cp "$PKG_PATH" "$DMG_STAGING/"

hdiutil create \
  -volname "SaveOS Agent $VERSION" \
  -srcfolder "$DMG_STAGING" \
  -ov -format UDZO \
  "$DMG_PATH"

echo "✅ $DMG_PATH"

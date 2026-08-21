#!/usr/bin/env bash
# Construit le paquet .deb de l'agent SaveOS via fpm : dist/saveos-agent
# (binaire PyInstaller) -> /usr/local/bin/saveos-agent, avec un script
# postinst qui active et démarre le service systemd.
#
# Invocation (depuis la racine du dépôt, sur un runner/machine Linux avec
# fpm installé — `gem install fpm`) :
#   packaging/linux/build_deb.sh <version>
set -euo pipefail

VERSION="${1:?Usage: build_deb.sh <version>}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

BIN_PATH="$REPO_ROOT/dist/saveos-agent"
if [ ! -f "$BIN_PATH" ]; then
  echo "❌ $BIN_PATH introuvable — construire avec pyinstaller packaging/saveos-agent.spec d'abord" >&2
  exit 1
fi

STAGE_DIR="$WORK_DIR/root/usr/local/bin"
mkdir -p "$STAGE_DIR"
cp "$BIN_PATH" "$STAGE_DIR/saveos-agent"
chmod 755 "$STAGE_DIR/saveos-agent"

POSTINST="$WORK_DIR/postinst.sh"
cat > "$POSTINST" <<'EOF'
#!/usr/bin/env bash
set -e
/usr/local/bin/saveos-agent service install || true
/usr/local/bin/saveos-agent service start || true
exit 0
EOF
chmod 755 "$POSTINST"

PRERM="$WORK_DIR/prerm.sh"
cat > "$PRERM" <<'EOF'
#!/usr/bin/env bash
set -e
/usr/local/bin/saveos-agent service stop || true
exit 0
EOF
chmod 755 "$PRERM"

OUT_DIR="$REPO_ROOT/dist/installers"
mkdir -p "$OUT_DIR"

fpm \
  -s dir \
  -t deb \
  -n saveos-agent \
  -v "$VERSION" \
  --architecture amd64 \
  --description "Agent de sauvegarde SaveOS" \
  --url "https://github.com/Vanti7/SaveOS" \
  --license "AGPL-3.0" \
  --maintainer "SaveOS Project <contact@saveos.local>" \
  --after-install "$POSTINST" \
  --before-remove "$PRERM" \
  --package "$OUT_DIR/saveos-agent_${VERSION}_amd64.deb" \
  -C "$WORK_DIR/root" \
  usr

echo "✅ $OUT_DIR/saveos-agent_${VERSION}_amd64.deb"

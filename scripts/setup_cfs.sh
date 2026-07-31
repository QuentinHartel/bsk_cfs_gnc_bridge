#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFS_DIR="$REPO_ROOT/cfs"
APP_SRC="$REPO_ROOT/cfs-apps/gnc_app"
APP_DEST="$CFS_DIR/apps/gnc_app"

echo "== Linking gnc_app into cFS apps directory =="
if [ -L "$APP_DEST" ] || [ -d "$APP_DEST" ]; then
    echo "gnc_app already present at $APP_DEST — removing stale link/copy"
    rm -rf "$APP_DEST"
fi
ln -s "$APP_SRC" "$APP_DEST"
echo "Linked: $APP_DEST -> $APP_SRC"

echo ""
echo "== Manual steps remaining =="
echo "1. Add 'gnc_app' to the TGT1_APPLIST in:"
echo "   $CFS_DIR/sample_defs/targets.cmake"
echo ""
echo "2. Add a startup entry for GNC_APP in:"
echo "   $CFS_DIR/sample_defs/cpu1_cfe_es_startup.scr"
echo ""
echo "Run 'make native_std.prep' after making both edits."

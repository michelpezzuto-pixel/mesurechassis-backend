#!/usr/bin/env bash
# build-web.sh — Rebuild the Web Statique production bundle
#
# USAGE :
#   ./build-web.sh           # build only
#   ./build-web.sh --serve   # build + restart supervisor expo (serve dist)
#
# CONTEXTE :
#   Le supervisor "expo" sert /app/frontend/dist via `serve`. Toute modification
#   du code frontend nécessite de rebuild ce dossier pour être visible.
set -euo pipefail
cd "$(dirname "$0")"

echo "▶ Building Expo web export → /app/frontend/dist ..."
rm -rf dist
yarn expo export --platform web --output-dir dist

echo "▶ Build complete. Files:"
ls -1 dist | head -10

if [[ "${1:-}" == "--serve" ]]; then
  echo "▶ Restarting supervisor expo (serve dist)..."
  sudo supervisorctl restart expo
  echo "▶ Done. Preview ready at http://localhost:3000"
fi

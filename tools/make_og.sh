#!/usr/bin/env bash
# Rasterise tools/og.svg → public/static/og.png at 1200×630.
# Re-run this after editing the SVG. Requires `rsvg-convert` (Homebrew: librsvg).
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v rsvg-convert >/dev/null; then
  echo "rsvg-convert not found. Install with: brew install librsvg" >&2
  exit 1
fi

mkdir -p public/static
rsvg-convert --width=1200 --height=630 --keep-aspect-ratio \
             --background-color=transparent \
             --output public/static/og.png \
             tools/og.svg

# Also produce a 600×600 square version for platforms that prefer it
rsvg-convert --width=600 --height=600 --keep-aspect-ratio \
             --background-color=transparent \
             --output public/static/og-square.png \
             tools/og.svg

echo "Wrote public/static/og.png ($(wc -c < public/static/og.png) bytes)"
echo "Wrote public/static/og-square.png ($(wc -c < public/static/og-square.png) bytes)"

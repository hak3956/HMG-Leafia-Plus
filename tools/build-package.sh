#!/bin/sh
# Build the Wireless CarPlay/AA NEMESIS package. Everything comes from this repo:
# scripts, lpatch, recipes and the per-car patch sets in patches/. No modified
# app is shipped - the head unit rebuilds them from its own stock files.
# usage: build-package.sh [output zip]
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=${1:-$ROOT/dist/HMG_Leafia_Plus_Wireless_CarPlay_AA.zip}
case "$OUT" in /*) ;; *) OUT=$(pwd)/$OUT ;; esac
# the HU's shell (mksh) has no printf, but the host shells the tests run in do;
# the only allowed use is putline's host fallback
if grep -rn --include='*.sh' 'printf' "$ROOT/packages/wireless-carplay-aa" \
    | grep -vE ':[0-9]+:[[:space:]]*#' | grep -vF "printf '%s\n' \"\$1\""; then
    echo "build-package: printf in package scripts (not on the head unit) - use echo or putline" >&2
    exit 1
fi
STAGE=$(mktemp -d)
cp -R "$ROOT/packages/wireless-carplay-aa/." "$STAGE/inner"
rm -f "$STAGE/inner/README.md"
mkdir -p "$STAGE/inner/tools" "$STAGE/inner/recipes"
cp "$ROOT/tools/lpatch/lpatch" "$STAGE/inner/tools/lpatch"
cp "$ROOT"/recipes/*.recipe "$STAGE/inner/recipes/"
cp -R "$ROOT/patches" "$STAGE/inner/patches"
rm -f "$STAGE/inner/patches/README.md"
# which source this package was built from; logged at install, read by the Leafia kit
echo "$(git -C "$ROOT" describe --always --dirty 2>/dev/null || echo unknown) $(date -u +%Y-%m-%d)" > "$STAGE/inner/BUILD"
mkdir -p "$STAGE/outer/packages"
# NEMESIS.data first, then every other path in sorted order: the order `zip -r .` takes
# from the file system changes from build to build (ext4 hashes each new directory), and
# NEMESIS 1.15 could not show or install a build whose NEMESIS.data came last in the
# inner zip ("usb prompt result_fail" / timeout before any of our scripts ran)
(cd "$STAGE/inner" && { echo NEMESIS.data; find . -mindepth 1 | sed 's|^\./||' | grep -vx NEMESIS.data | LC_ALL=C sort; } \
    | zip -qX "$STAGE/outer/packages/wireless.carplay.aa.zip" -@)
printf '[nemesis]\nversion=1.0\ntype=install\npath=packages/wireless.carplay.aa.zip\n' > "$STAGE/outer/NEMESIS.data"
mkdir -p "$(dirname "$OUT")" && rm -f "$OUT"
(cd "$STAGE/outer" && zip -qrX "$OUT" NEMESIS.data packages)
rm -r "$STAGE"
echo "$OUT"

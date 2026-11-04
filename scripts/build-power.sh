#!/usr/bin/env bash
# Build build/power/ps5power-<action>.elf, using the SDK build-padd.sh downloads.
# From Windows:  wsl -d Ubuntu -- bash scripts/build-power.sh
set -euo pipefail

SDK_VERSION=v0.43
root=$(cd "$(dirname "$0")/.." && pwd)
out=$root/build/power
work=${PADD_WORK:-$HOME/.cache/playden-tester/padd}
sdk=$work/ps5-payload-sdk-$SDK_VERSION
[ -x "$sdk/bin/prospero-clang" ] || { echo "no SDK at $sdk: run scripts/build-padd.sh first" >&2; exit 1; }

export PS5_PAYLOAD_SDK=$sdk
export PATH=/usr/lib/llvm-18/bin:$PATH
mkdir -p "$out"
for action in restart standby off; do
  "$sdk/bin/prospero-clang" -std=c11 -Wall -Wextra -Werror -O1 "-DPOWER_ACTION=\"$action\"" \
    -o "$out/ps5power-$action.elf" "$root/payloads/ps5power.c"
done
(cd "$out" && sha256sum ./*.elf | tee SHA256SUMS)

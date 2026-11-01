#!/usr/bin/env bash
# Build padd.elf, ps5-mcp's virtual-DualSense payload, into build/padd/.
# Runs on Linux or WSL. Needs: clang-18 lld-18 unzip curl git
#   sudo apt install -y clang-18 lld-18 unzip
# From Windows:  wsl -d Ubuntu -- bash scripts/build-padd.sh
set -euo pipefail

PS5MCP_REPO=https://github.com/leolobato/ps5-mcp.git
PS5MCP_COMMIT=84c0f7b316772b13cd62e0121c154afc3ed2482c
SDK_VERSION=v0.43
SDK_URL=https://github.com/ps5-payload-dev/sdk/releases/download/$SDK_VERSION/ps5-payload-sdk.zip
SDK_SHA256=a9cc9929f21b2b2c5d5b309f3bab4997067c45281c0622cf4838b1aecba66fcb

root=$(cd "$(dirname "$0")/.." && pwd)
out=$root/build/padd
# The SDK and sources go in the Linux home: symlinks and exec bits do not survive /mnt/c.
work=${PADD_WORK:-$HOME/.cache/playden-tester/padd}
mkdir -p "$out" "$work"

for tool in clang-18 ld.lld-18 unzip curl git; do
  command -v "$tool" >/dev/null || { echo "missing $tool: sudo apt install -y clang-18 lld-18 unzip curl git" >&2; exit 1; }
done

sdk=$work/ps5-payload-sdk-$SDK_VERSION
if [ ! -x "$sdk/bin/prospero-clang" ]; then
  zip=$work/ps5-payload-sdk-$SDK_VERSION.zip
  [ -f "$zip" ] || curl -fL --retry 3 -o "$zip.part" "$SDK_URL" && { [ -f "$zip" ] || mv "$zip.part" "$zip"; }
  echo "$SDK_SHA256  $zip" | sha256sum -c - || { rm -f "$zip"; echo "SDK checksum mismatch" >&2; exit 1; }
  rm -rf "$work/sdk-unpack" && mkdir "$work/sdk-unpack"
  unzip -q "$zip" -d "$work/sdk-unpack"
  rm -rf "$sdk" && mv "$work/sdk-unpack/ps5-payload-sdk" "$sdk" && rmdir "$work/sdk-unpack"
fi

src=$work/ps5-mcp
if [ ! -d "$src/.git" ]; then
  git clone -q "$PS5MCP_REPO" "$src"
fi
git -C "$src" fetch -q origin "$PS5MCP_COMMIT" 2>/dev/null || true
git -C "$src" -c advice.detachedHead=false checkout -q "$PS5MCP_COMMIT"

export PS5_PAYLOAD_SDK=$sdk
export LLVM_CONFIG=${LLVM_CONFIG:-$(command -v llvm-config-18 || true)}
export PATH=/usr/lib/llvm-18/bin:$PATH
cd "$src"
"$sdk/bin/prospero-clang" -std=c11 -Wall -Wextra -Werror -g -O1 -o "$out/padd.elf" \
  payload/padd.c payload/smp.c payload/system_ps5.c -lSceUserService -lSceSystemService -lSceAppInstUtil
cp LICENSE "$out/LICENSE-ps5-mcp"
sha256sum "$out/padd.elf" | tee "$out/padd.elf.sha256"
echo "padd from ps5-mcp $PS5MCP_COMMIT, SDK $SDK_VERSION" > "$out/BUILD.txt"
echo "built $out/padd.elf"

#!/usr/bin/env bash
# Build rp-get-pin.elf into build/rp-get-pin/, from idlesauce's ps5-remoteplay-get-pin at a pinned commit, using the
# SDK build-padd.sh downloads. It's changed so it never turns Remote Play on: the original writes that setting.
# From Windows:  wsl -d Ubuntu -- bash scripts/build-rp-get-pin.sh
set -euo pipefail

REPO=https://github.com/idlesauce/ps5-remoteplay-get-pin.git
COMMIT=637319752150fbf1e8abafe10dea6b785cc747cf
SDK_VERSION=v0.43

root=$(cd "$(dirname "$0")/.." && pwd)
out=$root/build/rp-get-pin
base=${PADD_WORK:-$HOME/.cache/playden-tester/padd}
work=$(dirname "$base")/rp-get-pin
sdk=$base/ps5-payload-sdk-$SDK_VERSION
[ -x "$sdk/bin/prospero-clang" ] || { echo "no SDK at $sdk: run scripts/build-padd.sh first" >&2; exit 1; }

[ -d "$work/.git" ] || git clone -q "$REPO" "$work"
git -C "$work" fetch -q origin
git -C "$work" -c advice.detachedHead=false checkout -q -f "$COMMIT"

python3 - "$work/main.c" <<'EOF'
import sys
path = sys.argv[1]
text = open(path).read()
start = text.index("    if (original_rp_enable_val != 1)\n")
end = text.index('    pid_t shellui_pid = find_pid("SceShellUI");')
text = text[:start] + '''    if (original_rp_enable_val != 1)
    {
        notifyf_printf("Remote Play is off: turn it on in Settings, then send this again");
        return -1;
    }

''' + text[end:]
assert "sceRegMgrSetInt(SCE_REGMGR" not in text
open(path, "w").write(text)
EOF

export PS5_PAYLOAD_SDK=$sdk
export PATH=/usr/lib/llvm-18/bin:$PATH
make -s -C "$work" clean all
mkdir -p "$out"
cp "$work/rp-get-pin.elf" "$out/"
sha256sum "$out/rp-get-pin.elf"
echo "built $out/rp-get-pin.elf"

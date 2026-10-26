#!/usr/bin/env bash
set -euo pipefail
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
workspace=$(dirname -- "$src")
out=${OUT_DIR:-"$workspace/out-miatoll-6.18"}
dist=${DIST_DIR:-"$workspace/dist/miatoll-6.18"}
toolroot=${WORKSPACE_TOOLS:-"$workspace/tools"}
llvm="$toolroot/llvm18/usr/lib/llvm-18/bin"
host="$toolroot/host-build"
if [[ -d "$llvm" ]]; then export PATH="$llvm:$PATH"; fi
if [[ -d "$host/usr/bin" ]]; then
    export PATH="$host/usr/bin:$PATH"
    export BISON_PKGDATADIR="$host/usr/share/bison"
    export M4="$host/usr/bin/m4"
    export HOSTCFLAGS="-I$host/usr/include ${HOSTCFLAGS:-}"
    export HOSTLDFLAGS="-L$host/usr/lib/x86_64-linux-gnu ${HOSTLDFLAGS:-}"
    export PKG_CONFIG_LIBDIR="$host/usr/lib/x86_64-linux-gnu/pkgconfig"
    export PKG_CONFIG_SYSROOT_DIR="$host"
fi
export ARCH=arm64 LLVM=1
export KBUILD_BUILD_USER=miatoll KBUILD_BUILD_HOST=lts
export KBUILD_BUILD_TIMESTAMP='2026-10-26 00:00:00 +0000'
mkdir -p "$out" "$dist"
out=$(realpath "$out")
dist=$(realpath "$dist")
make -C "$src" O="$out" defconfig
python3 - "$src" "$out/.config" <<'PY'
from pathlib import Path
import re, subprocess, sys
src, config = map(Path, sys.argv[1:])
lines = config.read_text().splitlines()
config.write_text('\n'.join('# ' + x[:-2] + ' is not set' if x.endswith('=m') else x
                           for x in lines) + '\n')
for symbol in re.findall(r'^config (ARCH_[A-Z0-9_]+)$',
                         (src/'arch/arm64/Kconfig.platforms').read_text(), re.M):
    if symbol != 'ARCH_QCOM':
        subprocess.run([str(src/'scripts/config'), '--file', str(config),
                        '--disable', symbol], check=True)
PY
fragments=("$src/miatoll/configs/miatoll.config")
for fragment in "$@"; do fragments+=("$(realpath "$fragment")"); done
"$src/scripts/kconfig/merge_config.sh" -m -O "$out" "$out/.config" "${fragments[@]}"
make -C "$src" O="$out" olddefconfig
python3 - "$out/.config" "${fragments[@]}" <<'PY'
from pathlib import Path
import sys
def parse(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        if line.startswith('CONFIG_'):
            k, v = line.split('=', 1); values[k] = v
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            values[line[2:-11]] = 'n'
    return values
actual = parse(sys.argv[1]); requested = {}
for fragment in sys.argv[2:]: requested.update(parse(fragment))
missing = [f'{k}: requested {v}, got {actual.get(k, "n")}'
           for k, v in requested.items() if actual.get(k, 'n') != v]
if missing: raise SystemExit('Unresolved Kconfig requests:\n' + '\n'.join(missing))
PY
if [[ ${CONFIG_ONLY:-0} == 1 ]]; then exit 0; fi
make -C "$src" O="$out" -j"${JOBS:-32}" Image dtbs modules
make -C "$src" O="$out" INSTALL_MOD_PATH="$dist/modules" modules_install
cp "$out/arch/arm64/boot/Image" "$out/.config" "$out/Module.symvers" "$out/System.map" "$dist/"
mkdir -p "$dist/dtbs"
find "$out/arch/arm64/boot/dts/qcom" -maxdepth 1 -name 'sm7125-xiaomi-*.dtb' \
    -exec cp -t "$dist/dtbs" {} +
make -s -C "$src" O="$out" kernelrelease > "$dist/kernelrelease.txt"
git -C "$src" rev-parse HEAD > "$dist/source-commit.txt"
git -C "$src" diff --binary HEAD > "$dist/source-changes.patch"
find "$dist" -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > "$dist/SHA256SUMS"

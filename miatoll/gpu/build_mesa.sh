#!/usr/bin/env bash
# Cross-build Mesa (freedreno only, EGL/GBM/GLES2, no LLVM, no X11/Wayland)
# and kmscube for the curtana RAM test.
# usage: build_mesa.sh [gles|vulkan]
#   gles    -> ../out-mesa          (gpu2: GLES only)
#   vulkan  -> ../out-mesa-vulkan   (adds the Turnip Vulkan driver, the Alpine
#                                    Vulkan loader and vulkan-tools) Inputs are pinned by SHA-256; the
# sysroot comes from prepare_mesa_sysroot.py. Everything is written to
# ../out-mesa, outside the repository.
set -euo pipefail

src=$(cd "$(dirname "$0")/../.." && pwd)
workspace=$(dirname "$src")
variant=${1:-gles}
case $variant in
    gles) out=$workspace/out-mesa; vulkan_drivers= ;;
    vulkan) out=$workspace/out-mesa-vulkan; vulkan_drivers=freedreno ;;
    *) echo "usage: $0 [gles|vulkan]" >&2; exit 2 ;;
esac
tools=$workspace/tools
sysroot=$tools/sysroot-mesa-aarch64
llvm=$tools/llvm18/usr/lib/llvm-18
resource=$tools/clang18-resource-aarch64-musl
venv=$tools/mesa-venv

mesa_tar=$workspace/downloads/mesa-src/mesa-25.1.9.tar.xz
mesa_sha256=412df33a1bb3c785ed698555a3972118a37c458e7accf6ae53f4bb87b3db454a
kmscube_commit=2c1f2646c5e58d11b279b610a8509116c02b067b
kmscube_tar=$workspace/downloads/kmscube-src/kmscube-$kmscube_commit.tar.gz
kmscube_sha256=27f61c74f724fdc584d7575772d09a19817628b30faca072855f4c3ebeaf3f36

echo "$mesa_sha256  $mesa_tar" | sha256sum -c -
if [[ $variant == vulkan ]]; then
    # Host glslangValidator for Turnip's internal shaders: Ubuntu 26.04
    # glslang-tools 16.2.0-2 (SHA-256 from the signed APT metadata), extracted
    # to tools/host-glslang.
    echo "2ad3ea819da071f1eff681415d35bc0af03e076ed5ff3993bffb558095adbb4d  $workspace/downloads/host-glslang/glslang-tools_16.2.0-2_amd64.deb" | sha256sum -c -
    export PATH=$tools/host-glslang/usr/bin:$PATH
fi
echo "$kmscube_sha256  $kmscube_tar" | sha256sum -c -
test -f "$sysroot/sysroot-packages.json"

# compiler-rt start files and builtins from the sysroot's Alpine compiler-rt,
# with clang 18's own headers.
rm -rf "$resource"
mkdir -p "$resource/lib/linux"
ln -s "$(realpath "$llvm/lib/clang/18/include")" "$resource/include"
cp "$sysroot"/usr/lib/llvm20/lib/clang/20/lib/aarch64-alpine-linux-musl/{clang_rt.crtbegin-aarch64.o,clang_rt.crtend-aarch64.o,libclang_rt.builtins-aarch64.a} \
   "$resource/lib/linux/"

mkdir -p "$out"
cross=$out/aarch64-musl.cross
common="'--target=aarch64-linux-musl', '--sysroot=$sysroot', '-resource-dir', '$resource'"
cat > "$cross" <<EOF
[binaries]
c = ['$llvm/bin/clang', $common]
cpp = ['$llvm/bin/clang++', $common, '-nostdinc++',
       '-isystem', '$sysroot/usr/include/c++/14.2.0',
       '-isystem', '$sysroot/usr/include/c++/14.2.0/aarch64-alpine-linux-musl']
ar = '$llvm/bin/llvm-ar'
strip = '$llvm/bin/llvm-strip'
pkg-config = '$venv/bin/pkgconf'

[built-in options]
c_link_args = ['-fuse-ld=lld', '-rtlib=compiler-rt', '-unwindlib=libgcc']
cpp_link_args = ['-fuse-ld=lld', '-rtlib=compiler-rt', '-unwindlib=libgcc']

[properties]
sys_root = '$sysroot'
pkg_config_libdir = ['$sysroot/usr/lib/pkgconfig', '$out/stage/usr/lib/pkgconfig']

[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'cortex-a76'
endian = 'little'
EOF

export PATH=$venv/bin:$tools/host-build/usr/bin:$PATH
export PKG_CONFIG_SYSROOT_DIR=$sysroot
# The extracted host bison looks for its m4 skeletons under /usr/share by default.
export BISON_PKGDATADIR=$tools/host-build/usr/share/bison M4=$tools/host-build/usr/bin/m4

rm -rf "$out/mesa-src" "$out/mesa-build" "$out/stage" "$out/kmscube-src" "$out/kmscube-build"
mkdir -p "$out/mesa-src" "$out/kmscube-src"
tar -xJf "$mesa_tar" -C "$out/mesa-src" --strip-components=1
tar -xzf "$kmscube_tar" -C "$out/kmscube-src" --strip-components=1

meson setup "$out/mesa-build" "$out/mesa-src" --cross-file "$cross" --wrap-mode=nodownload \
    --prefix=/usr --libdir=lib --buildtype=release -Db_ndebug=true -Dstrip=true \
    -Dplatforms= -Dgallium-drivers=freedreno -Dfreedreno-kmds=msm -Dvulkan-drivers=$vulkan_drivers \
    -Degl=enabled -Dgbm=enabled -Dgles1=disabled -Dgles2=enabled -Dopengl=true \
    -Dglx=disabled -Dglvnd=disabled -Dllvm=disabled -Dshader-cache=disabled -Dzstd=disabled \
    -Dxmlconfig=disabled -Dexpat=disabled -Dvalgrind=disabled -Dlibunwind=disabled -Dlmsensors=disabled \
    -Dbuild-tests=false -Dgallium-va=disabled -Dgallium-vdpau=disabled \
    -Dgallium-rusticl=false -Dvideo-codecs= \
    -Dtools= -Dperfetto=false -Dteflon=false -Dandroid-libbacktrace=disabled \
    -Dhtml-docs=disabled -Dselinux=false
ninja -C "$out/mesa-build"
DESTDIR="$out/stage" ninja -C "$out/mesa-build" install

# kmscube links against the freshly staged Mesa: give it a merged sysroot so
# pkg-config's sysroot prefix points at both Alpine and Mesa files.
rm -rf "$out/sysroot-kmscube"
cp -a "$sysroot" "$out/sysroot-kmscube"
cp -a "$out/stage/." "$out/sysroot-kmscube/"
sed "s|$sysroot|$out/sysroot-kmscube|g" "$cross" > "$out/aarch64-musl-kmscube.cross"
PKG_CONFIG_SYSROOT_DIR=$out/sysroot-kmscube meson setup "$out/kmscube-build" "$out/kmscube-src" \
    --cross-file "$out/aarch64-musl-kmscube.cross" --wrap-mode=nodownload \
    --prefix=/usr --buildtype=release -Dstrip=true -Dgstreamer=disabled
ninja -C "$out/kmscube-build"
DESTDIR="$out/stage" ninja -C "$out/kmscube-build" install

# Runtime manifest: the files the RAM test needs, with their hashes and the
# pinned inputs they came from. mesa_payload.py checks it before packaging.
python3 - "$out" "$sysroot" "$src" "$mesa_sha256" "$kmscube_sha256" "$kmscube_commit" "$variant" <<'PY'
import hashlib, json, os, sys
from pathlib import Path
out, sysroot, src = map(Path, sys.argv[1:4])
variant = sys.argv[7]
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
files = {}
for rel in ('usr/lib/libgallium-25.1.9.so', 'usr/lib/libEGL.so.1.0.0', 'usr/lib/libGLESv2.so.2.0.0',
            'usr/lib/libgbm.so.1.0.0', 'usr/lib/gbm/dri_gbm.so', 'usr/bin/kmscube'):
    files[rel] = {'from': 'stage', 'sha256': sha(out / 'stage' / rel)}
for rel in ('lib/ld-musl-aarch64.so.1', 'usr/lib/libdrm.so.2.124.0', 'usr/lib/libpciaccess.so.0.11.1',
            'usr/lib/libz.so.1.3.2', 'usr/lib/libstdc++.so.6.0.33', 'usr/lib/libgcc_s.so.1'):
    files[rel] = {'from': 'sysroot', 'sha256': sha(sysroot / rel)}
links = {'lib/libc.musl-aarch64.so.1': 'ld-musl-aarch64.so.1', 'usr/lib/libEGL.so.1': 'libEGL.so.1.0.0',
         'usr/lib/libGLESv2.so.2': 'libGLESv2.so.2.0.0', 'usr/lib/libgbm.so.1': 'libgbm.so.1.0.0',
         'usr/lib/libdrm.so.2': 'libdrm.so.2.124.0', 'usr/lib/libpciaccess.so.0': 'libpciaccess.so.0.11.1',
         'usr/lib/libz.so.1': 'libz.so.1.3.2', 'usr/lib/libstdc++.so.6': 'libstdc++.so.6.0.33'}
if variant == 'vulkan':
    for rel in ('usr/lib/libvulkan_freedreno.so', 'usr/share/vulkan/icd.d/freedreno_icd.cortex-a76.json'):
        files[rel] = {'from': 'stage', 'sha256': sha(out / 'stage' / rel)}
    sonames = {'libvulkan.so.1': 'libvulkan.so.1.4.313', 'libX11.so.6': 'libX11.so.6.4.0',
               'libxcb.so.1': 'libxcb.so.1.1.0', 'libXau.so.6': 'libXau.so.6.0.0',
               'libXdmcp.so.6': 'libXdmcp.so.6.0.0', 'libbsd.so.0': 'libbsd.so.0.12.2',
               'libmd.so.0': 'libmd.so.0.1.0', 'libwayland-client.so.0': 'libwayland-client.so.0.23.1',
               'libffi.so.8': 'libffi.so.8.1.4'}
    for soname, real in sonames.items():
        files['usr/lib/' + real] = {'from': 'sysroot', 'sha256': sha(sysroot / 'usr/lib' / real)}
        links['usr/lib/' + soname] = real
    for rel in ('usr/bin/vkcube', 'usr/bin/vulkaninfo'):
        files[rel] = {'from': 'sysroot', 'sha256': sha(sysroot / rel)}
licenses = {'usr/share/licenses/mesa/license.rst': out / 'mesa-src/docs/license.rst',
            'usr/share/licenses/kmscube/COPYING': out / 'kmscube-src/COPYING'}
result = {'variant': variant, 'mesa': {'version': '25.1.9', 'tarball_sha256': sys.argv[4]},
          'kmscube': {'commit': sys.argv[6], 'tarball_sha256': sys.argv[5]},
          'sysroot_packages_sha256': sha(sysroot / 'sysroot-packages.json'),
          'build_script_sha256': sha(src / 'miatoll/gpu/build_mesa.sh'),
          'files': files, 'links': links,
          'licenses': {k: {'source': str(v.relative_to(out)), 'sha256': sha(v)} for k, v in licenses.items()}}
(out / 'build-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
PY

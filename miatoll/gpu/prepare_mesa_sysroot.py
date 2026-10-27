#!/usr/bin/env python3
"""Prepare the aarch64 musl sysroot used to cross-build Mesa and kmscube.

Every package is an Alpine v3.22 main/aarch64 APK listed in the pinned
downloads/alpine-APKINDEX.tar.gz. Each APK is checked against its index entry
(size, control-segment SHA-1) and its .PKGINFO datahash before it is
extracted into tools/sysroot-mesa-aarch64. The kernel helper sysroot
tools/sysroot-aarch64 is left untouched.
"""
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import urllib.request
import zlib

WORKSPACE = Path(__file__).resolve().parents[3]
INDEX = WORKSPACE / 'downloads/alpine-APKINDEX.tar.gz'
CACHE = WORKSPACE / 'downloads/mesa-apk'
SYSROOT = WORKSPACE / 'tools/sysroot-mesa-aarch64'
URL = 'https://dl-cdn.alpinelinux.org/alpine/v3.22/main/aarch64/'
PACKAGES = ('musl', 'musl-dev', 'linux-headers', 'libgcc', 'libstdc++', 'libstdc++-dev',
            'libdrm', 'libdrm-dev', 'libpciaccess', 'libpciaccess-dev', 'expat', 'expat-dev',
            'zlib', 'zlib-dev', 'compiler-rt',
            # Vulkan loader and headers, and vulkan-tools (vkcube, vulkaninfo) with the
            # X11/Wayland client libraries it links against; the RAM test uses its
            # VK_KHR_display path only.
            'vulkan-headers', 'vulkan-loader', 'vulkan-loader-dev', 'vulkan-tools',
            'libx11', 'libxcb', 'libxau', 'libxdmcp', 'libbsd', 'libmd', 'wayland-libs-client', 'libffi')


def index_entries():
    with tarfile.open(INDEX) as archive:
        text = archive.extractfile('APKINDEX').read().decode()
    entries = {}
    for block in text.split('\n\n'):
        fields = dict(line.split(':', 1) for line in block.splitlines() if ':' in line[:2])
        if fields.get('P') in PACKAGES:
            entries[fields['P']] = fields
    return entries


def split_apk(data):
    members = []
    while data:
        inflater = zlib.decompressobj(31)
        payload = inflater.decompress(data)
        members.append((data[:len(data) - len(inflater.unused_data)], payload))
        data = inflater.unused_data
    return members


def main():
    entries = index_entries()
    missing = set(PACKAGES) - set(entries)
    if missing:
        raise SystemExit('Not in APKINDEX: ' + ', '.join(sorted(missing)))
    if SYSROOT.exists():
        shutil.rmtree(SYSROOT)
    SYSROOT.mkdir(parents=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    record = {}
    for name in PACKAGES:
        entry = entries[name]
        filename = f"{name}-{entry['V']}.apk"
        path = CACHE / filename
        if not path.exists():
            urllib.request.urlretrieve(URL + filename, path)
        data = path.read_bytes()
        if len(data) != int(entry['S']):
            raise SystemExit(f'{filename}: size differs from APKINDEX')
        members = split_apk(data)
        control = next(item for item in members if b'.PKGINFO' in item[1][:2048])
        if not entry['C'].startswith('Q1') or hashlib.sha1(control[0]).digest() != base64.b64decode(entry['C'][2:]):
            raise SystemExit(f'{filename}: control checksum differs from APKINDEX')
        with tarfile.open(fileobj=io.BytesIO(control[1])) as archive:
            info = dict(line.split(' = ', 1) for line in
                        archive.extractfile('.PKGINFO').read().decode().splitlines() if ' = ' in line)
        if hashlib.sha256(members[-1][0]).hexdigest() != info['datahash']:
            raise SystemExit(f'{filename}: datahash mismatch')
        with tarfile.open(fileobj=io.BytesIO(members[-1][1])) as archive:
            archive.extractall(SYSROOT, filter='data')
        record[name] = {'version': entry['V'], 'bytes': len(data),
                        'sha256': hashlib.sha256(data).hexdigest(), 'apkindex_checksum': entry['C']}
    # libgcc ships only the runtime soname; the -lgcc_s link name lives in the gcc package.
    (SYSROOT / 'usr/lib/libgcc_s.so').symlink_to('libgcc_s.so.1')
    record['local_links'] = {'usr/lib/libgcc_s.so': 'libgcc_s.so.1'}
    (SYSROOT / 'sysroot-packages.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()

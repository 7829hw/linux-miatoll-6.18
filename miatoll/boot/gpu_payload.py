"""Pinned Adreno A618 firmware for the gpu1 RAMdisk.

a630_sqe.fw and a630_gmu.bin come from the Alpine linux-firmware-qcom
20250509-r0 package (APK SHA-256, control checksum and datahash are checked,
license file pinned from linux-firmware tag 20250509). The zap shader is
curtana's a615_zap.mbn from sm7125-mainline/firmware-xiaomi-miatoll a7073ad1,
checked by size, Git blob SHA-1 and SHA-256. Provenance: miatoll/reference/gpu1.
"""
import base64
import hashlib
import io
from pathlib import Path
import subprocess
import tarfile
import zlib

PACKAGE = 'linux-firmware-qcom-20250509-r0.apk'
PACKAGE_BYTES = 115509089
PACKAGE_SHA256 = '80edeec02370ff7684f57a40a41ead3c13ba9aa6aeec7a89d8d21bee072c1533'
CONTROL_SHA1 = 'zn3gmuliANevh5t/5pO5tdz1WsI='
NAMES = ('a630_sqe.fw', 'a630_gmu.bin')
ZAP = ('lib/firmware/qcom/sm7125/miatoll/a615_zap.mbn', 14272, '866ed58584de9e1a67e8cf98c4b3cafe5ecb7c31',
       '67d535d27ba2424e597a7bd8c54b723854d1c45666ad48270b564e995ac0e063')
LICENSE_SHA256 = 'be904cd28cb292b80cdb6cf412ab0d9159d431671e987ad433c1f62e0988a9bc'


def load(workspace):
    """Return {initramfs path: (bytes, mode)} and a provenance summary."""
    workspace = Path(workspace)
    data = (workspace / 'downloads' / PACKAGE).read_bytes()
    if len(data) != PACKAGE_BYTES or hashlib.sha256(data).hexdigest() != PACKAGE_SHA256:
        raise ValueError('GPU firmware package differs from pinned input')
    rest = data
    members = []
    while rest:
        inflater = zlib.decompressobj(31)
        payload = inflater.decompress(rest)
        members.append((rest[:len(rest) - len(inflater.unused_data)], payload))
        rest = inflater.unused_data
    control = next(item for item in members if b'.PKGINFO' in item[1][:2048])
    if hashlib.sha1(control[0]).digest() != base64.b64decode(CONTROL_SHA1):
        raise ValueError('GPU APK control checksum mismatch')
    with tarfile.open(fileobj=io.BytesIO(control[1])) as archive:
        info = dict(line.split(' = ', 1) for line in archive.extractfile('.PKGINFO').read().decode().splitlines()
                    if ' = ' in line)
    if info['pkgname'] != 'linux-firmware-qcom' or info['pkgver'] != '20250509-r0':
        raise ValueError('Unexpected GPU APK identity')
    if hashlib.sha256(members[-1][0]).hexdigest() != info['datahash']:
        raise ValueError('GPU APK datahash mismatch')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(members[-1][1])) as archive:
        for name in NAMES:
            compressed = archive.extractfile('lib/firmware/qcom/' + name + '.zst').read()
            raw = subprocess.check_output([str(workspace / 'tools/host-build/usr/bin/zstd'), '-dc'], input=compressed)
            files['lib/firmware/qcom/' + name] = (raw, 0o644)
    path, size, blob, sha256 = ZAP
    zap = (workspace / 'downloads/gpu-firmware' / path).read_bytes()
    if len(zap) != size or hashlib.sha256(zap).hexdigest() != sha256 or \
            hashlib.sha1(b'blob %d\0' % size + zap).hexdigest() != blob:
        raise ValueError('Zap shader differs from pinned input')
    files[path] = (zap, 0o644)
    license_data = (workspace / 'reference/gpu/LICENSE.qcom').read_bytes()
    if hashlib.sha256(license_data).hexdigest() != LICENSE_SHA256:
        raise ValueError('LICENSE.qcom checksum mismatch')
    files['usr/share/licenses/linux-firmware-qcom/LICENSE.qcom'] = (license_data, 0o644)
    summary = {'firmware': {name: {'bytes': len(blob_data), 'sha256': hashlib.sha256(blob_data).hexdigest()}
                            for name, (blob_data, _) in files.items() if name.startswith('lib/firmware/')},
               'firmware_package': {'name': PACKAGE, 'sha256': PACKAGE_SHA256},
               'zap_git_blob_sha1': blob}
    return files, summary

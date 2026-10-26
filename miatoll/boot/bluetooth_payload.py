"""Pinned WCN399x Bluetooth firmware and the btctl tool for the bt1 RAMdisk.

The firmware comes from the pinned Alpine linux-firmware-qca package used by
the earlier curtana bring-up (APK SHA-256, control checksum and datahash are
checked); btctl revision 4 is checked against its recorded binary and source
hashes. Provenance is copied to miatoll/reference/bt1.
"""
import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import tarfile
import zlib

PACKAGE = 'linux-firmware-qca-20250509-r0.apk'
PACKAGE_SHA256 = '5b26191c5e3bba0899d6c178ce159066c52f6eac10bb404965db4afdb37d05b9'
NAMES = ('crbtfw21.tlv', 'crbtfw32.tlv', 'crnv21.bin', 'crnv32.bin', 'crnv32u.bin')
LICENSES = {
    'LICENSE.QualcommAtheros_ath10k': '337a55102138d7baa143ee4a4c6c91693e0113fece35d380b2a12109e8c23b3f',
    'NOTICE.txt': '600276e0992c8e5a85300d605fb2db6132ffcf2a21ddcfd0e8566a19e0f491c3',
}


def load_bluetooth_firmware(root):
    root = Path(root)
    data = (root / 'downloads' / PACKAGE).read_bytes()
    if len(data) != 2108951 or hashlib.sha256(data).hexdigest() != PACKAGE_SHA256:
        raise ValueError('Bluetooth firmware package differs from pinned input')
    rest = data
    members = []
    while rest:
        inflater = zlib.decompressobj(31)
        payload = inflater.decompress(rest)
        compressed = rest[:len(rest) - len(inflater.unused_data)]
        members.append((compressed, payload))
        rest = inflater.unused_data
    control = next(item for item in members if b'.PKGINFO' in item[1][:2048])
    if hashlib.sha1(control[0]).digest() != base64.b64decode('P3JUOnopnLsEKsMEka2en70SUzY='):
        raise ValueError('Bluetooth APK control checksum mismatch')
    with tarfile.open(fileobj=io.BytesIO(control[1])) as archive:
        info = dict(line.split(' = ', 1) for line in archive.extractfile('.PKGINFO').read().decode().splitlines() if ' = ' in line)
    if info['pkgname'] != 'linux-firmware-qca' or info['pkgver'] != '20250509-r0':
        raise ValueError('Unexpected Bluetooth APK identity')
    if hashlib.sha256(members[-1][0]).hexdigest() != info['datahash']:
        raise ValueError('Bluetooth APK datahash mismatch')
    result = {}
    with tarfile.open(fileobj=io.BytesIO(members[-1][1])) as archive:
        for name in NAMES:
            source = 'lib/firmware/qca/' + name + '.zst'
            compressed = archive.extractfile(source).read()
            raw = subprocess.check_output([str(root / 'tools/host-build/usr/bin/zstd'), '-dc'], input=compressed)
            header = struct.unpack_from('<I', raw)[0]
            # WCN399x NVM files use the combined BT/FM container (type 4),
            # which btqca's TLV_TYPE_NVM parser explicitly unwraps.
            if header & 0xff != (1 if name.endswith('.tlv') else 4) or 4 + (header >> 8) != len(raw):
                raise ValueError('Unexpected Bluetooth TLV framing: ' + name)
            result['lib/firmware/qca/' + name] = raw
    for name, expected in LICENSES.items():
        if hashlib.sha256((root / 'reference/bluetooth' / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Bluetooth license checksum mismatch: ' + name)
    return result


BTCTL_DIR = 'out-btctl-pair1'


def load(workspace):
    """Return {initramfs path: (bytes, mode)} and a provenance summary."""
    workspace = Path(workspace)
    files = {path: (data, 0o644) for path, data in load_bluetooth_firmware(workspace).items()}
    record = json.loads((workspace / BTCTL_DIR / 'build-result.json').read_text())
    data = (workspace / BTCTL_DIR / 'btctl').read_bytes()
    assert len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['sha256'], 'btctl changed'
    assert record['static_arm64_elf_verified'], 'Unverified btctl build'
    for path, sha256 in record['sources'].items():
        assert hashlib.sha256((workspace / path).read_bytes()).hexdigest() == sha256, 'Rebuild btctl: ' + path
    files['bin/btctl'] = (data, 0o755)
    for name in LICENSES:
        files['usr/share/licenses/linux-firmware-qca/' + name] = (
            (workspace / 'reference/bluetooth' / name).read_bytes(), 0o644)
    summary = {'firmware': {path: {'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}
                            for path, (blob, _) in files.items() if path.startswith('lib/firmware/')},
               'firmware_package': {'name': PACKAGE, 'sha256': PACKAGE_SHA256},
               'btctl': {'version': record['version'], 'bytes': record['bytes'], 'sha256': record['sha256']}}
    return files, summary

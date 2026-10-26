"""Pinned WCN3990 firmware and static user-space tools for the wifi1 RAMdisk.

The firmware and tool binaries stay outside Git in the workspace. Every file
is checked against the size/SHA-256 (and Git blob for firmware) recorded by
the earlier curtana bring-up, and each tool against the hashes of the sources
it was built from (workspace userspace/, see reference/wifi1-payload.json).
"""
import hashlib
import json
import subprocess
from pathlib import Path

# initramfs path, workspace source, bytes, Git blob SHA-1, SHA-256
FIRMWARE = (
    ('lib/firmware/qcom/sm7125/miatoll/modem.mbn',
     'downloads/wifi-firmware/lib/firmware/qcom/sm7125/miatoll/modem.mbn', 62183024,
     '7e890a505bcc8f7bf1de085c5b653db5a00238e4',
     '112271f1756f7b8f10567c10bc2923fa27622b34468087dc055524113535cf6d'),
    ('lib/firmware/qcom/sm7125/miatoll/wlanmdsp.mbn',
     'downloads/wifi-firmware/lib/firmware/qcom/sm7125/miatoll/wlanmdsp.mbn', 3844700,
     '485353b9f054d0121f3c3b882b92575338a112a9',
     '39c60ee8ba62b720bbfb3183cadff21f94353f253470429e84868f2d343b7ab9'),
    ('lib/firmware/ath10k/WCN3990/hw1.0/board-2.bin',
     'downloads/wifi-firmware/lib/firmware/postmarketos/ath10k/WCN3990/hw1.0/board-2.bin.zst', 29537,
     '16dfcacb004c8fc8537bba5ede05fb20c111710a',
     '5e28e3ebe6cb09ddb02c1c5c407437d3224a3e440ed9b5245638e49919b9b762'),
    ('lib/firmware/ath10k/WCN3990/hw1.0/firmware-5.bin',
     'downloads/wifi-firmware/lib/firmware/ath10k/WCN3990/hw1.0/firmware-5.bin', 60,
     '69b4cae2d5e9fc340fbc43f3f120dd0698d907af',
     'fef6539e0127579536bc977be57a90d018b83f2931fedc3a8870fbe38d6c4127'),
)
# wireless-regdb from the pinned aarch64 sysroot
REGDB = {
    'lib/firmware/regulatory.db': 'd67150c8925a98a4783c2c9a3e652b5a21fcdf8119875e1d2860c7c180fa98f8',
    'lib/firmware/regulatory.db.p7s': '704ba48e3b12a28d3ed9411e526f127870201ba5007ee0c17ae92dafe2444fa5',
}
TOOLS = (('out-remote-services', ('tqftpserv', 'rmtfs', 'qrtr-lookup')), ('out-wifi-tools', ('iw',)))
LICENSES = {
    'usr/share/licenses/rmtfs/LICENSE': 'userspace/rmtfs/LICENSE',
    'usr/share/licenses/tqftpserv/LICENSE': 'userspace/tqftpserv/LICENSE',
    'usr/share/licenses/qrtr/LICENSE': 'userspace/qrtr/LICENSE',
    'usr/share/licenses/iw/COPYING': 'userspace/iw/COPYING',
    'usr/share/licenses/libnl/COPYING': 'reference/wifi-tools/libnl-COPYING',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(workspace, connect=False):
    """Return {initramfs path: (bytes, mode)} and a provenance summary.

    With connect, also add the validated static wpa_supplicant and wpa_cli.
    """
    workspace = Path(workspace)
    files, summary = {}, {'firmware': {}, 'tools': {}}
    for target, source, size, blob, sha256 in FIRMWARE:
        data = (workspace / source).read_bytes()
        assert len(data) == size and digest(data) == sha256, 'Wi-Fi firmware changed: ' + source
        assert hashlib.sha1(b'blob %d\0' % size + data).hexdigest() == blob, 'Git blob mismatch: ' + source
        if source.endswith('.zst'):
            zstd = workspace / 'tools/host-build/usr/bin/zstd'
            data = subprocess.check_output([str(zstd), '-dc', str(workspace / source)])
            assert len(data) == 949600 and data.startswith(b'QCA-ATH10K-BOARD\0'), 'Unexpected board-2.bin'
        files[target] = (data, 0o644)
        summary['firmware'][target] = {'bytes': len(data), 'sha256': digest(data), 'source_git_blob': blob}
    for target, sha256 in REGDB.items():
        data = (workspace / 'tools/sysroot-aarch64' / target).read_bytes()
        assert digest(data) == sha256, 'regulatory database changed: ' + target
        files[target] = (data, 0o644)
        summary['firmware'][target] = {'bytes': len(data), 'sha256': sha256}
    for directory, names in TOOLS:
        record = json.loads((workspace / directory / 'build-result.json').read_text())
        for name in names:
            entry = record.get(name, record)
            data = (workspace / directory / name).read_bytes()
            assert len(data) == entry['bytes'] and digest(data) == entry['sha256'], 'Tool changed: ' + name
            assert entry['elf_aarch64_static_verified'], 'Unverified tool: ' + name
            for path, sha256 in entry['sources'].items():
                assert digest((workspace / path).read_bytes()) == sha256, 'Rebuild after source change: ' + path
            files['bin/' + name] = (data, 0o755)
            summary['tools'][name] = {'bytes': len(data), 'sha256': entry['sha256'],
                                      'built_from': directory, 'source_files': len(entry['sources'])}
    if connect:
        record = json.loads((workspace / 'out-wifi-connect/build-result.json').read_text())
        assert record['actual_sae_config_parser_verified'], 'Unverified wpa_supplicant build'
        for path in record['sources']:
            assert (workspace / path).is_file(), 'Missing wpa_supplicant source: ' + path
        for name in ('wpa_supplicant', 'wpa_cli'):
            entry = record['binaries'][name]
            data = (workspace / 'out-wifi-connect' / name).read_bytes()
            assert len(data) == entry['bytes'] and digest(data) == entry['sha256'], 'Tool changed: ' + name
            assert entry['elf_aarch64_static_verified'], 'Unverified tool: ' + name
            files['bin/' + name] = (data, 0o755)
            summary['tools'][name] = {'bytes': len(data), 'sha256': entry['sha256'],
                                      'built_from': 'out-wifi-connect', 'source_files': len(record['sources'])}
        files['usr/share/licenses/wpa_supplicant/COPYING'] = (
            (workspace / 'userspace/wpa_supplicant/COPYING').read_bytes(), 0o644)
    for target, source in LICENSES.items():
        files[target] = ((workspace / source).read_bytes(), 0o644)
    return files, summary

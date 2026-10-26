"""Build a module-free ARM64 RAM diagnostic initramfs.

Only the touch profiles carry firmware: the pinned Huaxing FT8756 RAM image.
"""
import gzip
import hashlib
import io
import json
from pathlib import Path
import stat
import struct
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BOOT = ROOT / 'miatoll/boot'
APK_SHA256 = 'ee469aee2958feffd7f64dd96655704025ff60af614f77a1d7323dc237c34da2'
# sm7125-mainline/firmware-xiaomi-miatoll blob e4fb163b71b430156b4134b7a311fc939addb838
TOUCH_FIRMWARE = 'focaltech_ts_fw_huaxing.bin'
TOUCH_FIRMWARE_SHA256 = '83e7fb01d3a0595984c2b701633db83db4eb71eb4fd613aa635437a768ad6c9b'

def build(output, profile='boot1'):
    assert profile in ('boot1', 'display1', 'display2', 'touch1', 'storage1', 'usb2')
    script_names = ['init', 'usb-gadget', 'boot-probe']
    if profile != 'boot1':
        script_names += ['display-banner', 'display-probe']
    touch = profile in ('touch1', 'storage1', 'usb2')
    if touch:
        script_names += ['touch-probe', 'touch-events']
    if profile in ('storage1', 'usb2'):
        script_names += ['storage-probe']
    if profile == 'usb2':
        script_names += ['usb-host-watch']
    package = ROOT.parent / 'downloads/busybox-static-1.37.0-r20.apk'
    assert hashlib.sha256(package.read_bytes()).hexdigest() == APK_SHA256
    with tarfile.open(package, 'r:gz', ignore_zeros=True) as archive:
        binary = archive.extractfile('bin/busybox.static').read()
    assert binary[:6] == b'\x7fELF\x02\x01'
    assert struct.unpack_from('<H', binary, 18)[0] == 183
    offset = struct.unpack_from('<Q', binary, 32)[0]
    entry_size, count = struct.unpack_from('<HH', binary, 54)
    assert all(struct.unpack_from('<I', binary, offset + i * entry_size)[0] not in (2, 3)
               for i in range(count)), 'BusyBox must be static'
    qemu = ROOT.parent / 'tools/qemu/qemu-aarch64-static'
    required = {'sh', 'mount', 'uname', 'mkdir', 'cat', 'head', 'tail', 'grep',
                'blockdev', 'watchdog', 'tr', 'setsid', 'sleep', 'ln', 'ls', 'dmesg'}
    if touch:
        required |= {'hexdump', 'timeout', 'seq', 'cut', 'basename', 'readlink'}
    if profile in ('storage1', 'usb2'):
        required |= {'dd', 'sha256sum', 'sync'}
    with tempfile.TemporaryDirectory(prefix='boot1-busybox-') as temporary:
        executable = Path(temporary) / 'busybox'
        executable.write_bytes(binary)
        executable.chmod(0o755)
        applets = subprocess.check_output([str(qemu), str(executable), '--list'], text=True).splitlines()
        assert not required - set(applets), required - set(applets)
        help_result = subprocess.run([str(qemu), str(executable), 'setsid', '--help'],
                                     capture_output=True, text=True, check=True)
        assert 'Set controlling terminal to stdin' in help_result.stdout + help_result.stderr
        for name in script_names:
            subprocess.run([str(qemu), str(executable), 'sh', '-n', str(BOOT / name)], check=True)
    stream = io.BytesIO()
    inode = 0
    members = []
    def add(name, mode, data=b'', major=0, minor=0):
        nonlocal inode
        inode += 1
        encoded = name.encode() + b'\0'
        fields = (inode, mode, 0, 0, 2 if stat.S_ISDIR(mode) else 1, 0,
                  len(data), 0, 0, major, minor, len(encoded), 0)
        stream.write(b'070701' + b''.join(f'{n:08x}'.encode() for n in fields))
        stream.write(encoded)
        stream.write(b'\0' * (-stream.tell() % 4))
        stream.write(data)
        stream.write(b'\0' * (-stream.tell() % 4))
        members.append(name)
    for name in ('.', 'bin', 'sbin', 'dev', 'proc', 'sys', 'run', 'etc', 'root'):
        add(name, stat.S_IFDIR | 0o755)
    add('dev/console', stat.S_IFCHR | 0o600, major=5, minor=1)
    add('bin/busybox', stat.S_IFREG | 0o755, binary)
    for name in sorted(required):
        add('bin/' + name, stat.S_IFLNK | 0o777, b'busybox')
    add('init', stat.S_IFREG | 0o755, (BOOT / 'init').read_bytes())
    for name in script_names[1:]:
        add('bin/' + name, stat.S_IFREG | 0o755, (BOOT / name).read_bytes())
    firmware = None
    if touch:
        firmware = (ROOT.parent / 'downloads' / TOUCH_FIRMWARE).read_bytes()
        assert hashlib.sha256(firmware).hexdigest() == TOUCH_FIRMWARE_SHA256
        for name in ('lib', 'lib/firmware'):
            add(name, stat.S_IFDIR | 0o755)
        add('lib/firmware/' + TOUCH_FIRMWARE, stat.S_IFREG | 0o644, firmware)
    add('TRAILER!!!', 0)
    allowed = {'lib', 'lib/firmware', 'lib/firmware/' + TOUCH_FIRMWARE} if firmware else set()
    assert not any(name.startswith(('lib', 'vendor/', 'system/')) and name not in allowed
                   for name in members)
    compressed = gzip.compress(stream.getvalue(), mtime=0)
    output.write_bytes(compressed)
    result = {'bytes': len(compressed), 'sha256': hashlib.sha256(compressed).hexdigest(),
              'busybox_apk_sha256': APK_SHA256, 'members': members,
              'arm64_static_busybox_and_shell_syntax_passed': True,
              'contains_firmware': [TOUCH_FIRMWARE] if firmware else False,
              'firmware_sha256': TOUCH_FIRMWARE_SHA256 if firmware else None,
              'contains_modules': False,
              'mounts_android_filesystems': False, 'profile': profile}
    output.with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
    return result

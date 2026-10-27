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

def build_static_tool(source, libraries=('-lc',)):
    """Compile a static ARM64 helper from miatoll/boot with the pinned toolchain."""
    tools = ROOT.parent / 'tools'
    sysroot = tools / 'sysroot-aarch64'
    builtins = next(sysroot.rglob('libclang_rt.builtins-aarch64.a'))
    clang = tools / 'llvm18/usr/lib/llvm-18/bin/clang'
    with tempfile.TemporaryDirectory(prefix='static-tool-') as temporary:
        output = Path(temporary) / 'tool'
        subprocess.run([str(clang), '--target=aarch64-linux-musl', '--sysroot=' + str(sysroot), '-O2',
                        '-Wall', '-Wextra', '-Werror', '-mno-outline-atomics', '-fuse-ld=lld', '-static',
                        '-nostdlib', str(sysroot / 'usr/lib/crt1.o'), str(sysroot / 'usr/lib/crti.o'),
                        str(BOOT / source), '-L' + str(sysroot / 'usr/lib'), '-Wl,--start-group',
                        *libraries, str(builtins), '-Wl,--end-group', str(sysroot / 'usr/lib/crtn.o'),
                        '-o', str(output)], check=True)
        return output.read_bytes()


TINYALSA_TARBALL = 'tinyalsa/tinyalsa-2.0.0.tar.gz'
TINYALSA_SHA256 = '573ae0b2d3480851c1d2a12503ead2beea27f92d44ed47b74b553ba947994ef1'


def build_tinyalsa():
    """Build static tinymix/tinyplay/tinycap from the pinned tinyalsa v2.0.0 release."""
    tarball = ROOT.parent / 'downloads' / TINYALSA_TARBALL
    assert hashlib.sha256(tarball.read_bytes()).hexdigest() == TINYALSA_SHA256
    tools = ROOT.parent / 'tools'
    sysroot = tools / 'sysroot-aarch64'
    builtins = next(sysroot.rglob('libclang_rt.builtins-aarch64.a'))
    clang = tools / 'llvm18/usr/lib/llvm-18/bin/clang'
    result = {}
    with tempfile.TemporaryDirectory(prefix='tinyalsa-') as temporary:
        with tarfile.open(tarball) as archive:
            archive.extractall(temporary, filter='data')
        source = Path(temporary) / 'tinyalsa-2.0.0'
        library = [str(source / 'src' / name) for name in
                   ('pcm.c', 'pcm_hw.c', 'mixer.c', 'mixer_hw.c', 'limits.c', 'snd_card_plugin.c')]
        for tool in ('tinymix', 'tinyplay', 'tinycap'):
            output = Path(temporary) / tool
            subprocess.run([str(clang), '--target=aarch64-linux-musl', '--sysroot=' + str(sysroot), '-O2',
                            '-mno-outline-atomics', '-fuse-ld=lld', '-static', '-nostdlib',
                            '-I' + str(source / 'include'), str(sysroot / 'usr/lib/crt1.o'),
                            str(sysroot / 'usr/lib/crti.o'), str(source / 'utils' / (tool + '.c')), *library,
                            '-L' + str(sysroot / 'usr/lib'), '-Wl,--start-group', '-lc', str(builtins),
                            '-Wl,--end-group', str(sysroot / 'usr/lib/crtn.o'), '-o', str(output)], check=True)
            result[tool] = output.read_bytes()
        result['NOTICE'] = (source / 'NOTICE').read_bytes()
    return result


def quiet_tone_wav(seconds=3, rate=48000, frequency=1000, peak=256, fade_ms=10):
    """Stereo S16 WAV of a quiet sine with linear fades (peak 256/32768, -42.1 dBFS)."""
    import math
    frames = seconds * rate
    fade = rate * fade_ms // 1000
    body = bytearray()
    for n in range(frames):
        gain = min(1.0, n / fade, (frames - 1 - n) / fade)
        value = int(round(peak * gain * math.sin(2 * math.pi * frequency * n / rate)))
        body += struct.pack('<hh', value, value)
    header = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + len(body), b'WAVE', b'fmt ', 16, 1, 2,
                         rate, rate * 4, 4, 16, b'data', len(body))
    return header + bytes(body)


def build(output, profile='boot1'):
    assert profile in ('boot1', 'display1', 'display2', 'touch1', 'storage1', 'usb2', 'wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6')
    script_names = ['init', 'usb-gadget', 'boot-probe']
    if profile != 'boot1':
        script_names += ['display-banner', 'display-probe']
    touch = profile in ('touch1', 'storage1', 'usb2', 'wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6')
    if touch:
        script_names += ['touch-probe', 'touch-events']
    if profile in ('storage1', 'usb2', 'wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
        script_names += ['storage-probe']
    if profile in ('usb2', 'wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
        script_names += ['usb-host-watch']
    if profile in ('wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
        script_names += ['wifi-start', 'wifi-services', 'wifi-board', 'wifi-probe', 'wifi-scan']
    if profile in ('wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
        script_names += ['wifi-join', 'wifi-udhcpc', 'wifi-link-probe', 'wifi-disconnect']
    if profile in ('bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
        script_names += ['bt-start', 'bt-probe']
    if profile in ('battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
        script_names += ['battery-probe']
    reboot_tool = profile in ('reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6')
    if reboot_tool:
        script_names += ['fastboot-reboot']
    if profile in ('audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
        script_names += ['audio-init', 'audio-probe']
    if profile in ('audio3', 'audio4', 'audio5', 'audio6'):
        script_names += ['audio-path']
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
    if profile in ('storage1', 'usb2', 'wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
        required |= {'dd', 'sha256sum', 'sync', 'chmod', 'uniq'}
    if profile in ('wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
        required |= {'sed', 'awk', 'mktemp', 'stat', 'mount', 'umount', 'cp', 'mv', 'rm', 'kill', 'ip'}
    if profile in ('wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
        required |= {'stty', 'tee', 'ifconfig', 'udhcpc', 'ping'}
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
    if profile in ('wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
        # wpa_cli binds its client socket in /tmp.
        add('tmp', stat.S_IFDIR | 0o1777)
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
    wifi = {}
    if profile in ('wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
        import wifi_payload
        wifi, wifi_summary = wifi_payload.load(ROOT.parent, connect=profile in ('wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'))
        if profile in ('audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
            import audio_payload
            audio, audio_summary = audio_payload.load(ROOT.parent)
            wifi.update(audio)
            wifi_summary['audio'] = audio_summary
        if profile in ('bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
            import bluetooth_payload
            bluetooth, bluetooth_summary = bluetooth_payload.load(ROOT.parent)
            wifi.update(bluetooth)
            wifi_summary['bluetooth'] = bluetooth_summary
        made = {'lib', 'lib/firmware'}
        for name in sorted(wifi):
            parts = name.split('/')
            for depth in range(1, len(parts)):
                directory = '/'.join(parts[:depth])
                if directory not in made and directory != 'bin':
                    add(directory, stat.S_IFDIR | 0o755)
                    made.add(directory)
            data, mode = wifi[name]
            add(name, stat.S_IFREG | mode, data)
    reboot_mode = None
    if reboot_tool:
        reboot_mode = build_static_tool('reboot-mode.c')
        assert reboot_mode[:4] == b'\x7fELF'
        add('bin/reboot-mode', stat.S_IFREG | 0o755, reboot_mode)
    if profile in ('audio3', 'audio4', 'audio5', 'audio6'):
        tinyalsa = build_tinyalsa()
        for tool in ('tinymix', 'tinyplay', 'tinycap'):
            add('bin/' + tool, stat.S_IFREG | 0o755, tinyalsa[tool])
        add('usr/share/sounds', stat.S_IFDIR | 0o755)
        add('usr/share/sounds/quiet-1khz-3s.wav', stat.S_IFREG | 0o644, quiet_tone_wav())
        add('usr/share/licenses/tinyalsa', stat.S_IFDIR | 0o755)
        add('usr/share/licenses/tinyalsa/NOTICE', stat.S_IFREG | 0o644, tinyalsa['NOTICE'])
        # tinyplay 2.0.0 returned at once without playing here; pcm-test plays and records.
        add('bin/pcm-test', stat.S_IFREG | 0o755, build_static_tool('pcm-test.c', ('-lc', '-lm')))
    speaker_tone = None
    if profile in ('audio2', 'audio3', 'audio4', 'audio5', 'audio6'):
        speaker_tone = build_static_tool('speaker-tone.c', ('-lc', '-lm'))
        add('bin/speaker-tone', stat.S_IFREG | 0o755, speaker_tone)
    add('TRAILER!!!', 0)
    allowed = {'lib', 'lib/firmware', 'lib/firmware/' + TOUCH_FIRMWARE} if firmware else set()
    allowed |= {name for name in members if name.startswith('lib/firmware/') and profile in ('wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6')}
    assert not any(name.startswith(('lib', 'vendor/', 'system/')) and name not in allowed
                   for name in members)
    compressed = gzip.compress(stream.getvalue(), mtime=0)
    output.write_bytes(compressed)
    result = {'bytes': len(compressed), 'sha256': hashlib.sha256(compressed).hexdigest(),
              'busybox_apk_sha256': APK_SHA256, 'members': members,
              'arm64_static_busybox_and_shell_syntax_passed': True,
              'contains_firmware': [TOUCH_FIRMWARE] if firmware else False,
              'firmware_sha256': TOUCH_FIRMWARE_SHA256 if firmware else None,
              'wifi_payload': wifi_summary if wifi else None,
              'reboot_mode_sha256': hashlib.sha256(reboot_mode).hexdigest() if reboot_mode else None,
              'speaker_tone_sha256': hashlib.sha256(speaker_tone).hexdigest() if speaker_tone else None,
              'contains_modules': False,
              'mounts_android_filesystems': False, 'profile': profile}
    output.with_suffix('.json').write_text(json.dumps(result, indent=2) + '\n')
    return result

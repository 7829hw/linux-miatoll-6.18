#!/usr/bin/env python3
"""Run one curtana RAM boot test from WSL and store the raw logs.

This is the Linux counterpart of Test-Boot1.ps1. It checks the packaged image,
restarts the bootloader once, sends the image once with `fastboot boot`, then
collects the probe output and the kernel log from the Linux USB ACM console.
Only the fastboot subcommands in FASTBOOT_ALLOWED can be issued; nothing is
flashed or erased. The physical screen state is recorded separately with the
`observe` subcommand, from what the user reports.
"""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
REPORTS = ROOT / 'miatoll/reports/device-tests'
FASTBOOT = WORKSPACE / 'tools/platform-tools/fastboot'
ACM_ID = ('1d6b', '0104')
FASTBOOT_ID = ('18d1', 'd00d')
USBIPD = Path('/mnt/c/Program Files/usbipd-win/usbipd.exe')
FASTBOOT_ALLOWED = (('devices',), ('getvar', 'product'), ('reboot', 'bootloader'))  # plus `boot <image>`
LOG_END = re.compile(r'^BOOT1_KERNELLOG_EXIT=(\d+)\r?$', re.M)


class Stop(Exception):
    """Abort without retrying anything on the device."""


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Fastboot:
    def __init__(self, log):
        self.log = log

    def run(self, *args, serial=None, timeout=120):
        command = tuple(args)
        if command not in FASTBOOT_ALLOWED and not (command[:1] == ('boot',) and len(command) == 2):
            raise Stop('Refusing fastboot command outside the RAM test allowlist: ' + ' '.join(command))
        argv = [str(FASTBOOT)] + (['-s', serial] if serial else []) + list(command)
        try:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as expired:
            partial = b''.join(x for x in (expired.stdout, expired.stderr) if x).decode(errors='replace')
            with self.log.open('a', encoding='utf-8') as stream:
                stream.write('fastboot ' + ' '.join(argv[1:]) + '\n' + partial +
                             f'\nTIMEOUT after {timeout} s\n')
            raise Stop(f'fastboot timed out after {timeout} s; no automatic retry. Log: {self.log}')
        text = (result.stdout + result.stderr).strip()
        with self.log.open('a', encoding='utf-8') as stream:
            stream.write('fastboot ' + ' '.join(argv[1:]) + '\n' + text + '\n')
        print(text)
        if result.returncode:
            raise Stop(f'fastboot failed ({result.returncode}); no automatic retry. Log: {self.log}')
        return text


def usbipd_attach(ids):
    """Forward a shared Windows USB device to WSL; a no-op when absent or attached."""
    if USBIPD.exists():
        subprocess.run([str(USBIPD), 'attach', '--wsl', '--hardware-id', ':'.join(ids)],
                       capture_output=True, timeout=30)


def fastboot_serials(fastboot):
    return re.findall(r'^(\S+)\s+fastboot\s*$', fastboot.run('devices'), re.M)


def find_acm():
    for tty in sorted(Path('/sys/class/tty').glob('ttyACM*')):
        usb = (tty / 'device').resolve().parent
        try:
            ids = ((usb / 'idVendor').read_text().strip(), (usb / 'idProduct').read_text().strip())
        except OSError:
            continue
        if ids == ACM_ID:
            yield Path('/dev') / tty.name


def shell_to_bootloader(log, timeout=60):
    """Ask a running RAM test to restart into Fastboot through its USB shell."""
    import serial
    ports = list(find_acm())
    if len(ports) != 1:
        raise Stop('Expected exactly one Linux ACM port for the shell reboot.')
    command = ('for t in /bin/reboot-mode /run/reboot-mode; do [ -x "$t" ] && exec "$t" bootloader; done; '
               # The split marker keeps the shell's echo of this line from matching.
               'echo REBOOT_MODE_UNAVAIL""ABLE\n')
    text = ''
    try:
        with serial.Serial(str(ports[0]), 115200, timeout=0.2, write_timeout=3) as console:
            console.reset_input_buffer()
            console.write(command.encode())
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and 'REBOOT_MODE_UNAVAILABLE\r' not in text:
                text += console.read(4096).decode('utf-8', 'replace')
    except serial.SerialException:
        text += '\n[ACM closed by the restart]\n'
    with log.open('a', encoding='utf-8') as stream:
        stream.write('shell: reboot-mode bootloader\n' + text + '\n')
    if 'REBOOT_MODE_REQUESTED: bootloader' not in text:
        raise Stop('The RAM shell did not accept the bootloader restart; nothing else was tried.')
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        usbipd_attach(FASTBOOT_ID)
        time.sleep(2)
        if Fastboot(log).run('devices').strip():
            return
    raise Stop(f'No Fastboot device {timeout} s after the shell restart.')


def capture(port, probe, log, timeout):
    import serial
    text = ''
    with serial.Serial(str(port), 115200, timeout=0.2, write_timeout=3) as console:
        console.dtr = console.rts = True
        time.sleep(2)
        for line in ('', 'uname -r', probe,
                     '/bin/busybox dmesg; printf "\\nBOOT1_KERNELLOG_EXIT=%s\\n" "$?"'):
            console.write((line + '\n').encode())
        deadline = time.monotonic() + timeout
        with log.open('a', encoding='utf-8', newline='') as stream:
            while time.monotonic() < deadline:
                chunk = console.read(65536).decode('utf-8', 'replace')
                if chunk:
                    text += chunk
                    stream.write(chunk)
                    stream.flush()
                if LOG_END.search(text):
                    break
                if len(text) > 8 << 20:
                    raise Stop('Serial output exceeded 8 MiB; keep the captured log.')
    return text


def summarize(text, report):
    tag = report['boot_profile'].split('-')[0].upper()
    smmu = [line for line in text.splitlines() if 'Unhandled context fault' in line]
    irq_lines = [line.strip() for line in text.splitlines()
                 if re.search(r'smmu|iommu', line, re.I) and re.match(r'\s*\d+:', line)]
    markers = sorted(set(re.findall(r'^(%s_[A-Z_]+)' % tag, text, re.M)))
    end = LOG_END.findall(text)
    return {
        'kernel_release_seen': report['kernel_release'] in text,
        'boot_profile_seen': report['boot_profile'] in text,
        'probe_end_seen': f'{tag}_PROBE_END' in text,
        'kernel_log_exit': int(end[-1]) if end else None,
        'markers': markers,
        'smmu_context_fault_lines': len(smmu),
        'smmu_first_fault': smmu[0].strip() if smmu else None,
        'smmu_irq_lines': irq_lines,
        'kernel_warning_lines': len(re.findall(r'WARNING: CPU', text)),
    }


def run(args):
    report_path = Path(args.report).resolve()
    report = json.loads(report_path.read_text())
    image = report_path.parent / report['image']
    profile = report['boot_profile'].split('-')[0]
    probe = 'boot-probe' if profile == 'boot1' else 'display-probe'
    if sha256(image) != report['image_sha256']:
        raise Stop('Image SHA256 does not match the report.')
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    out = REPORTS / (f'{stamp}-{profile}' + (f'-{args.label}' if args.label else ''))
    out.mkdir(parents=True)
    fastboot_log = out / f'{profile}-fastboot-{stamp}.txt'
    serial_log = out / f'{profile}-serial-{stamp}.txt'
    fastboot = Fastboot(fastboot_log)
    result = {'capture_id': stamp, 'host': 'WSL', 'kernel_release': report['kernel_release'],
              'boot_profile': report['boot_profile'], 'image': report['image'],
              'image_sha256': report['image_sha256'], 'capture_only': args.capture_only,
              'fastboot_commands': [], 'physical_display_confirmed': None,
              'user_observation': 'pending'}

    def save():
        for log in (fastboot_log, serial_log):
            if log.exists():
                result.setdefault('log_files', {})[log.name] = {
                    'bytes': log.stat().st_size, 'sha256': sha256(log)}
        (out / 'result.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')

    try:
        if args.from_shell and not args.capture_only:
            print('Restarting the running RAM test into Fastboot from its USB shell.')
            shell_to_bootloader(fastboot_log)
            result['restarted_from_shell'] = True
        if not args.capture_only:
            usbipd_attach(FASTBOOT_ID)
            time.sleep(2)
            serials = fastboot_serials(fastboot)
            if len(serials) != 1:
                raise Stop('Connect exactly one curtana in bootloader fastboot mode.')
            device = serials[0]
            if not re.search(r'product:\s*curtana\b', fastboot.run('getvar', 'product', serial=device)):
                raise Stop('Expected product curtana. Keep the log and stop here.')
            if args.no_restart:
                # After `adb reboot bootloader` this bootloader rejects
                # reboot-bootloader as an unknown command; it is already fresh.
                print('Skipping the bootloader restart as requested.')
            else:
                print('Restarting the bootloader for a fresh Fastboot session. No partition is written.')
                fastboot.run('reboot', 'bootloader', serial=device)
                deadline = time.monotonic() + args.reconnect_timeout
                while True:
                    time.sleep(2)
                    usbipd_attach(FASTBOOT_ID)
                    if device in fastboot_serials(fastboot):
                        break
                    if time.monotonic() > deadline:
                        raise Stop('Bootloader did not reconnect; image was not sent.')
            print('Sending the image once with fastboot boot for RAM execution. This does not flash it.')
            fastboot.run('boot', str(image), serial=device)
            result['ram_boot_requests'] = 1
        print('Waiting for the Linux USB serial device...')
        port = Path(args.port) if args.port else None
        deadline = time.monotonic() + args.port_timeout
        while port is None and time.monotonic() < deadline:
            ports = list(find_acm())
            if len(ports) > 1:
                raise Stop('Multiple Linux ACM ports; rerun with --capture-only --port.')
            port = ports[0] if ports else None
            if port is None:
                usbipd_attach(ACM_ID)
                time.sleep(1)
        if port is None:
            raise Stop(f'No Linux ACM port after {args.port_timeout} s. Do not resend the image.')
        result['serial_port'] = str(port)
        text = capture(port, probe, serial_log, args.capture_timeout)
        result['summary'] = summarize(text, report)
    except Stop as error:
        result['stopped'] = str(error)
        raise
    finally:
        if fastboot_log.exists():
            result['fastboot_commands'] = [line for line in fastboot_log.read_text().splitlines()
                                           if line.startswith('fastboot ')]
        save()
        print('Report directory:', out)
    summary = result['summary']
    if summary['kernel_release_seen'] and summary['boot_profile_seen'] and summary['probe_end_seen']:
        print(f"{profile.upper()}_LOG_CAPTURED: USB shell reached. Physical screen state still needs the user's report.")
    else:
        print('Boot is not confirmed. Inspect the logs.')


def shell(args):
    """Run one step on the running RAM shell and append it to steps.txt."""
    import serial
    ports = [Path(args.port)] if args.port else list(find_acm())
    deadline = time.monotonic() + args.wait_port
    while not ports and time.monotonic() < deadline:
        usbipd_attach(ACM_ID)
        time.sleep(1)
        ports = list(find_acm())
    if ports and not args.port:
        time.sleep(2)
    if len(ports) != 1:
        raise Stop('Expected exactly one Linux ACM port; nothing was sent.')
    marker = 'STEP_DONE_' + datetime.datetime.now().strftime('%H%M%S')
    done = re.compile(r'^%s=(\d+)\r?$' % marker, re.M)
    text = ''
    with serial.Serial(str(ports[0]), 115200, timeout=0.2, write_timeout=3) as console:
        console.dtr = console.rts = True
        console.reset_input_buffer()
        console.write(f'{args.cmdline}; printf "\\n{marker}=%s\\n" "$?"\n'.encode())
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline and not done.search(text):
            text += console.read(65536).decode('utf-8', 'replace')
    with (Path(args.directory) / 'steps.txt').open('a', encoding='utf-8', newline='') as stream:
        stream.write(f'### {datetime.datetime.now().isoformat(timespec="seconds")} {args.step}\n'
                     f'$ {args.cmdline}\n{text}\n')
    print(text)
    if not done.search(text):
        raise Stop('Step did not finish within the timeout; output kept in steps.txt.')


def reboot_bootloader(args):
    """Restart the running RAM test into Fastboot and wait for the device."""
    log = Path(args.directory) / 'reboot-bootloader.txt'
    shell_to_bootloader(log)
    print('Fastboot device is back; see', log)


def observe(args):
    path = Path(args.directory) / 'result.json'
    result = json.loads(path.read_text())
    entry = {'screen': args.screen, 'backlight': args.backlight, 'notes': args.notes}
    if args.step:
        result.setdefault('step_observations', {})[args.step] = entry
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
        return
    result['user_observation'] = entry
    result['physical_display_confirmed'] = args.confirmed
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')


def pull(args):
    """Copy one file from the RAM shell in sha256-checked chunks.

    The bytes go only to the local output path; steps.txt records the
    transfer summary, so recordings and other private data stay out of Git.
    """
    import serial
    ports = [Path(args.port)] if args.port else list(find_acm())
    if len(ports) != 1:
        raise Stop('Expected exactly one Linux ACM port; nothing was sent.')
    remote = args.remote
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', remote):
        raise Stop('Remote path must be a plain absolute path.')

    def call(console, cmdline, end, timeout=30):
        console.reset_input_buffer()
        # The shell echoes the command line; the quotes keep the markers out of the echo.
        console.write(f'echo {end}""_BEGIN; {cmdline}; echo {end}""_DONE\n'.encode())
        text = ''
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and f'{end}_DONE' not in text:
            text += console.read(65536).decode('ascii', 'replace')
        if f'{end}_DONE' not in text:
            raise Stop(f'No reply for {end}; transfer abandoned.')
        return text.split(f'{end}_DONE')[0].split(f'{end}_BEGIN')[-1]

    chunk = 4096
    data = bytearray()
    retries = 0
    with serial.Serial(str(ports[0]), 115200, timeout=0.2, write_timeout=3) as console:
        console.dtr = console.rts = True
        info = call(console, f'ls -ln {remote}; sha256sum {remote}', 'INFO')
        size = int(re.search(r'^\S+\s+\d+\s+\d+\s+\d+\s+(\d+) ', info, re.M).group(1))
        whole = re.search(r'^([0-9a-f]{64}) ', info, re.M).group(1)
        for index in range((size + chunk - 1) // chunk):
            for attempt in range(4):
                text = call(console, f'dd if={remote} bs={chunk} skip={index} count=1 2>/dev/null'
                            f" | hexdump -v -e '32/1 \"%02x\" \"\\n\"'; echo SUM; "
                            f'dd if={remote} bs={chunk} skip={index} count=1 2>/dev/null | sha256sum',
                            f'CHUNK{index}')
                body, _, tail = text.partition('SUM')
                piece = bytes.fromhex(re.sub(r'[^0-9a-f]', '', body))
                want = re.search(r'([0-9a-f]{64})', tail)
                if want and hashlib.sha256(piece).hexdigest() == want.group(1):
                    data += piece
                    break
                retries += 1
            else:
                raise Stop(f'Chunk {index} failed its checksum four times.')
    if hashlib.sha256(data).hexdigest() != whole:
        raise Stop('Whole-file sha256 mismatch; output not written.')
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    summary = f'pulled {remote} bytes={len(data)} sha256={whole} chunk_retries={retries}'
    with (Path(args.directory) / 'steps.txt').open('a', encoding='utf-8', newline='') as stream:
        stream.write(f'### {datetime.datetime.now().isoformat(timespec="seconds")} pull\n{summary}\n')
    print(summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    boot = commands.add_parser('boot', help='verify, RAM boot once and capture logs')
    boot.add_argument('report', help='packaged <profile>-report.json next to the boot image')
    boot.add_argument('--capture-only', action='store_true', help='do not use fastboot')
    boot.add_argument('--port', help='ACM device; default: the only 1d6b:0104 ttyACM')
    boot.add_argument('--reconnect-timeout', type=int, default=60)
    boot.add_argument('--port-timeout', type=int, default=120)
    boot.add_argument('--capture-timeout', type=int, default=120)
    boot.add_argument('--label', help='suffix for the report directory name')
    boot.add_argument('--no-restart', action='store_true',
                      help='send the image without first restarting the bootloader')
    boot.add_argument('--from-shell', action='store_true',
                      help='first restart the running RAM test into Fastboot through its USB shell')
    rb = commands.add_parser('reboot-bootloader', help='restart the running RAM test into Fastboot')
    rb.add_argument('directory', help='report directory for the log')
    step = commands.add_parser('shell', help='run one diagnostic step on the running RAM shell')
    step.add_argument('directory')
    step.add_argument('step', help='short step name recorded in steps.txt')
    step.add_argument('cmdline', metavar='command')
    step.add_argument('--port')
    step.add_argument('--timeout', type=int, default=60)
    step.add_argument('--wait-port', type=int, default=0,
                      help='seconds to wait for (and attach) a re-enumerated ACM port')
    get = commands.add_parser('pull', help='copy a file from the RAM shell with sha256 checks')
    get.add_argument('directory', help='report directory; only the transfer summary is logged')
    get.add_argument('remote')
    get.add_argument('output', help='local path, keep private data outside Git')
    get.add_argument('--port')
    note = commands.add_parser('observe', help="record the user's physical observation")
    note.add_argument('directory')
    note.add_argument('--screen', required=True)
    note.add_argument('--backlight', required=True)
    note.add_argument('--notes', default='')
    note.add_argument('--step', help='record against a shell step instead of the whole boot')
    note.add_argument('--confirmed', action='store_true', help='banner text and colours seen')
    args = parser.parse_args()
    try:
        {'boot': run, 'shell': shell, 'observe': observe,
         'reboot-bootloader': reboot_bootloader, 'pull': pull}[args.command](args)
    except Stop as error:
        sys.exit('STOPPED: ' + str(error))


if __name__ == '__main__':
    main()

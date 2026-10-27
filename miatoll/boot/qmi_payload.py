"""qmicli (libqmi over QRTR) for the modem1 RAMdisk.

The runtime comes from miatoll/modem/prepare_qmi_runtime.py: Alpine v3.22
main/community APKs checked against the signed indexes. Only qmicli and the
shared objects it needs (followed through DT_NEEDED) are copied; the musl
loader comes from the Mesa payload already in the image.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

READELF = 'tools/llvm18/usr/lib/llvm-18/bin/llvm-readelf'


def load(workspace):
    """Return ({initramfs path: (bytes, mode)}, {link: target}, summary)."""
    workspace = Path(workspace)
    runtime = workspace / 'tools/qmi-runtime-aarch64'
    record = json.loads((runtime / 'qmi-runtime-packages.json').read_text())
    assert all(info['signature'] == 'Verified OK' for info in record['indexes'].values())
    files, links = {}, {}
    pending, seen = ['usr/bin/qmicli'], set()
    while pending:
        rel = pending.pop()
        if rel in seen:
            continue
        seen.add(rel)
        path = runtime / rel
        real = path.resolve()
        assert real.is_relative_to(runtime.resolve()), rel
        if path.is_symlink():
            links[rel] = path.readlink().as_posix()
        files[real.relative_to(runtime.resolve()).as_posix()] = (real.read_bytes(), 0o755)
        dynamic = subprocess.check_output([str(workspace / READELF), '-d', str(real)], text=True)
        for soname in re.findall(r'\(NEEDED\)\s+Shared library: \[([^\]]+)\]', dynamic):
            if soname == 'libc.musl-aarch64.so.1':
                continue
            candidate = 'usr/lib/' + soname
            assert (runtime / candidate).exists(), 'Missing QMI dependency ' + soname
            pending.append(candidate)
    summary = {'packages': {name: info['version'] for name, info in record['packages'].items()},
               'indexes': record['indexes'],
               'files': {rel: hashlib.sha256(data).hexdigest() for rel, (data, _) in files.items()},
               'links': links}
    return files, links, summary

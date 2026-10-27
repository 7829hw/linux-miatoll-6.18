#!/usr/bin/env python3
"""Prepare the aarch64 musl runtime for qmicli (libqmi over QRTR).

Both Alpine v3.22 aarch64 indexes (main and community) are checked against
the Alpine signing key, which was fetched from alpinelinux.org/keys and from
the aports alpine-keys directory and found identical. Every APK is checked
against its index entry (size, control-segment SHA-1) and its .PKGINFO
datahash, then extracted into tools/qmi-runtime-aarch64.
"""
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
import zlib

WORKSPACE = Path(__file__).resolve().parents[3]
KEY = WORKSPACE / 'downloads/alpine-keys/web-alpine-devel@lists.alpinelinux.org-616ae350.rsa.pub'
KEY_SHA256 = 'd11f6b21c61b4274e182eb888883a8ba8acdbf820dcc7a6d82a7d9fc2fd2836d'
INDEXES = {
    'main': (WORKSPACE / 'downloads/alpine-APKINDEX.tar.gz', 'https://dl-cdn.alpinelinux.org/alpine/v3.22/main/aarch64/'),
    'community': (WORKSPACE / 'downloads/alpine-community-APKINDEX.tar.gz',
                  'https://dl-cdn.alpinelinux.org/alpine/v3.22/community/aarch64/'),
}
CACHE = WORKSPACE / 'downloads/qmi-apk'
OUT = WORKSPACE / 'tools/qmi-runtime-aarch64'
PACKAGES = ('qmi-utils', 'libqmi', 'libqrtr-glib', 'libmbim', 'libgudev', 'eudev-libs', 'glib', 'libffi',
            'libintl', 'libmount', 'libblkid', 'libeconf', 'pcre2', 'zlib')


def split_gzip(data):
    members = []
    while data:
        inflater = zlib.decompressobj(31)
        payload = inflater.decompress(data)
        members.append((data[:len(data) - len(inflater.unused_data)], payload))
        data = inflater.unused_data
    return members


def verified_index(path):
    members = split_gzip(path.read_bytes())
    with tarfile.open(fileobj=io.BytesIO(members[0][1])) as archive:
        name = archive.getnames()[0]
        signature = archive.extractfile(name).read()
    if name != '.SIGN.RSA.' + KEY.name.removeprefix('web-'):
        raise SystemExit(f'{path.name}: unexpected signing key {name}')
    with tempfile.TemporaryDirectory() as temporary:
        (Path(temporary) / 'sig').write_bytes(signature)
        (Path(temporary) / 'data').write_bytes(b''.join(item[0] for item in members[1:]))
        subprocess.run(['openssl', 'dgst', '-sha1', '-verify', str(KEY), '-signature',
                        str(Path(temporary) / 'sig'), str(Path(temporary) / 'data')], check=True,
                       capture_output=True)
    with tarfile.open(fileobj=io.BytesIO(members[1][1])) as archive:
        text = archive.extractfile('APKINDEX').read().decode()
        description = archive.extractfile('DESCRIPTION').read().decode().strip()
    entries = {}
    for block in text.split('\n\n'):
        fields = dict(line.split(':', 1) for line in block.splitlines() if ':' in line[:2])
        if 'P' in fields:
            entries[fields['P']] = fields
    return entries, description


def main():
    if hashlib.sha256(KEY.read_bytes()).hexdigest() != KEY_SHA256:
        raise SystemExit('Alpine signing key differs from the pinned key')
    repos = {}
    for repo, (path, url) in INDEXES.items():
        entries, description = verified_index(path)
        repos[repo] = (entries, url, description, hashlib.sha256(path.read_bytes()).hexdigest())
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    record = {'indexes': {repo: {'description': info[2], 'sha256': info[3], 'signature': 'Verified OK'}
                          for repo, info in repos.items()}, 'packages': {}}
    for name in PACKAGES:
        repo = next(r for r, info in repos.items() if name in info[0])
        entry, url = repos[repo][0][name], repos[repo][1]
        filename = f"{name}-{entry['V']}.apk"
        path = CACHE / filename
        if not path.exists():
            urllib.request.urlretrieve(url + filename, path)
        data = path.read_bytes()
        if len(data) != int(entry['S']):
            raise SystemExit(f'{filename}: size differs from APKINDEX')
        members = split_gzip(data)
        control = next(item for item in members if b'.PKGINFO' in item[1][:2048])
        if hashlib.sha1(control[0]).digest() != base64.b64decode(entry['C'][2:]):
            raise SystemExit(f'{filename}: control checksum differs from APKINDEX')
        with tarfile.open(fileobj=io.BytesIO(control[1])) as archive:
            info = dict(line.split(' = ', 1) for line in
                        archive.extractfile('.PKGINFO').read().decode().splitlines() if ' = ' in line)
        if hashlib.sha256(members[-1][0]).hexdigest() != info['datahash']:
            raise SystemExit(f'{filename}: datahash mismatch')
        with tarfile.open(fileobj=io.BytesIO(members[-1][1])) as archive:
            archive.extractall(OUT, filter='data')
        record['packages'][name] = {'repository': repo, 'version': entry['V'], 'bytes': len(data),
                                    'sha256': hashlib.sha256(data).hexdigest(), 'apkindex_checksum': entry['C']}
    (OUT / 'qmi-runtime-packages.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()

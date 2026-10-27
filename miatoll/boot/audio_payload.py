"""Pinned native ADSP audio firmware for the audio RAMdisk.

Same files and pins as the earlier curtana bring-up (sm7125-mainline
firmware-xiaomi-miatoll, see miatoll/reference/audio1/firmware-sources.json).
"""
import hashlib
from pathlib import Path

# initramfs path, bytes, Git blob SHA-1, SHA-256
PINNED = (
    ('lib/firmware/qcom/sm7125/miatoll/adsp.mbn', 16281748, '804f2f83dcbe2544b0d393d4a7af391ee961a5bf',
     '3cecdd348ea3d2e9d4a3913a46fcc7ff7e9fdd16ed28c364a30216b6c6d79094'),
    ('lib/firmware/qcom/sm7125/miatoll/adspr.jsn', 403, '0964c15a7204f5b8868a0d91cb90da373f31a038',
     '4781dc9312fa017b0e611c752dae2183c0f205af8300b28417a496dae511b0a5'),
    ('lib/firmware/qcom/sm7125/miatoll/adsps.jsn', 405, 'ac032cf62729d86a4aab1776f3ea7654c6f9455c',
     '9723d9873223f83464246a234bef61569c3d6a07112448e4e7da870d4ce5972a'),
    ('lib/firmware/qcom/sm7125/miatoll/adspua.jsn', 555, '2d6824e8fb9a7ec2e0c2197cb400f3772bcb3cba',
     'd6c6376f53e5449eb4f7b9e5a30679ebc2a9afaad28c13ff171f979e7b1af1f6'),
)


def load(workspace):
    """Return {initramfs path: (bytes, mode)} and a provenance summary."""
    files, summary = {}, {}
    for name, size, blob, sha256 in PINNED:
        data = (Path(workspace) / 'downloads/audio-firmware' / name).read_bytes()
        assert len(data) == size and hashlib.sha256(data).hexdigest() == sha256, 'Audio firmware changed: ' + name
        assert hashlib.sha1(b'blob %d\0' % size + data).hexdigest() == blob, 'Git blob mismatch: ' + name
        files[name] = (data, 0o644)
        summary[name] = {'bytes': size, 'sha256': sha256, 'git_blob_sha1': blob}
    return files, summary

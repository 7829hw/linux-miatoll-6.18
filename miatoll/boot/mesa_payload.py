"""Mesa freedreno userspace and kmscube for the gpu2 and vulkan1 RAMdisks.

Built by miatoll/gpu/build_mesa.sh (Mesa 25.1.9 and kmscube 2c1f2646, both
pinned by SHA-256) against the Alpine v3.22 sysroot from
prepare_mesa_sysroot.py. The recorded build-result.json must match the build
script in this tree, the sysroot package list and every runtime file.
"""
import hashlib
import json
from pathlib import Path

BOOT = Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(workspace, variant='gles'):
    """Return ({initramfs path: (bytes, mode)}, {link: target}, summary).

    variant 'gles' is ../out-mesa (gpu2); 'vulkan' is ../out-mesa-vulkan, which
    adds Turnip, the Alpine Vulkan loader and vulkan-tools (vulkan1).
    """
    workspace = Path(workspace)
    out = workspace / {'gles': 'out-mesa', 'vulkan': 'out-mesa-vulkan'}[variant]
    sysroot = workspace / 'tools/sysroot-mesa-aarch64'
    record = json.loads((out / 'build-result.json').read_text())
    assert record.get('variant', 'gles') == variant, 'Unexpected Mesa build variant'
    assert record['build_script_sha256'] == sha256(BOOT.parent / 'gpu/build_mesa.sh'), 'Rebuild Mesa: script changed'
    assert record['sysroot_packages_sha256'] == sha256(sysroot / 'sysroot-packages.json'), 'Mesa sysroot changed'
    if record.get('vk_display_probe_source_sha256'):
        assert record['vk_display_probe_source_sha256'] == sha256(BOOT.parent / 'gpu/vk-display-probe.c'), \
            'Rebuild Mesa: vk-display-probe.c changed'
    files = {}
    for rel, info in record['files'].items():
        base = out / 'stage' if info['from'] == 'stage' else sysroot
        data = (base / rel).read_bytes()
        assert hashlib.sha256(data).hexdigest() == info['sha256'], 'Mesa runtime file changed: ' + rel
        files[rel] = (data, 0o755)
    for rel, info in record['licenses'].items():
        data = (out / info['source']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == info['sha256'], 'License changed: ' + rel
        files[rel] = (data, 0o644)
    summary = {'mesa': record['mesa'], 'kmscube': record['kmscube'],
               'files': {rel: info['sha256'] for rel, info in record['files'].items()}}
    return files, record['links'], summary
